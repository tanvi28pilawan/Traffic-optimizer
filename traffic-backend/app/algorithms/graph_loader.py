import os
import requests
import osmnx as ox
import json
import math

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

    tmp_file = cache_file + ".tmp"

    try:
        os.makedirs(CACHE_DIR, exist_ok=True)

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


# ============================================================
# SHARED HOSPITAL CACHE
# (same RAM-dict pattern as the graph cache above, so
# emergency.py / normal.py / delivery.py all share ONE copy
# of the hospital list per city instead of three.)
# ============================================================

_hospital_cache = {}

HOSPITAL_CACHE_DIR = os.path.join(BASE_DIR, "hospital_cache")


def _hospital_cache_file(city: str) -> str:
    return os.path.join(
        HOSPITAL_CACHE_DIR,
        f"{_safe_filename(city)}.json"
    )


def _save_hospitals_to_disk(city: str, hospital_data: list):
    """
    Save the already-filtered hospital list (list of {name, lat, lon}
    dicts) to disk. Must receive the FILTERED list, not the raw OSM
    GeoDataFrame, or vet/pet/animal clinics would reappear on every
    subsequent disk-cache read.
    """
    try:
        os.makedirs(HOSPITAL_CACHE_DIR, exist_ok=True)

        with open(
            _hospital_cache_file(city), "w", encoding="utf-8"
        ) as f:
            json.dump(hospital_data, f, ensure_ascii=False, indent=2)

        print(
            f"[SHARED HOSPITALS] Saved "
            f"{len(hospital_data)} hospitals for {city}"
        )

    except Exception as e:
        print(f"[SHARED HOSPITALS] Could not save hospitals: {e}")


def _load_hospitals_from_disk(city: str):
    cache_file = _hospital_cache_file(city)

    if not os.path.exists(cache_file):
        return None

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            hospital_data = json.load(f)

        if not hospital_data:
            return None

        print(
            f"[SHARED HOSPITALS] Loaded "
            f"{len(hospital_data)} hospitals from disk for {city}"
        )
        return hospital_data

    except Exception as e:
        print(f"[SHARED HOSPITALS] Could not load cache: {e}")
        return None


def get_hospitals(city: str):
    city = _normalize_city(city)

    # 1. RAM cache
    if city in _hospital_cache:
        print(f"[SHARED HOSPITALS] Using in-memory hospitals for {city}")
        return _hospital_cache[city]

    # 2. Disk cache
    cached_hospitals = _load_hospitals_from_disk(city)

    if cached_hospitals is not None:
        _hospital_cache[city] = cached_hospitals
        return cached_hospitals

    # 3. OSM/Overpass
    print(f"[SHARED HOSPITALS] Fetching hospitals from OSM for {city}...")

    try:
        hospitals = ox.features_from_place(city, tags={"amenity": "hospital"})
    except Exception as e:
        raise Exception(
            f"Could not fetch hospitals for {city}. "
            f"OpenStreetMap/Overpass may be temporarily unavailable. "
            f"Details: {str(e)}"
        )

    hospital_data = []

    if not hospitals.empty:
        for _, hospital in hospitals.iterrows():
            try:
                geometry = hospital.geometry

                if geometry is None:
                    continue

                if geometry.geom_type == "Point":
                    lat = float(geometry.y)
                    lon = float(geometry.x)
                else:
                    centroid = geometry.centroid
                    lat = float(centroid.y)
                    lon = float(centroid.x)

                if math.isnan(lat) or math.isnan(lon):
                    continue

                name = hospital.get("name", "Unknown Hospital")

                if not isinstance(name, str):
                    name = "Unknown Hospital"

                name_lower = name.lower()

                if any(word in name_lower for word in ["vet", "pet", "animal"]):
                    continue

                hospital_data.append({"name": name, "lat": lat, "lon": lon})

            except Exception:
                continue

    if not hospital_data:
        raise Exception("No hospitals found nearby!")

    _hospital_cache[city] = hospital_data
    _save_hospitals_to_disk(city, hospital_data)

    return hospital_data