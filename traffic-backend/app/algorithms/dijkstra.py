import os
import requests
import osmnx as ox
import networkx as nx

from .geo_utils import get_turn_directions, distance_m

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
# The .graphml files are too large (100MB+) for a normal git push
# (GitHub's hard limit is 100MB per file). Instead of committing
# them to the repo, upload them as assets on a GitHub Release and
# point this env var at the release's base download URL, e.g.:
#
#   GRAPH_CACHE_BASE_URL=https://github.com/<user>/<repo>/releases/download/v1-graphs
#
# On first request for a city (cold start on Render, since the
# disk is ephemeral there), we download the matching .graphml from
# this URL instead of hitting Overpass at all. If this env var is
# not set, or the download fails, we fall back to live Overpass
# download exactly as before.
GRAPH_CACHE_BASE_URL = os.getenv("GRAPH_CACHE_BASE_URL", "").rstrip("/")


# ============================================================
# GRAPH CACHE
# ============================================================

# In-memory cache
_graph_cache = {}

# dijkstra.py is inside:
# traffic-backend/app/algorithms/
#
# We need:
# traffic-backend/app/graph_cache/
#
# FIX: this must match the SAME folder delivery.py and emergency.py
# use, otherwise each mode re-downloads its own separate copy of the
# same city's graph instead of sharing one cache.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CACHE_DIR = os.path.join(BASE_DIR, "graph_cache")


# ============================================================
# CITY / CACHE HELPERS
# ============================================================

def _normalize_city(city: str) -> str:
    """
    Normalize city name so the same city always uses
    the same cache key and filename.
    """
    return ", ".join(
        part.strip().title()
        for part in city.split(",")
    )


def _cache_filename(city: str) -> str:
    """
    Generate the GraphML cache filename.
    """
    filename = (
        city
        .replace(", ", "_")
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )
    return os.path.join(
        CACHE_DIR,
        f"{filename}.graphml"
    )


def _try_download_from_release(city: str, cache_file: str) -> bool:
    """
    Attempt to download a prebuilt .graphml for this city from a
    GitHub Release (or any static file host) into cache_file.

    Returns True if the file was downloaded successfully, False
    otherwise (missing env var, 404, network error, etc.) so the
    caller can fall back to live Overpass download.
    """

    if not GRAPH_CACHE_BASE_URL:
        return False

    filename = os.path.basename(cache_file)
    url = f"{GRAPH_CACHE_BASE_URL}/{filename}"

    print(f"[GRAPH] Trying prebuilt graph download for {city}...")
    print(f"[GRAPH] {url}")

    try:
        with requests.get(url, stream=True, timeout=60) as resp:
            if resp.status_code != 200:
                print(
                    f"[GRAPH] Prebuilt graph not available "
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

        print(f"[GRAPH] Prebuilt graph downloaded for {city}!")
        return True

    except Exception as e:
        print(f"[GRAPH] Prebuilt graph download failed for {city}: {e}")
        return False


# ============================================================
# GRAPH LOADER
# ============================================================

def get_graph(city: str):
    """
    Load road graph using the following priority:

    1. In-memory cache
    2. Local graph_cache/*.graphml
    3. Prebuilt graph from GitHub Release (GRAPH_CACHE_BASE_URL)
    4. Download from OpenStreetMap/Overpass (last resort)

    Existing graphs are NEVER downloaded again.
    """

    city = _normalize_city(city)

    # --------------------------------------------------------
    # 1. IN-MEMORY CACHE
    # --------------------------------------------------------

    if city in _graph_cache:
        print(f"[GRAPH] Using in-memory graph for {city}")
        return _graph_cache[city]

    # --------------------------------------------------------
    # 2. LOCAL DISK CACHE
    # --------------------------------------------------------

    os.makedirs(CACHE_DIR, exist_ok=True)

    cache_file = _cache_filename(city)

    print(f"[GRAPH] Looking for cached graph:")
    print(f"[GRAPH] {cache_file}")

    if not os.path.exists(cache_file):
        # --------------------------------------------------------
        # 3. TRY PREBUILT GRAPH FROM GITHUB RELEASE
        # --------------------------------------------------------
        _try_download_from_release(city, cache_file)

    if os.path.exists(cache_file):

        try:
            print(f"[GRAPH] Loading graph from disk for {city}...")

            G = ox.load_graphml(cache_file)

            _graph_cache[city] = G

            print(f"[GRAPH] Graph loaded successfully for {city}!")

            return G

        except Exception as e:

            print(
                f"[GRAPH] Cached graph could not be loaded: {e}"
            )

            # Delete only if the file is actually corrupted
            try:
                os.remove(cache_file)
                print(
                    f"[GRAPH] Removed corrupted cache file: "
                    f"{cache_file}"
                )
            except Exception:
                pass

    # --------------------------------------------------------
    # 4. DOWNLOAD FROM OVERPASS ONLY IF NOTHING ELSE WORKED
    # --------------------------------------------------------

    print(
        f"[GRAPH] No cached/prebuilt graph found for {city}."
    )

    print(
        f"[GRAPH] Downloading road network from "
        f"OpenStreetMap/Overpass..."
    )

    try:

        G = ox.graph_from_place(
            city,
            network_type="drive"
        )

        # ----------------------------------------------------
        # SAVE GRAPH LOCALLY
        # ----------------------------------------------------

        try:

            ox.save_graphml(
                G,
                cache_file
            )

            print(
                f"[GRAPH] Graph downloaded and saved:"
            )

            print(
                f"[GRAPH] {cache_file}"
            )

        except Exception as save_error:

            print(
                f"[GRAPH] WARNING: Graph downloaded but "
                f"could not be saved: {save_error}"
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
# A* HEURISTIC
# ============================================================

def _make_heuristic(G):
    """
    Create the straight-line distance heuristic
    used by A*.
    """

    def heuristic(u, v):

        u_data = G.nodes[u]
        v_data = G.nodes[v]

        return distance_m(
            (
                float(u_data["y"]),
                float(u_data["x"])
            ),
            (
                float(v_data["y"]),
                float(v_data["x"])
            )
        )

    return heuristic


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

    Road graphs are loaded from local cache whenever
    available.
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