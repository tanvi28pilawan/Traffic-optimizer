import os
import osmnx as ox
import networkx as nx

from .geo_utils import get_turn_directions, make_heuristic
from .graph_loader import get_graph


# ============================================================
# OVERPASS CONFIG
# ============================================================
# Overpass is kept only as a last-resort fallback inside the
# shared graph_loader. Delivery does NOT maintain its own graph
# cache, so it cannot create a second copy of the same city graph.
ox.settings.overpass_url = os.getenv(
    "OVERPASS_URL",
    "https://overpass.kumi.systems/api"
)
ox.settings.overpass_rate_limit = True


# ============================================================
# DELIVERY ROUTE
# ============================================================

# ============================================================

def get_delivery_route(
    source: str,
    stops: list,
    city: str = "Chhatrapati Sambhajinagar, Maharashtra, India"
):
    """
    Calculate a delivery route using A*.

    Stops are ordered using a nearest-next-stop strategy:
    - Start from source.
    - Find the closest unvisited stop using A* distance.
    - Visit that stop.
    - Repeat until all stops are visited.

    This is a greedy heuristic for the multi-stop delivery problem.
    """

    try:
        city = _normalize_city(city)

        # ----------------------------------------------------
        # Validate stops
        # ----------------------------------------------------

        if not stops or not isinstance(stops, list):
            raise Exception(
                "Please provide at least one delivery stop."
            )

        # Remove empty/invalid stop names
        valid_stops = []

        for stop in stops:
            if isinstance(stop, str) and stop.strip():
                valid_stops.append(stop.strip())

        if not valid_stops:
            raise Exception(
                "No valid delivery stops provided."
            )

        # ----------------------------------------------------
        # Load graph
        # ----------------------------------------------------

        G = get_graph(city)

        heuristic = make_heuristic(G)

        city_short = city.split(",")[0].strip()

        # ----------------------------------------------------
        # Geocode source
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
        # Geocode all delivery stops
        # ----------------------------------------------------

        stop_nodes = []
        stop_coords = []

        for stop in valid_stops:

            try:
                point = ox.geocode(
                    f"{stop}, {city}"
                )
            except Exception:
                point = ox.geocode(
                    f"{stop}, {city_short}"
                )

            node = ox.nearest_nodes(
                G,
                point[1],
                point[0]
            )

            stop_nodes.append(node)

            stop_coords.append({
                "name": stop,
                "coords": [
                    float(point[0]),
                    float(point[1])
                ]
            })

        if not stop_nodes:
            raise Exception(
                "Could not locate any delivery stops."
            )

        # ----------------------------------------------------
        # Greedy nearest-stop ordering
        # ----------------------------------------------------

        unvisited = list(range(len(stop_nodes)))

        current_node = source_node

        ordered_stops = []
        ordered_coords = []

        while unvisited:

            nearest_node = None
            nearest_distance = float("inf")
            nearest_index = None

            for idx in unvisited:

                try:
                    distance = nx.astar_path_length(
                        G,
                        current_node,
                        stop_nodes[idx],
                        heuristic=heuristic,
                        weight="length"
                    )

                    if distance < nearest_distance:
                        nearest_distance = distance
                        nearest_node = stop_nodes[idx]
                        nearest_index = idx

                except Exception:
                    continue

            # No reachable stop
            if nearest_node is None:
                break

            ordered_stops.append(nearest_node)

            ordered_coords.append(
                stop_coords[nearest_index]
            )

            unvisited.remove(nearest_index)

            current_node = nearest_node

        # If some stops could not be reached
        if unvisited:
            unreachable_names = [
                stop_coords[idx]["name"]
                for idx in unvisited
            ]

            print(
                f"Warning: unreachable stops: "
                f"{unreachable_names}"
            )

        if not ordered_stops:
            raise Exception(
                "Could not find a route to any delivery stop."
            )

        # ----------------------------------------------------
        # Build complete route
        # ----------------------------------------------------

        all_nodes = [
            source_node
        ] + ordered_stops

        full_path = []
        total_length = 0.0

        for i in range(len(all_nodes) - 1):

            start_node = all_nodes[i]
            end_node = all_nodes[i + 1]

            try:
                segment = nx.astar_path(
                    G,
                    start_node,
                    end_node,
                    heuristic=heuristic,
                    weight="length"
                )

                segment_length = nx.path_weight(
                    G,
                    segment,
                    weight="length"
                )

                total_length += segment_length

                # Add segment coordinates
                # Skip first node of subsequent segments
                # to prevent duplicate points.
                start_index = 0 if i == 0 else 1

                for node in segment[start_index:]:

                    node_data = G.nodes[node]

                    full_path.append([
                        float(node_data["y"]),
                        float(node_data["x"])
                    ])

            except Exception:
                continue

        if not full_path:
            raise Exception(
                "Could not construct the delivery route."
            )

        # ----------------------------------------------------
        # Turn-by-turn directions
        # ----------------------------------------------------

        directions = get_turn_directions(
            full_path
        )

        # ----------------------------------------------------
        # Response
        # ----------------------------------------------------

        return {
            "path": full_path,
            "source": full_path[0],
            "destination": full_path[-1],
            "stops": ordered_coords,
            "distance_m": round(total_length),
            "distance_km": round(
                total_length / 1000,
                2
            ),
            "directions": directions
        }

    except Exception as e:

        raise Exception(
            f"Delivery route error: {str(e)}"
        )