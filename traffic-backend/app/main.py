from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from .database import engine, Base
from .routers import auth, route
import threading
import os
from dotenv import load_dotenv

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TrafficOpt API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Email config
mail_config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

app.state.mail = FastMail(mail_config)

app.include_router(auth.router)
app.include_router(route.router)

def preload_graphs():
    from .algorithms.dijkstra import get_graph
    cities = [
        "Chhatrapati Sambhajinagar, Maharashtra, India",
        "Pune, Maharashtra, India",
        "Nagpur, Maharashtra, India",
        "Bangalore, Karnataka, India",
    ]
    for city in cities:
        try:
            print(f"Preloading {city}...")
            get_graph(city)
        except Exception as e:
            print(f"Failed to preload {city}: {e}")

@app.on_event("startup")
async def startup_event():
    thread = threading.Thread(target=preload_graphs, daemon=True)
    thread.start()

@app.get("/")
def root():
    return {"message": "TrafficOpt API is running!"}