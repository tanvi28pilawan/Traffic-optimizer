import os
import osmnx as ox
import networkx as nx

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

def get_shortest_path(source: str, destination: str, city: str = "Chhatrapati Sambhajinagar, Maharashtra, India"):
    try:
        G = get_graph(city)

        city_short = city.split(",")[0].strip()

        try:
            source_point = ox.geocode(f"{source}, {city}")
        except Exception:
            source_point = ox.geocode(f"{source}, {city_short}")

        try:
            dest_point = ox.geocode(f"{destination}, {city}")
        except Exception:
            dest_point = ox.geocode(f"{destination}, {city_short}")

        source_node = ox.nearest_nodes(G, source_point[1], source_point[0])
        dest_node = ox.nearest_nodes(G, dest_point[1], dest_point[0])

        path = nx.shortest_path(G, source_node, dest_node, weight="length")

        coordinates = []
        for node in path:
            node_data = G.nodes[node]
            coordinates.append([node_data["y"], node_data["x"]])

        length = nx.shortest_path_length(G, source_node, dest_node, weight="length")

        return {
            "path": coordinates,
            "source": coordinates[0],
            "destination": coordinates[-1],
            "distance_m": round(length),
            "distance_km": round(length / 1000, 2)
        }
    except Exception as e:
        raise Exception(f"Route not found: {str(e)}")