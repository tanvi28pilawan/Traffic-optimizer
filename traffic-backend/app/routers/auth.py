import token

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import User, Route, OTP
from ..schemas import UserCreate, UserLogin, Token, UserResponse
from ..auth import hash_password, verify_password, create_access_token, verify_token
from fastapi.security import OAuth2PasswordBearer
from fastapi_mail import MessageSchema, MessageType
from pydantic import BaseModel, EmailStr
import random
import string
from datetime import datetime, timedelta

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

router = APIRouter(prefix="/auth", tags=["auth"])

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str
class UpdateNameRequest(BaseModel):
    name: str
@router.post("/signup", response_model=UserResponse)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    new_user = User(
    name=user.name,
    email=user.email,
    hashed_password=hash_password(user.password),
    role=user.role
)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    token = create_access_token({"sub": str(db_user.id), "email": db_user.email})
    return {"token": token, "token_type": "bearer", "name": db_user.name, "role": db_user.role}

@router.post("/forgot-password")
async def forgot_password(request: Request, data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not registered")

    # Generate 6 digit OTP
    otp_code = "".join(random.choices(string.digits, k=6))

    # Save OTP to database
    db.query(OTP).filter(OTP.email == data.email).delete()
    new_otp = OTP(email=data.email, otp=otp_code)
    db.add(new_otp)
    db.commit()

    # Send email
    message = MessageSchema(
        subject="TrafficOpt — Password Reset OTP",
        recipients=[data.email],
        body=f"""
        <h2>Password Reset Request</h2>
        <p>Your OTP for resetting your TrafficOpt password is:</p>
        <h1 style="color: #10B981; letter-spacing: 8px;">{otp_code}</h1>
        <p>This OTP is valid for <strong>10 minutes</strong>.</p>
        <p>If you did not request this, ignore this email.</p>
        """,
        subtype=MessageType.html
    )

    mail = request.app.state.mail
    await mail.send_message(message)

    return {"message": "OTP sent to your email"}

@router.post("/verify-otp")
def verify_otp(data: VerifyOTPRequest, db: Session = Depends(get_db)):
    otp_record = db.query(OTP).filter(
        OTP.email == data.email,
        OTP.otp == data.otp,
        OTP.is_used == 0
    ).first()

    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Check OTP expiry (10 minutes)
    if datetime.utcnow() - otp_record.created_at > timedelta(minutes=10):
        raise HTTPException(status_code=400, detail="OTP expired")

    # Update password
    user = db.query(User).filter(User.email == data.email).first()
    user.hashed_password = hash_password(data.new_password)
    db.commit()

    # Mark OTP as used
    otp_record.is_used = 1
    db.commit()

    return {"message": "Password reset successful"}

@router.get("/profile")
def get_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_routes = db.query(Route).filter(Route.user_id == current_user.id).count()

    mode_counts = db.query(Route.mode, func.count(Route.mode)).filter(
        Route.user_id == current_user.id
    ).group_by(Route.mode).all()

    favourite_mode = max(mode_counts, key=lambda x: x[1])[0] if mode_counts else "None"

    recent = db.query(Route).filter(
        Route.user_id == current_user.id
    ).order_by(Route.created_at.desc()).limit(3).all()

    recent_routes = [
        {
            "mode": r.mode,
            "source": r.source,
            "destination": r.destination,
            "created_at": str(r.created_at)
        }
        for r in recent
    ]

    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "created_at": str(current_user.created_at),
        "total_routes": total_routes,
        "favourite_mode": favourite_mode,
        "recent_routes": recent_routes
    }
@router.put("/profile/name")
def update_name(
    data: UpdateNameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")

    current_user.name = data.name.strip()
    db.commit()
    db.refresh(current_user)

    return {"name": current_user.name}