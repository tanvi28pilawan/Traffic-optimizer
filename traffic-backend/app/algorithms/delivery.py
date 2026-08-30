import os
import requests
import osmnx as ox
import networkx as nx

from .geo_utils import get_turn_directions, make_heuristic

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
# Same mechanism as dijkstra.py / emergency.py -- the .graphml files
# are too large for a normal git push, so they're uploaded as assets
# on a GitHub Release instead. Set this env var to the release's base
# download URL, e.g.:
#
#   GRAPH_CACHE_BASE_URL=https://github.com/<user>/<repo>/releases/download/v1-graphs
#
# If not set, or the download fails, falls back to live Overpass
# download exactly as before.
GRAPH_CACHE_BASE_URL = os.getenv("GRAPH_CACHE_BASE_URL", "").rstrip("/")


# ============================================================
# CACHE CONFIGURATION
# ============================================================

_graph_cache = {}

# Keep graph cache inside the backend directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "graph_cache")

# ============================================================
# HELPERS
# ============================================================

def _normalize_city(city: str) -> str:
    """Normalize city name for consistent caching."""
    return ", ".join(
        part.strip().title()
        for part in city.split(",")
    )


def _safe_filename(city: str) -> str:
    """Create a safe filename from a city name."""
    return (
        city
        .replace(", ", "_")
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )


def _cache_file(city: str) -> str:
    return os.path.join(
        CACHE_DIR,
        f"{_safe_filename(city)}.graphml"
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

    print(f"[DELIVERY GRAPH] Trying prebuilt graph download for {city}...")
    print(f"[DELIVERY GRAPH] {url}")

    try:
        with requests.get(url, stream=True, timeout=60) as resp:
            if resp.status_code != 200:
                print(
                    f"[DELIVERY GRAPH] Prebuilt graph not available "
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

        print(f"[DELIVERY GRAPH] Prebuilt graph downloaded for {city}!")
        return True

    except Exception as e:
        print(f"[DELIVERY GRAPH] Prebuilt graph download failed for {city}: {e}")
        return False


# ============================================================
# GRAPH LOADING
# ============================================================

def get_graph(city: str):
    """
    Load the road graph for a city.

    Priority:
    1. In-memory cache
    2. Disk GraphML cache
    3. Prebuilt graph from GitHub Release (GRAPH_CACHE_BASE_URL)
    4. Download from OpenStreetMap through OSMnx (last resort)

    Downloaded graphs are saved locally for reuse.
    """

    city = _normalize_city(city)

    # 1. Memory cache
    if city in _graph_cache:
        print(f"Using in-memory graph for {city}...")
        return _graph_cache[city]

    # Ensure cache directory exists
    os.makedirs(CACHE_DIR, exist_ok=True)

    cache_file = _cache_file(city)

    # 2. Disk cache
    if not os.path.exists(cache_file):
        # 3. Try prebuilt graph from GitHub Release
        _try_download_from_release(city, cache_file)

    if os.path.exists(cache_file):
        try:
            print(f"Loading graph from disk for {city}...")

            G = ox.load_graphml(cache_file)

            _graph_cache[city] = G

            print(f"Graph loaded from cache for {city}!")

            return G

        except Exception as e:
            print(
                f"Could not load cached graph for {city}: {e}"
            )

            # Remove corrupted cache
            try:
                os.remove(cache_file)
            except Exception:
                pass

    # 4. Download graph from Overpass only if nothing else worked
    print(f"No cached/prebuilt graph found for {city}.")
    print(f"Downloading road graph for {city}...")

    try:
        G = ox.graph_from_place(
            city,
            network_type="drive"
        )

        # Save graph for future requests
        try:
            ox.save_graphml(G, cache_file)
            print(f"Graph downloaded and cached for {city}!")
        except Exception as e:
            print(
                f"Graph downloaded but could not be cached: {e}"
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
# DELIVERY ROUTE
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