import os
import json
import math

import osmnx as ox
import networkx as nx

from .geo_utils import get_turn_directions, make_heuristic, distance_m
from .graph_loader import get_graph


# ============================================================
# OVERPASS CONFIG
# ============================================================

ox.settings.overpass_url = os.getenv(
    "OVERPASS_URL",
    "https://overpass.kumi.systems/api"
)

ox.settings.overpass_rate_limit = True


# ============================================================
# HOSPITAL CACHE
# ============================================================

_hospital_cache = {}

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

HOSPITAL_CACHE_DIR = os.path.join(
    BASE_DIR,
    "hospital_cache"
)


# ============================================================
# HELPERS
# ============================================================

def _normalize_city(city: str) -> str:
    return ", ".join(
        part.strip().title()
        for part in city.split(",")
    )


def _safe_filename(city: str) -> str:
    return (
        city
        .replace(", ", "_")
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )


def _hospital_cache_file(city: str) -> str:
    return os.path.join(
        HOSPITAL_CACHE_DIR,
        f"{_safe_filename(city)}.json"
    )


# ============================================================
# HOSPITAL CACHE - SAVE
# ============================================================

def _save_hospitals_to_disk(
    city: str,
    hospital_data: list
):
    try:
        os.makedirs(
            HOSPITAL_CACHE_DIR,
            exist_ok=True
        )

        with open(
            _hospital_cache_file(city),
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                hospital_data,
                f,
                ensure_ascii=False,
                indent=2
            )

        print(
            f"[HOSPITAL CACHE] Saved "
            f"{len(hospital_data)} hospitals for {city}"
        )

    except Exception as e:

        print(
            f"[HOSPITAL CACHE] Could not save hospitals: {e}"
        )


# ============================================================
# HOSPITAL CACHE - LOAD
# ============================================================

def _load_hospitals_from_disk(city: str):

    cache_file = _hospital_cache_file(city)

    if not os.path.exists(cache_file):
        return None

    try:

        with open(
            cache_file,
            "r",
            encoding="utf-8"
        ) as f:

            hospital_data = json.load(f)

        if not hospital_data:
            return None

        print(
            f"[HOSPITAL CACHE] Loaded "
            f"{len(hospital_data)} hospitals "
            f"from disk for {city}"
        )

        return hospital_data

    except Exception as e:

        print(
            f"[HOSPITAL CACHE] Could not load cache: {e}"
        )

        return None


# ============================================================
# GET HOSPITALS
# ============================================================

def get_hospitals(city: str):

    city = _normalize_city(city)

    # --------------------------------------------------------
    # 1. MEMORY CACHE
    # --------------------------------------------------------

    if city in _hospital_cache:

        print(
            f"[HOSPITAL CACHE] Using memory cache "
            f"for {city}"
        )

        return _hospital_cache[city]

    # --------------------------------------------------------
    # 2. DISK CACHE
    # --------------------------------------------------------

    cached_hospitals = _load_hospitals_from_disk(city)

    if cached_hospitals is not None:

        _hospital_cache[city] = cached_hospitals

        return cached_hospitals

    # --------------------------------------------------------
    # 3. OSM
    # --------------------------------------------------------

    print(
        f"[HOSPITAL CACHE] Fetching hospitals "
        f"from OpenStreetMap for {city}..."
    )

    try:

        hospitals = ox.features_from_place(
            city,
            tags={
                "amenity": "hospital"
            }
        )

    except Exception as e:

        raise Exception(
            f"Could not fetch hospitals for {city}. "
            f"OpenStreetMap/Overpass may be temporarily unavailable. "
            f"Details: {str(e)}"
        )

    hospital_data = []

    if not hospitals.empty:

        for _, hospital in hospitals.iterrows():

            try:

                geometry = hospital.geometry

                if geometry is None:
                    continue

                if geometry.geom_type == "Point":

                    lat = float(geometry.y)
                    lon = float(geometry.x)

                else:

                    centroid = geometry.centroid

                    lat = float(centroid.y)
                    lon = float(centroid.x)

                if math.isnan(lat) or math.isnan(lon):
                    continue

                name = hospital.get(
                    "name",
                    "Unknown Hospital"
                )

                if not isinstance(name, str):
                    name = "Unknown Hospital"

                name_lower = name.lower()

                # Ignore veterinary / animal facilities
                if any(
                    word in name_lower
                    for word in [
                        "vet",
                        "pet",
                        "animal"
                    ]
                ):
                    continue

                hospital_data.append({
                    "name": name,
                    "lat": lat,
                    "lon": lon
                })

            except Exception:
                continue

    if not hospital_data:

        raise Exception(
            "No hospitals found nearby!"
        )

    # --------------------------------------------------------
    # SAVE CACHE
    # --------------------------------------------------------

    _hospital_cache[city] = hospital_data

    _save_hospitals_to_disk(
        city,
        hospital_data
    )

    return hospital_data


# ============================================================
# EMERGENCY ROUTE
# ============================================================

