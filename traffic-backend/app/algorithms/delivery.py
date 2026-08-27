import os
import osmnx as ox
import networkx as nx

from .geo_utils import get_turn_directions   # <-- ADD THIS IMPORT

_graph_cache = {}
CACHE_DIR = "graph_cache"

def get_graph(city: str):
    city = ", ".join(part.strip().title() for part in city.split(","))

    if city in _graph_cache:
        return _graph_cache[city]

    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"{city.replace(', ', '_').replace(' ', '_')}.graphml")

    if os.path.exists(cache_file):
        print(f"Loading graph from disk for {city}...")
        _graph_cache[city] = ox.load_graphml(cache_file)
        print(f"Graph loaded for {city}!")
    else:
        print(f"Downloading graph for {city}...")
        _graph_cache[city] = ox.graph_from_place(city, network_type="drive")
        ox.save_graphml(_graph_cache[city], cache_file)
        print(f"Graph downloaded and saved for {city}!")

    return _graph_cache[city]

def get_delivery_route(source: str, stops: list, city: str = "Chhatrapati Sambhajinagar, Maharashtra, India"):
    try:
        G = get_graph(city)

        city_short = city.split(",")[0].strip()

        try:
            source_point = ox.geocode(f"{source}, {city}")
        except Exception:
            source_point = ox.geocode(f"{source}, {city_short}")

        source_node = ox.nearest_nodes(G, source_point[1], source_point[0])

        stop_nodes = []
        stop_coords = []
        for stop in stops:
            try:
                point = ox.geocode(f"{stop}, {city}")
            except Exception:
                point = ox.geocode(f"{stop}, {city_short}")
            node = ox.nearest_nodes(G, point[1], point[0])
            stop_nodes.append(node)
            stop_coords.append({"name": stop, "coords": [point[0], point[1]]})

        unvisited = list(range(len(stop_nodes)))
        current_node = source_node
        ordered_stops = []
        ordered_coords = []

        while unvisited:
            nearest = None
            nearest_dist = float("inf")
            nearest_idx = None

            for idx in unvisited:
                try:
                    dist = nx.shortest_path_length(G, current_node, stop_nodes[idx], weight="length")
                    if dist < nearest_dist:
                        nearest_dist = dist
                        nearest = stop_nodes[idx]
                        nearest_idx = idx
                except Exception:
                    continue

            if nearest is None:
                break

            ordered_stops.append(nearest)
            ordered_coords.append(stop_coords[nearest_idx])
            unvisited.remove(nearest_idx)
            current_node = nearest

        all_nodes = [source_node] + ordered_stops
        full_path = []
        total_length = 0

        for i in range(len(all_nodes) - 1):
            segment = nx.shortest_path(G, all_nodes[i], all_nodes[i+1], weight="length")
            length = nx.shortest_path_length(G, all_nodes[i], all_nodes[i+1], weight="length")
            total_length += length
            for node in segment:
                node_data = G.nodes[node]
                full_path.append([node_data["y"], node_data["x"]])

        directions = get_turn_directions(full_path)   # <-- ADD THIS LINE

        return {
            "path": full_path,
            "source": full_path[0] if full_path else None,
            "destination": full_path[-1] if full_path else None,
            "stops": ordered_coords,
            "distance_m": round(total_length),
            "distance_km": round(total_length / 1000, 2),
            "directions": directions   # <-- ADD THIS KEY
        }

    except Exception as e:
        raise Exception(f"Delivery route error: {str(e)}")