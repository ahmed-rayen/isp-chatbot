from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(100), default="New Conversation")
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # --- Relationships (cascade handles delete_session automatically) ---
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan", passive_deletes=True)
    summaries = relationship("SessionSummary", back_populates="session", cascade="all, delete-orphan", passive_deletes=True)
    tickets = relationship("Ticket", back_populates="session", cascade="all, delete-orphan", passive_deletes=True)
    kb_hits = relationship("KBHit", back_populates="session", cascade="all, delete-orphan", passive_deletes=True)

    def __repr__(self):
        return f"<ChatSession id={self.id} title={self.title!r}>"


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # --- Relationships ---
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<Message id={self.id} session_id={self.session_id} role={self.role!r}>"


class SessionSummary(Base):
    __tablename__ = "session_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    summary = Column(Text, nullable=False)
    status = Column(String(20), default="resolved")
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # --- Relationships ---
    session = relationship("ChatSession", back_populates="summaries")

    def __repr__(self):
        return f"<SessionSummary id={self.id} session_id={self.session_id} status={self.status!r}>"