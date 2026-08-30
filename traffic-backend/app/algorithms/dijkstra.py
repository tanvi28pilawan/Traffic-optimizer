import os
import math
import osmnx as ox
import networkx as nx

from .geo_utils import get_turn_directions, distance_m
from .graph_loader import get_graph


# ============================================================
# A* HEURISTIC
# ============================================================

def _make_heuristic(G):
    """
    Create a lightweight geographic heuristic for A*.

    Uses straight-line distance between nodes instead of
    calculating routes repeatedly.
    """

    def heuristic(u, v):

        u_data = G.nodes[u]
        v_data = G.nodes[v]

        try:
            return distance_m(
                float(u_data["y"]),
                float(u_data["x"]),
                float(v_data["y"]),
                float(v_data["x"])
            )

        except Exception:
            return 0

    return heuristic


# ============================================================
# ROUTE CALCULATION
# ============================================================

def calculate_route(
    source: str,
    destination: str,
    city: str
):
    """
    Calculate the shortest route between source and destination.

    Graph loading is handled entirely by graph_loader.py.

    Priority handled by graph_loader:
        1. In-memory graph
        2. Local graph_cache
        3. GitHub Release prebuilt graph
        4. Overpass as last resort
    """

    try:

        # ----------------------------------------------------
        # LOAD GRAPH
        # ----------------------------------------------------

        G = get_graph(city)

        # ----------------------------------------------------
        # CITY NAME
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # GEOCODE DESTINATION
        # ----------------------------------------------------

        try:

            destination_point = ox.geocode(
                f"{destination}, {city}"
            )

        except Exception:

            destination_point = ox.geocode(
                f"{destination}, {city_short}"
            )

        # ----------------------------------------------------
        # FIND NEAREST ROAD NODES
        # ----------------------------------------------------

        source_node = ox.nearest_nodes(
            G,
            source_point[1],
            source_point[0]
        )

        destination_node = ox.nearest_nodes(
            G,
            destination_point[1],
            destination_point[0]
        )

        # ----------------------------------------------------
        # CREATE A* HEURISTIC
        # ----------------------------------------------------

        heuristic = _make_heuristic(G)

        # ----------------------------------------------------
        # FIND SHORTEST PATH
        # ----------------------------------------------------

        path = nx.astar_path(
            G,
            source_node,
            destination_node,
            heuristic=heuristic,
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
        # CALCULATE DISTANCE
        # ----------------------------------------------------

        length = nx.path_weight(
            G,
            path,
            weight="length"
        )

        # ----------------------------------------------------
        # TURN-BY-TURN DIRECTIONS
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

            "distance_m": round(length),

            "distance_km": round(
                length / 1000,
                2
            ),

            "directions": directions
        }

    except Exception as e:

        raise Exception(
            f"Route not found: {str(e)}"
        )