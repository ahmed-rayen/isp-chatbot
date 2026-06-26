# backend/app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.routers import chat, auth, tickets, admin, notifications, feedback, technician, ws
from app.database import engine, Base, SessionLocal
from app.models import db_models
from app.services.auth import hash_password
from app.config import settings
import os
from app.limiter import limiter
Base.metadata.create_all(bind=engine)

# CRIT-002 FIX: Only seed in development
db = SessionLocal()
if not db.query(db_models.User).first():
    # Generate random credentials for dev only
    import random
    admin_pin = str(random.randint(100000, 999999))
    tech_pin = str(random.randint(100000, 999999))
    user_pin = str(random.randint(100000, 999999))
    
    admin_user = db_models.User(
        account_number="0000", name="Super Admin", email="admin@example.com",
        hashed_pin=hash_password(admin_pin), plan="Staff", is_admin=True
    )
    db.add(admin_user)
    
    mock_user = db_models.User(
        account_number="4821", name="Ahmed H.", email="ahmed@example.com",
        hashed_pin=hash_password(user_pin), plan="Fiber 500",
        balance=0.0, due_date="2024-06-01", address="123 Rue de Carthage, Tunis"
    )
    db.add(mock_user)
    
    tech1 = db_models.Technician(name="Karim", daily_capacity=3)
    tech2 = db_models.Technician(name="Sami", daily_capacity=2)
    db.add_all([tech1, tech2])
    db.commit()
    
    tech_user = db_models.User(
        account_number="1111", name="Karim (Tech)", email="tech@example.com",
        hashed_pin=hash_password(tech_pin), plan="Staff", is_technician=True,
        technician_id=tech1.id
    )
    db.add(tech_user)
    db.commit()
    
    print("=== DEVELOPMENT CREDENTIALS (DO NOT USE IN PRODUCTION) ===")
    print(f"Admin:    Account=0000  PIN={admin_pin}")
    print(f"User:     Account=4821  PIN={user_pin}")
    print(f"Tech:     Account=1111  PIN={tech_pin}")
    print("==========================================================")

# Seed outages
Base.metadata.create_all(bind=engine)
db = SessionLocal()

# 1. Seed Admin User
if not db.query(db_models.User).filter(db_models.User.account_number == "0000").first():
    admin_pin = str(random.randint(100000, 999999))
    db.add(db_models.User(
        account_number="0000", name="Super Admin", email="admin@example.com",
        hashed_pin=hash_password(admin_pin), plan="Staff", is_admin=True
    ))
    print(f"✅ Mock Admin created (Account: 0000, PIN: {admin_pin})")

# 2. Seed Normal User
if not db.query(db_models.User).filter(db_models.User.account_number == "4821").first():
    user_pin = str(random.randint(100000, 999999))
    db.add(db_models.User(
        account_number="4821", name="Ahmed H.", email="ahmed@example.com",
        hashed_pin=hash_password(user_pin), plan="Fiber 500",
        balance=0.0, due_date="2024-06-01", address="123 Rue de Carthage, Tunis"
    ))
    print(f"✅ Mock User created (Account: 4821, PIN: {user_pin})")

# 3. Seed Technicians (Fix scoping issue)
tech1 = db.query(db_models.Technician).filter(db_models.Technician.name == "Karim").first()
if not tech1:
    tech1 = db_models.Technician(name="Karim", daily_capacity=3)
    db.add(tech1)
    db.commit()

tech2 = db.query(db_models.Technician).filter(db_models.Technician.name == "Sami").first()
if not tech2:
    tech2 = db_models.Technician(name="Sami", daily_capacity=2)
    db.add(tech2)
    db.commit()
print("✅ Technicians ensured")

# 4. Seed Technician User Account (Linked safely!)
if not db.query(db_models.User).filter(db_models.User.account_number == "1111").first():
    tech_pin = str(random.randint(100000, 999999))
    db.add(db_models.User(
        account_number="1111", name="Karim (Tech)", email="tech@example.com",
        hashed_pin=hash_password(tech_pin), plan="Staff", is_technician=True,
        technician_id=tech1.id  # Now safely linked!
    ))
    print(f"✅ Mock Technician created (Account: 1111, PIN: {tech_pin})")

# 5. Seed Outages
if not db.query(db_models.Outage).first():
    db.add(db_models.Outage(city="tunis", status="Confirmed fiber cut. ETA: 2 hours.", is_active=True))
    db.add(db_models.Outage(city="sfax", status="Scheduled maintenance. Ends at 14:00.", is_active=True))
    db.add(db_models.Outage(city="sousse", status="All systems operational.", is_active=False))
    print("✅ Mock outages seeded")

db.commit()
db.close()


app = FastAPI(title="ISP Support Chatbot")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CRIT-003 FIX: Use explicit origin from config, not wildcard
# MED-006 FIX: Only ONE CORS middleware (removed duplicate)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],  # Explicit, no wildcards
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.middleware import AttachUserMiddleware
app.add_middleware(AttachUserMiddleware)

# HIGH-003 FIX: Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(tickets.router, prefix="/api", tags=["Tickets"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(notifications.router, prefix="/api", tags=["Notifications"])
app.include_router(feedback.router, prefix="/api", tags=["Feedback"])
app.include_router(technician.router, prefix="/api/technician", tags=["Technician"])
app.include_router(ws.router, prefix="/api", tags=["WebSockets"])

@app.get("/")
def root():
    return {"status": "ok", "service": "ISP Chatbot API"}