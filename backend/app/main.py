# backend/app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.routers import chat, auth          # Added auth
from app.database import engine, Base, SessionLocal  # Added SessionLocal
from app.models import db_models
from app.services.auth import hash_password # Added hash_password

# Create tables
Base.metadata.create_all(bind=engine)

# Seed a mock user if none exists
db = SessionLocal()
if not db.query(db_models.User).first():
    mock_user = db_models.User(
        account_number="4821",
        name="Ahmed H.",
        hashed_pin=hash_password("1234"),
        plan="Fiber 500"
    )
    db.add(mock_user)
    db.commit()
    print("✅ Mock user created (Account: 4821, PIN: 1234)")
db.close()

# Initialize Limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["10 per minute"])

app = FastAPI(title="ISP Support Chatbot")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])

@app.get("/")
def root():
    return {"status": "ok", "service": "ISP Chatbot API"}