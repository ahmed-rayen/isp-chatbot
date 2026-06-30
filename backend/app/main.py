import random

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.limiter import limiter
from app.middleware import AttachUserMiddleware
from app.models import db_models
from app.services.auth import hash_password
from app.services.rag import initialize_rag

# --- Routers ---
from app.routers import auth, chat, tickets, admin, notifications, feedback, technician, ws
from app.routers import sessions, outages  # extracted from chat.py

# ---------------------------------------------------------------------------
# Database tables
# ---------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Seed data (runs once at startup, inside lifespan — never at import time)
# ---------------------------------------------------------------------------
def seed_database() -> None:
    db = SessionLocal()
    try:
        # --- Admin ---
        if not db.query(db_models.User).filter(db_models.User.account_number == "0000").first():
            admin_pin = str(15000)
            db.add(db_models.User(
                account_number="0000", name="Super Admin", email="admin@example.com",
                hashed_pin=hash_password(admin_pin), plan="Staff", is_admin=True,
            ))
            print(f"✅ Mock Admin created (Account: 0000, PIN: {admin_pin})")

        # --- Normal User ---
        if not db.query(db_models.User).filter(db_models.User.account_number == "4821").first():
            user_pin = str(123456)
            db.add(db_models.User(
                account_number="4821", name="Ahmed H.", email="ahmed@example.com",
                hashed_pin=hash_password(user_pin), plan="Fiber 500",
                balance=0.0, due_date="2024-06-01", address="123 Rue de Carthage, Tunis",
            ))
            print(f"✅ Mock User created (Account: 4821, PIN: {user_pin})")

        # --- Technicians ---
        tech1 = db.query(db_models.Technician).filter(db_models.Technician.name == "Karim").first()
        if not tech1:
            tech1 = db_models.Technician(name="Karim", daily_capacity=3)
            db.add(tech1)

        tech2 = db.query(db_models.Technician).filter(db_models.Technician.name == "Sami").first()
        if not tech2:
            tech2 = db_models.Technician(name="Sami", daily_capacity=2)
            db.add(tech2)

        db.flush()  # ensure IDs are available for the user link below

        # --- Technician User Account ---
        if not db.query(db_models.User).filter(db_models.User.account_number == "1111").first():
            tech_pin = str(123456)
            db.add(db_models.User(
                account_number="1111", name="Karim (Tech)", email="tech@example.com",
                hashed_pin=hash_password(tech_pin), plan="Staff", is_technician=True,
                technician_id=tech1.id,
            ))
            print(f"✅ Mock Technician created (Account: 1111, PIN: {tech_pin})")

        # --- Outages ---
        if not db.query(db_models.Outage).first():
            db.add(db_models.Outage(city="tunis", status="Confirmed fiber cut. ETA: 2 hours.", is_active=True))
            db.add(db_models.Outage(city="sfax", status="Scheduled maintenance. Ends at 14:00.", is_active=True))
            db.add(db_models.Outage(city="sousse", status="All systems operational.", is_active=False))
            print("✅ Mock outages seeded")

        db.commit()
        print("==========================================================")
        print("  DEVELOPMENT CREDENTIALS — DO NOT USE IN PRODUCTION")
        print("==========================================================")
    except Exception as e:
        db.rollback()
        print(f"⚠️ Seeding failed: {e}")
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Security headers middleware (proper class, not inline function)
# ---------------------------------------------------------------------------
class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"strict-transport-security", b"max-age=31536000; includeSubDomains"))
                headers.append((b"x-content-type-options", b"nosniff"))
                headers.append((b"x-frame-options", b"DENY"))
                headers.append((b"referrer-policy", b"strict-origin-when-cross-origin"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
# ---------------------------------------------------------------------------
# App lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_database()
    await initialize_rag()
    yield

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(lifespan=lifespan, title="ISP Support Chatbot")

# Middleware (order matters: last added = first executed)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AttachUserMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(sessions.router, prefix="/api", tags=["Sessions"])
app.include_router(outages.router, prefix="/api", tags=["Outages"])
app.include_router(tickets.router, prefix="/api", tags=["Tickets"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(notifications.router, prefix="/api", tags=["Notifications"])
app.include_router(feedback.router, prefix="/api", tags=["Feedback"])
app.include_router(technician.router, prefix="/api/technician", tags=["Technician"])
app.include_router(ws.router, prefix="/api", tags=["WebSockets"])


@app.get("/")
def root():
    return {"status": "ok", "service": "ISP Chatbot API"}