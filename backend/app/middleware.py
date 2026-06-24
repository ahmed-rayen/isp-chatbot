# backend/app/middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from app.database import SessionLocal
from app.models.db_models import User
from jose import jwt
import json

SECRET_KEY = "YOUR_SUPER_SECRET_KEY_CHANGE_THIS_LATER"
ALGORITHM = "HS256"

class AttachUserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request.state.user = None
        
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                user_id = payload.get("sub")
                if user_id:
                    db = SessionLocal()
                    user = db.query(User).filter(User.id == user_id).first()
                    request.state.user = user
                    db.close()
            except Exception:
                request.state.user = None
                
        response = await call_next(request)
        return response