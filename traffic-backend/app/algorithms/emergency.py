import os
import json
import math

import requests
import osmnx as ox
import networkx as nx

from .geo_utils import get_turn_directions, make_heuristic, distance_m

# ============================================================
# OVERPASS CONFIG
# ============================================================
# overpass-api.de blocks/rate-limits many cloud/datacenter IPs
# (Render, Railway, etc.). Using a mirror avoids "Connection refused"
# errors in production.
ox.settings.overpass_url = "https://overpass.kumi.systems/api"
ox.settings.overpass_rate_limit = True


# ============================================================
# PREBUILT GRAPH DOWNLOAD (GitHub Releases)
# ============================================================
# Same mechanism as dijkstra.py -- the .graphml files are too large
# for a normal git push, so they're uploaded as assets on a GitHub
# Release instead. Set this env var to the release's base download
# URL, e.g.:
#
#   GRAPH_CACHE_BASE_URL=https://github.com/<user>/<repo>/releases/download/v1-graphs
#
# If not set, or the download fails, falls back to live Overpass
# download exactly as before.
GRAPH_CACHE_BASE_URL = os.getenv("GRAPH_CACHE_BASE_URL", "").rstrip("/")


# ============================================================
# CACHE
# ============================================================

_graph_cache = {}
_hospital_cache = {}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# IMPORTANT:
# Same graph_cache folder used by normal/dijkstra.py
CACHE_DIR = os.path.join(BASE_DIR, "graph_cache")

HOSPITAL_CACHE_DIR = os.path.join(BASE_DIR, "hospital_cache")


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


def _graph_cache_file(city: str) -> str:
    return os.path.join(
        CACHE_DIR,
        f"{_safe_filename(city)}.graphml"
    )


def _hospital_cache_file(city: str) -> str:
    return os.path.join(
        HOSPITAL_CACHE_DIR,
        f"{_safe_filename(city)}.json"
    )


