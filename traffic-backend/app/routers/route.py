from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_db
from ..models import Route, User
from ..schemas import RouteCreate, RouteResponse
from ..auth import verify_token
from ..algorithms.dijkstra import get_shortest_path
from ..algorithms.emergency import get_emergency_route, get_route_to_hospital
from ..algorithms.delivery import get_delivery_route
from fastapi.security import OAuth2PasswordBearer
from typing import List

router = APIRouter(prefix="/route", tags=["route"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

class HospitalSelect(BaseModel):
    source: str
    city: str = "Chhatrapati Sambhajinagar, Maharashtra, India"
    hospital_lat: float
    hospital_lon: float
    hospital_name: str

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

@router.post("/normal")
def normal_route(data: RouteCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        result = get_shortest_path(data.source, data.destination, data.city)
        new_route = Route(mode="normal", source=data.source, destination=data.destination, user_id=current_user.id)
        db.add(new_route)
        db.commit()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/emergency")
def emergency_route(data: RouteCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        result = get_emergency_route(data.source, data.city)
        new_route = Route(mode="emergency", source=data.source, destination=result.get("nearest_hospital", ""), user_id=current_user.id)
        db.add(new_route)
        db.commit()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/emergency/select")
def emergency_select_hospital(data: HospitalSelect, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        result = get_route_to_hospital(data.source, data.hospital_lat, data.hospital_lon, data.hospital_name, data.city)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/delivery")
def delivery_route(data: RouteCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        if not data.stops or len(data.stops) == 0:
            raise HTTPException(status_code=400, detail="Please provide delivery stops.")
        result = get_delivery_route(data.source, data.stops, data.city)
        new_route = Route(mode="delivery", source=data.source, stops=",".join(data.stops), user_id=current_user.id)
        db.add(new_route)
        db.commit()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history", response_model=List[RouteResponse])
def get_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    routes = db.query(Route).filter(Route.user_id == current_user.id).all()
    return routes