# backend/app/services/auth.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
from sqlalchemy.orm import Session
from app.models.db_models import RefreshToken
import secrets
import hashlib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# CRIT-001 FIX: Use secret from environment
SECRET_KEY = settings.jwt_secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def create_refresh_token(db: Session, user_id) -> str:
    raw_token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    db.add(RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() + timedelta(days=7)
    ))
    db.commit()
    return raw_token

# LOW-003 FIX: Token rotation on refresh
def rotate_refresh_token(db: Session, old_token_hash: str) -> str:
    record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == old_token_hash,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()
    if not record:
        return None
    
    # Revoke old token
    record.revoked = True
    
    # Issue new refresh token
    raw_token = secrets.token_urlsafe(64)
    new_token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    db.add(RefreshToken(
        user_id=record.user_id,
        token_hash=new_token_hash,
        expires_at=datetime.utcnow() + timedelta(days=7)
    ))
    db.commit()
    return raw_token