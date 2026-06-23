# backend/app/models/db_models.py
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean, Float, Integer, Date
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, date
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_number = Column(String(20), unique=True, index=True)
    name = Column(String(100))
    email = Column(String(100), unique=True, index=True) # NEW
    hashed_pin = Column(String(100))
    plan = Column(String(50), default="Fiber 100")
    balance = Column(Float, default=0.0)
    due_date = Column(String(20), default="N/A")
    address = Column(String(200), default="Unknown Address")
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

class Notification(Base):
    __tablename__ = "notifications" # NEW TABLE
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Outage(Base):
    __tablename__ = "outages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    city = Column(String(50), unique=True, index=True)
    status = Column(String(200))
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)

class Technician(Base):
    __tablename__ = "technicians"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50))
    daily_capacity = Column(Integer, default=3) # Max visits per day

class TechnicianVisit(Base):
    __tablename__ = "technician_visits"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(String(20), ForeignKey("tickets.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    technician_id = Column(UUID(as_uuid=True), ForeignKey("technicians.id"), nullable=False)
    scheduled_date = Column(Date, nullable=False)
    time_slot = Column(String(20), nullable=False) # morning, afternoon, evening
    status = Column(String(20), default="scheduled")
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(100), default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(String(20), primary_key=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    issue_summary = Column(Text, nullable=False)
    transcript = Column(Text, default="")
    status = Column(String(20), default="open")
    created_at = Column(DateTime, default=datetime.utcnow)
    
class SessionSummary(Base):
    __tablename__ = "session_summaries"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    summary = Column(Text, nullable=False)
    status = Column(String(20), default="resolved") # resolved/unresolved
    created_at = Column(DateTime, default=datetime.utcnow)
    
