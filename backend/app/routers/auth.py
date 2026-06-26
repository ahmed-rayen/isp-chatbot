# backend/app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
import random
import hashlib
import os
from app.database import get_db
from app.models.db_models import User, RefreshToken
from app.models.auth_schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services.auth import (
    verify_password, hash_password, create_access_token, 
    decode_access_token, create_refresh_token, rotate_refresh_token
)
from fastapi.security import OAuth2PasswordBearer
from app.limiter import limiter
from datetime import datetime
from app.config import settings
from app.logger import logger

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
def is_https():
    return os.getenv("FRONTEND_ORIGIN", "http://localhost:3000").startswith("https")

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
    refresh_token = create_refresh_token(db, new_user.id)
    
    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(new_user.id),
            "account_number": new_user.account_number,
            "name": new_user.name,
            "plan": new_user.plan,
            "is_admin": new_user.is_admin,
            "is_technician": new_user.is_technician
        }
    }
    return response_data

@router.post("/login", response_model=TokenResponse)
@limiter.limit("3 per minute")  # LOW-004 FIX: Stricter login limit
def login(request: Request, response: Response, payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.account_number == payload.account_number).first()
    if not user or not verify_password(payload.pin, user.hashed_pin):
        # MED-003 FIX: Log security events
        logger.warning(f"Failed login attempt for account: {payload.account_number}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid account number or PIN"
        )
    
    logger.info(f"Successful login for account: {payload.account_number}")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(db, user.id)
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_https(),  # FIX: False on localhost, True in production
        samesite="strict",
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
            "is_admin": user.is_admin,
            "is_technician": user.is_technician
        }
    }

# CRIT-007 FIX: Add rate limiting to refresh endpoint
@router.post("/refresh")
@limiter.limit("10 per minute")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_token = request.cookies.get("refresh_token")
    if not raw_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    
    # LOW-003 FIX: Token rotation
    new_refresh_token = rotate_refresh_token(db, token_hash)
    if not new_refresh_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    # Get user_id from the new token record
    record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == hashlib.sha256(new_refresh_token.encode()).hexdigest()
    ).first()
    
    new_access_token = create_access_token(data={"sub": str(record.user_id)})
    
    # Set new rotated refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=is_https(),  # FIX: False on localhost, True in production
        samesite="strict",
        max_age=7 * 24 * 3600
    )
       
    return {"access_token": new_access_token}

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