def _try_download_from_release(city: str, cache_file: str) -> bool:
    """
    Attempt to download a prebuilt .graphml for this city from a
    GitHub Release into cache_file. Returns True on success, False
    otherwise (caller falls back to live Overpass download).

    NOTE: since normal/dijkstra.py, emergency.py, and delivery.py all
    share the SAME CACHE_DIR and filename convention, whichever mode
    is hit first downloads the graph and the other two just find it
    already on disk -- no duplicate downloads.
    """

    if not GRAPH_CACHE_BASE_URL:
        return False

    filename = os.path.basename(cache_file)
    url = f"{GRAPH_CACHE_BASE_URL}/{filename}"

    print(f"[EMERGENCY GRAPH] Trying prebuilt graph download for {city}...")
    print(f"[EMERGENCY GRAPH] {url}")

    try:
        with requests.get(url, stream=True, timeout=60) as resp:
            if resp.status_code != 200:
                print(
                    f"[EMERGENCY GRAPH] Prebuilt graph not available "
                    f"(status {resp.status_code}) for {city}, "
                    f"will fall back to Overpass."
                )
                return False

            os.makedirs(CACHE_DIR, exist_ok=True)
            tmp_file = cache_file + ".tmp"

            with open(tmp_file, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

            os.replace(tmp_file, cache_file)

        print(f"[EMERGENCY GRAPH] Prebuilt graph downloaded for {city}!")
        return True

    except Exception as e:
        print(f"[EMERGENCY GRAPH] Prebuilt graph download failed for {city}: {e}")
        return False


# ============================================================
# GRAPH LOADING
# ============================================================

def get_graph(city: str):
    """
    Load graph using this priority:

    1. Memory cache
    2. Existing GraphML file
    3. Prebuilt graph from GitHub Release (GRAPH_CACHE_BASE_URL)
    4. Download from OSM/Overpass (last resort)

    Emergency uses the SAME graph_cache directory and
    SAME filename convention as normal mode.
    """

    city = _normalize_city(city)

    # --------------------------------------------------------
    # 1. MEMORY CACHE
    # --------------------------------------------------------

    if city in _graph_cache:
        print(f"[EMERGENCY GRAPH] Using memory cache: {city}")
        return _graph_cache[city]

    # --------------------------------------------------------
    # 2. DISK CACHE
    # --------------------------------------------------------

    os.makedirs(CACHE_DIR, exist_ok=True)

    cache_file = _graph_cache_file(city)

    print(f"[EMERGENCY GRAPH] Looking for cached graph:")
    print(f"[EMERGENCY GRAPH] {cache_file}")

    if not os.path.exists(cache_file):
        # ----------------------------------------------------
        # 3. TRY PREBUILT GRAPH FROM GITHUB RELEASE
        # ----------------------------------------------------
        _try_download_from_release(city, cache_file)

    if os.path.exists(cache_file):

        try:
            print(
                f"[EMERGENCY GRAPH] Loading graph from disk "
                f"for {city}..."
            )

            G = ox.load_graphml(cache_file)

            _graph_cache[city] = G

            print(
                f"[EMERGENCY GRAPH] Graph loaded successfully "
                f"for {city}!"
            )

            return G

        except Exception as e:

            print(
                f"[EMERGENCY GRAPH] Cached graph could not be loaded: "
                f"{e}"
            )

            # Remove only if corrupted
            try:
                os.remove(cache_file)
                print(
                    f"[EMERGENCY GRAPH] Removed corrupted cache: "
                    f"{cache_file}"
                )
            except Exception:
                pass

    # --------------------------------------------------------
    # 4. DOWNLOAD FROM OVERPASS ONLY IF NOTHING ELSE WORKED
    # --------------------------------------------------------

    print(
        f"[EMERGENCY GRAPH] No cached/prebuilt graph found for {city}."
    )

    print(
        f"[EMERGENCY GRAPH] Downloading road graph for {city}..."
    )

    try:

        G = ox.graph_from_place(
            city,
            network_type="drive"
        )

        try:

            ox.save_graphml(
                G,
                cache_file
            )

            print(
                f"[EMERGENCY GRAPH] Graph downloaded and "
                f"saved to cache for {city}!"
            )

        except Exception as e:

            print(
                f"[EMERGENCY GRAPH] Graph downloaded but "
                f"could not be saved: {e}"
            )

        _graph_cache[city] = G

        return G

    except Exception as e:

        raise Exception(
            f"Unable to load road network for {city}. "
            f"OpenStreetMap/Overpass may be temporarily unavailable. "
            f"Details: {str(e)}"
        )


# ============================================================
# HOSPITAL CACHE
# ============================================================

def _save_hospitals_to_disk(city: str, hospital_data: list):
    """
    Save the already-processed, already-filtered hospital list
    (list of {name, lat, lon} dicts) to disk.

    IMPORTANT: this must receive the FILTERED list (the same one
    returned to the caller), not the raw OSM GeoDataFrame -- otherwise
    vet/pet/animal clinics excluded from the live response would
    silently reappear on every subsequent disk-cache read.
    """

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
            f"{len(hospital_data)} hospitals from disk "
            f"for {city}"
        )

        return hospital_data

    except Exception as e:

        print(
            f"[HOSPITAL CACHE] Could not load cache: {e}"
        )

        return None


def get_hospitals(city: str):

    city = _normalize_city(city)

    # --------------------------------------------------------
    # MEMORY
    # --------------------------------------------------------

    if city in _hospital_cache:
        print(
            f"[HOSPITAL CACHE] Using memory cache for {city}"
        )
        return _hospital_cache[city]

    # --------------------------------------------------------
    # DISK
    # --------------------------------------------------------

    cached_hospitals = _load_hospitals_from_disk(city)

    if cached_hospitals is not None:

        _hospital_cache[city] = cached_hospitals

        return cached_hospitals

    # --------------------------------------------------------
    # OSM
    # --------------------------------------------------------

    print(
        f"[HOSPITAL CACHE] Fetching hospitals from "
        f"OpenStreetMap for {city}..."
    )

    try:

        hospitals = ox.features_from_place(
            city,
            tags={"amenity": "hospital"}
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

                # Ignore animal/veterinary facilities
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

    # Memory cache
    _hospital_cache[city] = hospital_data

    # Disk cache
    # FIX: save the filtered `hospital_data` list, not the raw
    # `hospitals` GeoDataFrame -- previously this bypassed the
    # vet/pet/animal filter for every subsequent disk-cache read.
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

        # Load shared graph
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

                h_lat = float(hospital["lat"])
                h_lon = float(hospital["lon"])

                if math.isnan(h_lat) or math.isnan(h_lon):
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

        # Only nearest 8
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
            "distance_m": round(best_length),
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

        coordinates = []

        for node in path:

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
            "nearest_hospital": h_name,
            "distance_m": round(length),
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