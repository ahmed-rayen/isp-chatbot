# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import chat  # <-- ADD THIS IMPORT
from app.database import engine, Base     # <-- ADD THIS
from app.models import db_models          # <-- ADD THIS (loads the schemas)

Base.metadata.create_all(bind=engine)  
app = FastAPI(
    title="ISP Support Chatbot",
    description="AI-powered multilingual technical support for Tunisian ISP customers",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register the router
app.include_router(chat.router, prefix="/api", tags=["Chat"])  # <-- ADD THIS

@app.get("/")
def root():
    return {"status": "ok", "service": "ISP Chatbot API"}

@app.get("/health")
def health():
    return {"status": "healthy"}