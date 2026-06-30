from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Outage(Base):
    __tablename__ = "outages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    city = Column(String(50), unique=True, index=True)
    status = Column(String(200))
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Outage city={self.city!r} active={self.is_active}>"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self):
        return f"<Notification id={self.id} user_id={self.user_id} read={self.is_read}>"


class KBHit(Base):
    __tablename__ = "kb_hits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    topic = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # --- Relationships ---
    session = relationship("ChatSession", back_populates="kb_hits")

    def __repr__(self):
        return f"<KBHit id={self.id} topic={self.topic!r}>"


class KBMiss(Base):
    __tablename__ = "kb_misses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    query = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self):
        return f"<KBMiss id={self.id} query={self.query!r:.50}>"