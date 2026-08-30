import os
from dotenv import load_dotenv

# IMPORTANT: this must run BEFORE importing routers/algorithms below,
# because those modules read env vars like OVERPASS_URL at import
# time (module-level code), not inside a function. If load_dotenv()
# runs after they're imported, os.getenv() calls inside them return
# the fallback default instead of the .env value.
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mail import FastMail, ConnectionConfig

from .database import engine, Base
from .routers import auth, route

import time
import threading


# ============================================================
# ENVIRONMENT
# ============================================================

# Overpass endpoint is now configurable via env var. Overpass's public
# instance (overpass-api.de) blocks/rate-limits a lot of cloud hosting
# IP ranges (Render/Railway/AWS/etc.), which is the most common cause
# of "Connection refused" in production even though it works locally.
# Set OVERPASS_URL in your production env to a mirror if the default
# gets blocked, e.g.:
#   https://overpass.kumi.systems/api
#   https://overpass.openstreetmap.ru/api
OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api")
os.environ["OVERPASS_URL"] = OVERPASS_URL  # so algorithms/*.py can read it too

REQUIRED_MAIL_VARS = [
    "MAIL_USERNAME",
    "MAIL_PASSWORD",
    "MAIL_FROM",
    "MAIL_SERVER",
]


# ============================================================
# DATABASE
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(title="TrafficOpt API")


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# EMAIL CONFIGURATION
# ============================================================

def build_mail_config():
    """
    Build the FastMail config, but fail loudly (in logs) instead of
    silently, if required env vars are missing. This is the #1 cause
    of "mail not found" / mail-send failures in production: the local
    .env file is never deployed, so these os.getenv() calls silently
    return None unless the variables are also set on the hosting
    platform itself (Render/Railway/etc. dashboard -> Environment).
    """
    missing = [var for var in REQUIRED_MAIL_VARS if not os.getenv(var)]
    if missing:
        print("=" * 60)
        print("[MAIL CONFIG] WARNING: missing env vars:", ", ".join(missing))
        print("[MAIL CONFIG] Forgot-password / any email-sending endpoint")
        print("[MAIL CONFIG] WILL FAIL until these are set in production env.")
        print("=" * 60)

    return ConnectionConfig(
        MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
        MAIL_FROM=os.getenv("MAIL_FROM", "noreply@example.com"),
        MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
        MAIL_SERVER=os.getenv("MAIL_SERVER", ""),
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
    )


mail_config = build_mail_config()
app.state.mail = FastMail(mail_config)


# ============================================================
# ROUTERS
# ============================================================

app.include_router(auth.router)
app.include_router(route.router)


# ============================================================
# DOWNLOAD GRAPH CACHE FROM GITHUB RELEASE
# ============================================================

import requests

GITHUB_GRAPH_RELEASE = (
    "https://github.com/tanvi28pilawan/Traffic-optimizer"
    "/releases/download/v1-graphs/"
)

GRAPH_CACHE_DIR = os.path.join(
    os.path.dirname(__file__),
    "graph_cache"
)

GRAPH_FILES = [
    "Bangalore_Karnataka_India.graphml",
    "Chhatrapati_Sambhajinagar_Maharashtra_India.graphml",
    "Nagpur_Maharashtra_India.graphml",
    "Pune_Maharashtra_India.graphml",
]


def download_graph_cache():
    """
    Download pre-generated graph files from the GitHub Release
    if they are not already present locally.
    """

    os.makedirs(GRAPH_CACHE_DIR, exist_ok=True)

    for filename in GRAPH_FILES:
        filepath = os.path.join(GRAPH_CACHE_DIR, filename)

        # Don't download again if the file already exists.
        if os.path.exists(filepath):
            print(f"[GRAPH CACHE] Already exists: {filename}")
            continue

        url = GITHUB_GRAPH_RELEASE + filename

        try:
            print(f"[GRAPH CACHE] Downloading {filename}...")

            response = requests.get(
                url,
                stream=True,
                timeout=300,
                headers={"User-Agent": "Traffic-Optimizer"}
            )
            response.raise_for_status()

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

            print(f"[GRAPH CACHE] Downloaded: {filename}")

        except Exception as e:
            print(f"[GRAPH CACHE] FAILED for {filename}: {e}")
# ============================================================
# GRAPH PRELOADING
# ============================================================

def preload_graphs(retries: int = 3, backoff_seconds: int = 5):
    """
    Preload road graphs for all supported cities.

    The graphs are downloaded only if they are not already
    present in graph_cache/.

    Once downloaded, they are loaded from disk on future
    requests instead of downloading them again.

    NOTE: if this keeps failing in production with "Connection
    refused" from overpass-api.de, that host is very likely
    blocking your hosting provider's IP range. The most reliable
    fix is to pre-generate graph_cache/*.graphml locally (where
    Overpass works) and ship that folder with the deployment, so
    no live Overpass call is ever needed at runtime. OVERPASS_URL
    env var lets you point at a mirror as a second option.
    """

    cities = [
        "Chhatrapati Sambhajinagar, Maharashtra, India",
        "Pune, Maharashtra, India",
        "Nagpur, Maharashtra, India",
        "Bangalore, Karnataka, India",
    ]

    try:
        # Import the shared graph loader from the routing modules.
        from .algorithms.dijkstra import get_graph as get_normal_graph
        from .algorithms.emergency import get_graph as get_emergency_graph
        from .algorithms.delivery import get_graph as get_delivery_graph

    except Exception as e:
        print(f"Could not import graph modules: {e}")
        return

    def load_with_retry(label, loader_fn, city):
        for attempt in range(1, retries + 1):
            try:
                print(f"[{label}] Loading graph for {city} (attempt {attempt}/{retries})...")
                loader_fn(city)
                print(f"[{label}] Graph ready for {city}!")
                return
            except Exception as e:
                print(f"[{label}] Attempt {attempt} failed for {city}: {e}")
                if attempt < retries:
                    time.sleep(backoff_seconds * attempt)  # simple linear backoff
        print(f"[{label}] Giving up on {city} after {retries} attempts.")
        print(f"[{label}] If this is 'Connection refused' from Overpass, your ")
        print(f"[{label}] host's IP is likely blocked — see graph_cache pre-bundling note above.")

    for city in cities:

        print("=" * 60)
        print(f"Preparing graph for: {city}")
        print("=" * 60)

        load_with_retry("NORMAL", get_normal_graph, city)
        load_with_retry("EMERGENCY", get_emergency_graph, city)
        load_with_retry("DELIVERY", get_delivery_graph, city)

    print("=" * 60)
    print("GRAPH PRELOADING COMPLETED")
    print("=" * 60)


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
async def startup_event():

    print("=" * 60)
    print("TrafficOpt API starting...")
    print(f"Overpass endpoint: {OVERPASS_URL}")
    download_graph_cache()
    print("Starting background graph preloading...")
    print("=" * 60)

    # Run graph downloading/loading in the background so that
    # FastAPI can start without blocking the application.
    thread = threading.Thread(
        target=preload_graphs,
        daemon=True
    )

    thread.start()


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "TrafficOpt API is running!"
    }