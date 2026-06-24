# backend/app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
import random
import hashlib
from app.database import get_db
from app.models.db_models import User, RefreshToken
from app.models.auth_schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services.auth import verify_password, hash_password, create_access_token, decode_access_token, create_refresh_token
from fastapi.security import OAuth2PasswordBearer
from app.limiter import limiter
from datetime import datetime

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise credentials_exception
    user_id = payload["sub"]
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/register", response_model=TokenResponse)
@limiter.limit("5 per minute")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    account_number = str(random.randint(100000, 999999))
    new_user = User(
        name=payload.name,
        email=payload.email,
        account_number=account_number,
        hashed_pin=hash_password(payload.pin),
        plan="Fiber 100"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": str(new_user.id)})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(new_user.id),
            "account_number": new_user.account_number,
            "name": new_user.name,
            "plan": new_user.plan,
            "is_admin": new_user.is_admin
        }
    }

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5 per minute")
def login(request: Request, response: Response, payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.account_number == payload.account_number).first()
    if not user or not verify_password(payload.pin, user.hashed_pin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid account number or PIN"
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(db, user.id)
    
    # Set httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False, # Set to True in production (HTTPS)
        samesite="lax",
        max_age=7 * 24 * 3600
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "account_number": user.account_number,
            "name": user.name,
            "plan": user.plan,
            "is_admin": user.is_admin
        }
    }

# NEW: Silent refresh endpoint
@router.post("/refresh")
def refresh(request: Request, db: Session = Depends(get_db)):
    raw_token = request.cookies.get("refresh_token")
    if not raw_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()
    
    if not record:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
        
    new_access_token = create_access_token(data={"sub": str(record.user_id)})
    return {"access_token": new_access_token}

# NEW: Logout endpoint to revoke token
@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_token = request.cookies.get("refresh_token")
    if raw_token:
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).update({"revoked": True})
        db.commit()
    response.delete_cookie("refresh_token")
    return {"status": "logged out"}

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user