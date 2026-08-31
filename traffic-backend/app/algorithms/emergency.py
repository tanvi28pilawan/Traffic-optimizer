import math

import networkx as nx
import osmnx as ox

from .geo_utils import get_turn_directions, make_heuristic, distance_m
from .graph_loader import get_graph, get_hospitals, _normalize_city


# ============================================================
# EMERGENCY ROUTE
# ============================================================

def get_emergency_route(
    source: str,
    city: str = "Chhatrapati Sambhajinagar, Maharashtra, India"
):

    try:

        city = _normalize_city(city)

        # Shared graph (same object used by normal/delivery too)
        G = get_graph(city)

        heuristic = make_heuristic(G)

        city_short = city.split(",")[0].strip()

        # ----------------------------------------------------
        # GEOCODE SOURCE
        # ----------------------------------------------------

        try:
            source_point = ox.geocode(f"{source}, {city}")
        except Exception:
            source_point = ox.geocode(f"{source}, {city_short}")

        source_node = ox.nearest_nodes(G, source_point[1], source_point[0])

        # ----------------------------------------------------
        # LOAD HOSPITALS
        # ----------------------------------------------------

        hospitals = get_hospitals(city)

        if not hospitals:
            raise Exception("No hospitals found nearby!")

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
                    (source_point[0], source_point[1]),
                    (h_lat, h_lon)
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
            raise Exception("No valid hospitals found!")

        candidates.sort(key=lambda c: c["straight_dist"])
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
                h_node = ox.nearest_nodes(G, candidate["lon"], candidate["lat"])

                length = nx.astar_path_length(
                    G, source_node, h_node,
                    heuristic=heuristic, weight="length"
                )

                hospital_list.append({
                    "name": candidate["name"],
                    "coords": [float(candidate["lat"]), float(candidate["lon"])],
                    "distance_km": round(length / 1000, 2)
                })

                if length < best_length:
                    best_length = length
                    best_node = h_node
                    best_hospital = candidate["name"]

            except Exception:
                continue

        if best_node is None:
            raise Exception("Could not find route to any hospital!")

        # ----------------------------------------------------
        # FULL PATH FOR WINNER
        # ----------------------------------------------------

        best_path = nx.astar_path(
            G, source_node, best_node,
            heuristic=heuristic, weight="length"
        )

        hospital_list.sort(key=lambda x: x["distance_km"])

        coordinates = []

        for node in best_path:
            node_data = G.nodes[node]
            coordinates.append([float(node_data["y"]), float(node_data["x"])])

        directions = get_turn_directions(coordinates)

        return {
            "path": coordinates,
            "source": coordinates[0],
            "destination": coordinates[-1],
            "nearest_hospital": best_hospital,
            "hospitals": hospital_list[:10],
            "distance_m": round(best_length),
            "distance_km": round(best_length / 1000, 2),
            "directions": directions
        }

    except Exception as e:
        raise Exception(f"Emergency route error: {str(e)}")


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
            source_point = ox.geocode(f"{source}, {city}")
        except Exception:
            source_point = ox.geocode(f"{source}, {city_short}")

        source_node = ox.nearest_nodes(G, source_point[1], source_point[0])

        # ----------------------------------------------------
        # HOSPITAL NODE
        # ----------------------------------------------------

        h_node = ox.nearest_nodes(G, float(h_lon), float(h_lat))

        # ----------------------------------------------------
        # A* ROUTE
        # ----------------------------------------------------

        path = nx.astar_path(
            G, source_node, h_node,
            heuristic=heuristic, weight="length"
        )

        length = nx.path_weight(G, path, weight="length")

        coordinates = []

        for node in path:
            node_data = G.nodes[node]
            coordinates.append([float(node_data["y"]), float(node_data["x"])])

        directions = get_turn_directions(coordinates)

        return {
            "path": coordinates,
            "source": coordinates[0],
            "destination": coordinates[-1],
            "nearest_hospital": h_name,
            "distance_m": round(length),
            "distance_km": round(length / 1000, 2),
            "directions": directions
        }

    except Exception as e:
        raise Exception(f"Hospital route error: {str(e)}")