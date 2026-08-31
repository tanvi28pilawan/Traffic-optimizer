import osmnx as ox
import networkx as nx

from .geo_utils import get_turn_directions, make_heuristic
from .graph_loader import get_graph, _normalize_city


# ============================================================
# A* HEURISTIC
# ============================================================




# ============================================================
# NORMAL SHORTEST ROUTE
# ============================================================

def get_shortest_path(
    source: str,
    destination: str,
    city: str = "Chhatrapati Sambhajinagar, Maharashtra, India"
):
    """
    Calculate the shortest route between source
    and destination using A*.

    Road graphs are loaded from the shared graph_loader cache
    (same graph object used by emergency and delivery modes).
    """

    try:

        city = _normalize_city(city)

        # ----------------------------------------------------
        # LOAD GRAPH (shared cache from graph_loader.py)
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
            source_point = ox.geocode(f"{source}, {city}")
        except Exception:
            source_point = ox.geocode(f"{source}, {city_short}")

        # ----------------------------------------------------
        # GEOCODE DESTINATION
        # ----------------------------------------------------

        try:
            destination_point = ox.geocode(f"{destination}, {city}")
        except Exception:
            destination_point = ox.geocode(f"{destination}, {city_short}")

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

        heuristic = make_heuristic(G)

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

        directions = get_turn_directions(coordinates)

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {
            "path": coordinates,
            "source": coordinates[0],
            "destination": coordinates[-1],
            "distance_m": round(length),
            "distance_km": round(length / 1000, 2),
            "directions": directions
        }

    except Exception as e:

        raise Exception(
            f"Route not found: {str(e)}"
        )