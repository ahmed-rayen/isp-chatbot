"""
Re-exports all models for backward compatibility.
All existing imports like `from app.models.db_models import User, Ticket` continue to work.
"""
from app.models.billing import Payment
from app.models.user import User, RefreshToken
from app.models.chat import ChatSession, Message, SessionSummary
from app.models.support import (
    Technician,
    TechnicianVisit,
    Ticket,
    TicketComment,
    Feedback,
    FlaggedKBChunk,
)
from app.models.system import Outage, Notification, KBHit, KBMiss

__all__ = [
    "User",
    "RefreshToken",
    "ChatSession",
    "Message",
    "SessionSummary",
    "Technician",
    "TechnicianVisit",
    "Ticket",
    "TicketComment",
    "Feedback",
    "FlaggedKBChunk",
    "Outage",
    "Notification",
    "KBHit",
    "KBMiss",
    "Payment",
]