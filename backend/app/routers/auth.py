import random
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter  # Rate limiter instance
from app.models.auth_schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.models.db_models import User
from app.services.auth import verify_password, hash_password, create_access_token, decode_access_token

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
    # 1. Generate a unique 6-digit account number
    account_number = str(random.randint(100000, 999999))
    
    # 2. Create new user
    new_user = User(
        name=payload.name,
        account_number=account_number,
        hashed_pin=hash_password(payload.pin),
        plan="Fiber 100"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # 3. Auto-login after signup
    access_token = create_access_token(data={"sub": str(new_user.id)})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(new_user.id),
            "account_number": new_user.account_number,
            "name": new_user.name,
            "plan": new_user.plan,
            
        }
    }

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5 per minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.account_number == payload.account_number).first()
    if not user or not verify_password(payload.pin, user.hashed_pin):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid account number or PIN"
        )
    access_token = create_access_token(data={"sub": str(user.id)})
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

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user