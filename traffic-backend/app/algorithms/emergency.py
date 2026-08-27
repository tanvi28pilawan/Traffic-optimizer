import os
import osmnx as ox
import networkx as nx
import math

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

def get_emergency_route(source: str, city: str = "Chhatrapati Sambhajinagar, Maharashtra, India"):
    try:
        G = get_graph(city)

        city_short = city.split(",")[0].strip()
        try:
            source_point = ox.geocode(f"{source}, {city}")
        except Exception:
            source_point = ox.geocode(f"{source}, {city_short}")

        source_node = ox.nearest_nodes(G, source_point[1], source_point[0])

        hospitals = ox.features_from_place(city, tags={"amenity": "hospital"})

        if hospitals.empty:
            raise Exception("No hospitals found nearby!")

        if "name" in hospitals.columns:
            hospitals = hospitals[
                ~hospitals["name"].str.lower().str.contains("vet|pet|animal|clinic", na=False)
            ]

        hospital_list = []
        best_path = None
        best_length = float("inf")
        best_hospital = None

        for idx, hospital in hospitals.iterrows():
            try:
                if hospital.geometry.geom_type == "Point":
                    h_lat = hospital.geometry.y
                    h_lon = hospital.geometry.x
                else:
                    h_lat = hospital.geometry.centroid.y
                    h_lon = hospital.geometry.centroid.x

                if math.isnan(h_lat) or math.isnan(h_lon):
                    continue

                h_node = ox.nearest_nodes(G, h_lon, h_lat)
                length = nx.shortest_path_length(G, source_node, h_node, weight="length")

                hospital_name = hospital.get("name", "Unknown Hospital")
                if not isinstance(hospital_name, str):
                    hospital_name = "Unknown Hospital"

                hospital_list.append({
                    "name": hospital_name,
                    "coords": [float(h_lat), float(h_lon)],
                    "distance_km": round(length / 1000, 2)
                })

                if length < best_length:
                    best_length = length
                    best_path = nx.shortest_path(G, source_node, h_node, weight="length")
                    best_hospital = hospital_name

            except Exception:
                continue

        if not best_path:
            raise Exception("Could not find route to any hospital!")

        hospital_list.sort(key=lambda x: x["distance_km"])

        coordinates = []
        for node in best_path:
            node_data = G.nodes[node]
            coordinates.append([float(node_data["y"]), float(node_data["x"])])

        directions = get_turn_directions(coordinates)   # <-- ADD THIS LINE

        return {
            "path": coordinates,
            "source": coordinates[0],
            "destination": coordinates[-1],
            "nearest_hospital": best_hospital,
            "hospitals": hospital_list[:10],
            "distance_m": round(best_length),
            "distance_km": round(best_length / 1000, 2),
            "directions": directions   # <-- ADD THIS KEY
        }

    except Exception as e:
        raise Exception(f"Emergency route error: {str(e)}")


def get_route_to_hospital(source: str, h_lat: float, h_lon: float, h_name: str, city: str = "Chhatrapati Sambhajinagar, Maharashtra, India"):
    try:
        G = get_graph(city)

        city_short = city.split(",")[0].strip()
        try:
            source_point = ox.geocode(f"{source}, {city}")
        except Exception:
            source_point = ox.geocode(f"{source}, {city_short}")

        source_node = ox.nearest_nodes(G, source_point[1], source_point[0])
        h_node = ox.nearest_nodes(G, h_lon, h_lat)

        path = nx.shortest_path(G, source_node, h_node, weight="length")
        length = nx.shortest_path_length(G, source_node, h_node, weight="length")

        coordinates = []
        for node in path:
            node_data = G.nodes[node]
            coordinates.append([float(node_data["y"]), float(node_data["x"])])

        directions = get_turn_directions(coordinates)   # <-- ADD THIS LINE

        return {
            "path": coordinates,
            "source": coordinates[0],
            "destination": coordinates[-1],
            "nearest_hospital": h_name,
            "distance_m": round(length),
            "distance_km": round(length / 1000, 2),
            "directions": directions   # <-- ADD THIS KEY
        }

    except Exception as e:
        raise Exception(f"Hospital route error: {str(e)}")