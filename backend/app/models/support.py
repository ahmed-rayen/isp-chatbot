from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Technician(Base):
    __tablename__ = "technicians"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50))
    daily_capacity = Column(Integer, default=3)

    # --- Relationships ---
    visits = relationship("TechnicianVisit", back_populates="technician")

    def __repr__(self):
        return f"<Technician id={self.id} name={self.name!r} capacity={self.daily_capacity}>"


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String(20), primary_key=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    issue_summary = Column(Text, nullable=False)
    transcript = Column(Text, default="")
    status = Column(String(20), default="open")
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # --- Relationships (cascade handles cleanup automatically) ---
    session = relationship("ChatSession", back_populates="tickets")
    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan", passive_deletes=True)
    visits = relationship("TechnicianVisit", back_populates="ticket", cascade="all, delete-orphan", passive_deletes=True)
    feedback = relationship("Feedback", back_populates="ticket", uselist=False, cascade="all, delete-orphan", passive_deletes=True)

    def __repr__(self):
        return f"<Ticket id={self.id} status={self.status!r} deleted={self.is_deleted}>"


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(String(20), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # --- Relationships ---
    ticket = relationship("Ticket", back_populates="comments")

    def __repr__(self):
        return f"<TicketComment id={self.id} ticket_id={self.ticket_id}>"


class TechnicianVisit(Base):
    __tablename__ = "technician_visits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(String(20), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    technician_id = Column(UUID(as_uuid=True), ForeignKey("technicians.id"), nullable=False)
    scheduled_date = Column(Date, nullable=False)
    time_slot = Column(String(20), nullable=False)
    status = Column(String(20), default="scheduled")
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # --- Relationships ---
    ticket = relationship("Ticket", back_populates="visits")
    technician = relationship("Technician", back_populates="visits")

    def __repr__(self):
        return f"<TechnicianVisit id={self.id} ticket_id={self.ticket_id} date={self.scheduled_date}>"


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    ticket_id = Column(String(20), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # --- Relationships ---
    ticket = relationship("Ticket", back_populates="feedback")
    flagged_chunks = relationship("FlaggedKBChunk", back_populates="feedback", cascade="all, delete-orphan", passive_deletes=True)

    def __repr__(self):
        return f"<Feedback id={self.id} ticket_id={self.ticket_id} rating={self.rating}>"


class FlaggedKBChunk(Base):
    __tablename__ = "flagged_kb_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feedback_id = Column(UUID(as_uuid=True), ForeignKey("feedback.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    topic = Column(String(200), nullable=False)
    reviewed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # --- Relationships ---
    feedback = relationship("Feedback", back_populates="flagged_chunks")

    def __repr__(self):
        return f"<FlaggedKBChunk id={self.id} topic={self.topic!r} reviewed={self.reviewed}>"