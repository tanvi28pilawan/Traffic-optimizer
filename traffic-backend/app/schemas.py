from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "normal"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    token: str
    token_type: str
    name: str
    role: str

class RouteCreate(BaseModel):
    mode: str
    source: str
    city: Optional[str] = "Chhatrapati Sambhajinagar, Maharashtra, India"
    destination: Optional[str] = None
    stops: Optional[List[str]] = None
class RouteResponse(BaseModel):
    id: int
    mode: str
    source: str
    destination: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True