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
from app.routers import chat, auth, tickets, admin 

# Create tables
Base.metadata.create_all(bind=engine)

# Seed a mock user if none exists
db = SessionLocal()
if not db.query(db_models.User).filter(db_models.User.account_number == "4821").first():
    mock_user = db_models.User(
        account_number="4821",
        name="Ahmed H.",
        hashed_pin=hash_password("1234"),
        plan="Fiber 500",
        balance=0.0,
        due_date="2024-06-01",
        address="123 Rue de Carthage, Tunis"
    )
    db.add(mock_user)
    print(" Mock user created (Account: 4821, PIN: 1234)")
if not db.query(db_models.Outage).first():
    db.add(db_models.Outage(city="Tunis", status="Confirmed fiber cut. ETA: 2 hours.", is_active=True))
    db.add(db_models.Outage(city="Sfax", status="Scheduled maintenance. Ends at 14:00.", is_active=True))
    db.add(db_models.Outage(city="Sousse", status="All systems operational.", is_active=False))
    print(" Mock outages seeded")
db.commit()
db.close()
#techniciens
if not db.query(db_models.Technician).first():
    db.add(db_models.Technician(name="Karim", daily_capacity=3))
    db.add(db_models.Technician(name="Sami", daily_capacity=2))
    print("✅ Mock technicians seeded")
db.commit()
db.close()
if not db.query(db_models.User).filter(db_models.User.is_admin == True).first():
    admin_user = db_models.User(
        account_number="0000",
        name="Super Admin",
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

# Register routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(tickets.router, prefix="/api", tags=["Tickets"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
@app.get("/")
def root():
    return {"status": "ok", "service": "ISP Chatbot API"}