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
from app.routers import chat, auth, tickets, admin, notifications, feedback, technician,ws
from app.limiter import limiter
from app.middleware import AttachUserMiddleware
# Create tables
Base.metadata.create_all(bind=engine)

# Seed a mock user if none exists
db = SessionLocal()
if not db.query(db_models.User).filter(db_models.User.account_number == "4821").first():
    mock_user = db_models.User(
        account_number="4821",
        name="Ahmed H.",
        email="ahmed@example.com",
        hashed_pin=hash_password("1234"),
        plan="Fiber 500",
        balance=0.0,
        due_date="2024-06-01",
        address="123 Rue de Carthage, Tunis"
    )
    db.add(mock_user)
    print(" Mock user created (Account: 4821, PIN: 1234)")
if not db.query(db_models.Outage).first():
    db.add(db_models.Outage(city="tunis", status="Confirmed fiber cut. ETA: 2 hours.", is_active=True))
    db.add(db_models.Outage(city="sfax", status="Scheduled maintenance. Ends at 14:00.", is_active=True))
    db.add(db_models.Outage(city="sousse", status="All systems operational.", is_active=False))
    print("✅ Mock outages seeded")
#techniciens
if not db.query(db_models.Technician).first():
    tech1 = db_models.Technician(name="Karim", daily_capacity=3)
    tech2 = db_models.Technician(name="Sami", daily_capacity=2)
    db.add_all([tech1, tech2])
    db.commit()
    print("✅ Mock technicians seeded")

if not db.query(db_models.User).filter(db_models.User.account_number == "1111").first():
    tech_user = db_models.User(
        account_number="1111",
        name="Karim (Tech)",
        email="tech@example.com",
        hashed_pin=hash_password("1234"),
        plan="Staff",
        is_technician=True,
        technician_id=tech1.id # Link to Karim
    )
    db.add(tech_user)
    print("✅ Mock technician user created (Account: 1111, PIN: 1234)")
db.commit()

if not db.query(db_models.User).filter(db_models.User.is_admin == True).first():
    admin_user = db_models.User(
        account_number="0000",
        name="Super Admin",
        email="admin@example.com",
        hashed_pin=hash_password("1234"),
        plan="Staff",
        is_admin=True
    )
    db.add(admin_user)
    print(" Mock Admin created (Account: 0000, PIN: 1234)")
db.commit()
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
app.add_middleware(AttachUserMiddleware)
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
app.include_router(tickets.router, prefix="/api", tags=["Tickets"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(notifications.router, prefix="/api", tags=["Notifications"])
app.include_router(feedback.router, prefix="/api", tags=["Feedback"])
app.include_router(technician.router, prefix="/api/technician", tags=["Technician"])
app.include_router(ws.router, prefix="/api", tags=["WebSockets"])
@app.get("/")
def root():
    return {"status": "ok", "service": "ISP Chatbot API"}