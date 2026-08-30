import os
import requests
import osmnx as ox

# ============================================================
# SHARED GRAPH CACHE
# ============================================================

_graph_cache = {}

# traffic-backend/app/graph_cache/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "graph_cache")

GRAPH_CACHE_BASE_URL = os.getenv(
    "GRAPH_CACHE_BASE_URL",
    "https://github.com/tanvi28pilawan/Traffic-optimizer/releases/download/v1-graphs"
).rstrip("/")


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


def _cache_file(city: str) -> str:
    return os.path.join(
        CACHE_DIR,
        f"{_safe_filename(city)}.graphml"
    )


# ============================================================
# DOWNLOAD GRAPH FROM GITHUB RELEASE
# ============================================================

def _download_graph(city: str, cache_file: str) -> bool:

    filename = os.path.basename(cache_file)
    url = f"{GRAPH_CACHE_BASE_URL}/{filename}"

    print(f"[SHARED GRAPH] Downloading {filename}...")

    try:
        os.makedirs(CACHE_DIR, exist_ok=True)

        tmp_file = cache_file + ".tmp"

        with requests.get(
            url,
            stream=True,
            timeout=300,
            headers={"User-Agent": "Traffic-Optimizer"}
        ) as response:

            response.raise_for_status()

            with open(tmp_file, "wb") as f:
                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):
                    if chunk:
                        f.write(chunk)

        os.replace(tmp_file, cache_file)

        print(f"[SHARED GRAPH] Downloaded {filename}")
        return True

    except Exception as e:

        print(
            f"[SHARED GRAPH] Download failed for "
            f"{city}: {e}"
        )

        try:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
        except Exception:
            pass

        return False


# ============================================================
# GET GRAPH
# ============================================================

def get_graph(city: str):

    city = _normalize_city(city)

    # --------------------------------------------------------
    # 1. RAM CACHE
    # --------------------------------------------------------

    if city in _graph_cache:

        print(
            f"[SHARED GRAPH] Using in-memory graph "
            f"for {city}"
        )

        return _graph_cache[city]

    # --------------------------------------------------------
    # 2. DISK CACHE
    # --------------------------------------------------------

    os.makedirs(CACHE_DIR, exist_ok=True)

    cache_file = _cache_file(city)

    # --------------------------------------------------------
    # 3. DOWNLOAD FROM RELEASE IF NEEDED
    # --------------------------------------------------------

    if not os.path.exists(cache_file):

        _download_graph(city, cache_file)

    # --------------------------------------------------------
    # 4. LOAD GRAPH FROM DISK
    # --------------------------------------------------------

    if os.path.exists(cache_file):

        try:

            print(
                f"[SHARED GRAPH] Loading graph "
                f"from disk for {city}..."
            )

            G = ox.load_graphml(cache_file)

            _graph_cache[city] = G

            print(
                f"[SHARED GRAPH] Graph loaded "
                f"for {city}!"
            )

            return G

        except Exception as e:

            print(
                f"[SHARED GRAPH] Could not load "
                f"cached graph: {e}"
            )

            try:
                os.remove(cache_file)
            except Exception:
                pass

    # --------------------------------------------------------
    # 5. LAST RESORT — OVERPASS
    # --------------------------------------------------------

    print(
        f"[SHARED GRAPH] No cached graph found "
        f"for {city}. Downloading from Overpass..."
    )

    try:

        G = ox.graph_from_place(
            city,
            network_type="drive"
        )

        try:
            ox.save_graphml(G, cache_file)
        except Exception as e:
            print(
                f"[SHARED GRAPH] Could not save graph: {e}"
            )

        _graph_cache[city] = G

        return G

    except Exception as e:

        raise Exception(
            f"Unable to load road network for {city}. "
            f"Details: {str(e)}"
        )