def get_emergency_route(
    source: str,
    city: str = "Chhatrapati Sambhajinagar, Maharashtra, India"
):

    try:

        city = _normalize_city(city)

        # IMPORTANT:
        # Graph comes from shared graph_loader.
        G = get_graph(city)

        heuristic = make_heuristic(G)

        city_short = city.split(",")[0].strip()

        # ----------------------------------------------------
        # GEOCODE SOURCE
        # ----------------------------------------------------

        try:

            source_point = ox.geocode(
                f"{source}, {city}"
            )

        except Exception:

            source_point = ox.geocode(
                f"{source}, {city_short}"
            )

        source_node = ox.nearest_nodes(
            G,
            source_point[1],
            source_point[0]
        )

        # ----------------------------------------------------
        # LOAD HOSPITALS
        # ----------------------------------------------------

        hospitals = get_hospitals(city)

        if not hospitals:

            raise Exception(
                "No hospitals found nearby!"
            )

        # ----------------------------------------------------
        # PRE-FILTER HOSPITALS
        # ----------------------------------------------------

        candidates = []

        for hospital in hospitals:

            try:

                h_lat = float(
                    hospital["lat"]
                )

                h_lon = float(
                    hospital["lon"]
                )

                if (
                    math.isnan(h_lat)
                    or math.isnan(h_lon)
                ):
                    continue

                straight_dist = distance_m(
                    (
                        source_point[0],
                        source_point[1]
                    ),
                    (
                        h_lat,
                        h_lon
                    )
                )

                candidates.append({
                    "name": hospital["name"],
                    "lat": h_lat,
                    "lon": h_lon,
                    "straight_dist": straight_dist
                })

            except Exception:
                continue

        if not candidates:

            raise Exception(
                "No valid hospitals found!"
            )

        # Only nearest 8 hospitals
        candidates.sort(
            key=lambda c: c["straight_dist"]
        )

        candidates = candidates[:8]

        # ----------------------------------------------------
        # A* FOR CANDIDATES
        # ----------------------------------------------------

        hospital_list = []

        best_node = None
        best_length = float("inf")
        best_hospital = None

        for candidate in candidates:

            try:

                h_node = ox.nearest_nodes(
                    G,
                    candidate["lon"],
                    candidate["lat"]
                )

                length = nx.astar_path_length(
                    G,
                    source_node,
                    h_node,
                    heuristic=heuristic,
                    weight="length"
                )

                hospital_list.append({
                    "name": candidate["name"],
                    "coords": [
                        float(candidate["lat"]),
                        float(candidate["lon"])
                    ],
                    "distance_km": round(
                        length / 1000,
                        2
                    )
                })

                if length < best_length:

                    best_length = length
                    best_node = h_node
                    best_hospital = candidate["name"]

            except Exception:
                continue

        if best_node is None:

            raise Exception(
                "Could not find route to any hospital!"
            )

        # ----------------------------------------------------
        # FULL PATH FOR WINNER
        # ----------------------------------------------------

        best_path = nx.astar_path(
            G,
            source_node,
            best_node,
            heuristic=heuristic,
            weight="length"
        )

        hospital_list.sort(
            key=lambda x: x["distance_km"]
        )

        coordinates = []

        for node in best_path:

            node_data = G.nodes[node]

            coordinates.append([
                float(node_data["y"]),
                float(node_data["x"])
            ])

        directions = get_turn_directions(
            coordinates
        )

        return {
            "path": coordinates,

            "source": coordinates[0],

            "destination": coordinates[-1],

            "nearest_hospital": best_hospital,

            "hospitals": hospital_list[:10],

            "distance_m": round(
                best_length
            ),

            "distance_km": round(
                best_length / 1000,
                2
            ),

            "directions": directions
        }

    except Exception as e:

        raise Exception(
            f"Emergency route error: {str(e)}"
        )


# ============================================================
# ROUTE TO SELECTED HOSPITAL
# ============================================================

def get_route_to_hospital(
    source: str,
    h_lat: float,
    h_lon: float,
    h_name: str,
    city: str = "Chhatrapati Sambhajinagar, Maharashtra, India"
):

    try:

        city = _normalize_city(city)

        # Shared graph loader
        G = get_graph(city)

        heuristic = make_heuristic(G)

        city_short = city.split(",")[0].strip()

        # ----------------------------------------------------
        # GEOCODE SOURCE
        # ----------------------------------------------------

        try:

            source_point = ox.geocode(
                f"{source}, {city}"
            )

        except Exception:

            source_point = ox.geocode(
                f"{source}, {city_short}"
            )

        source_node = ox.nearest_nodes(
            G,
            source_point[1],
            source_point[0]
        )

        # ----------------------------------------------------
        # HOSPITAL NODE
        # ----------------------------------------------------

        h_node = ox.nearest_nodes(
            G,
            float(h_lon),
            float(h_lat)
        )

        # ----------------------------------------------------
        # A* ROUTE
        # ----------------------------------------------------

        path = nx.astar_path(
            G,
            source_node,
            h_node,
            heuristic=heuristic,
            weight="length"
        )

        length = nx.path_weight(
            G,
            path,
            weight="length"
        )

        # ----------------------------------------------------
        # CONVERT NODES TO COORDINATES
        # ----------------------------------------------------

        coordinates = []

        for node in path:

            node_data = G.nodes[node]

            coordinates.append([
                float(node_data["y"]),
                float(node_data["x"])
            ])

        # ----------------------------------------------------
        # DIRECTIONS
        # ----------------------------------------------------

        directions = get_turn_directions(
            coordinates
        )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {

            "path": coordinates,

            "source": coordinates[0],

            "destination": coordinates[-1],

            "nearest_hospital": h_name,

            "distance_m": round(
                length
            ),

            "distance_km": round(
                length / 1000,
                2
            ),

            "directions": directions
        }

    except Exception as e:

        raise Exception(
            f"Hospital route error: {str(e)}"
        )