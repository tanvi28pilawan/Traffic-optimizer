import os
from dotenv import load_dotenv

# IMPORTANT: load .env BEFORE importing routers/algorithms
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mail import FastMail, ConnectionConfig

from .database import engine, Base
from .routers import auth, route

import requests


# ============================================================
# ENVIRONMENT
# ============================================================

OVERPASS_URL = os.getenv(
    "OVERPASS_URL",
    "https://overpass-api.de/api"
)

os.environ["OVERPASS_URL"] = OVERPASS_URL

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
    missing = [var for var in REQUIRED_MAIL_VARS if not os.getenv(var)]

    if missing:
        print("=" * 60)
        print(
            "[MAIL CONFIG] WARNING: missing env vars:",
            ", ".join(missing)
        )
        print("[MAIL CONFIG] Email-sending endpoints may fail.")
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

        # Don't download again if already present.
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
                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):
                    if chunk:
                        f.write(chunk)

            print(f"[GRAPH CACHE] Downloaded: {filename}")

        except Exception as e:
            print(
                f"[GRAPH CACHE] FAILED for {filename}: {e}"
            )


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
async def startup_event():

    print("=" * 60)
    print("TrafficOpt API starting...")
    print(f"Overpass endpoint: {OVERPASS_URL}")
    print("Downloading/checking graph cache...")

    # Download graph files from GitHub Release.
    # This is streamed directly to disk and does not load
    # the entire graph into RAM.
    download_graph_cache()

    print("TrafficOpt API startup complete.")
    print("=" * 60)


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "TrafficOpt API is running!"
    }