from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_number = Column(String(20), unique=True, index=True)
    name = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    hashed_pin = Column(String(100))
    plan = Column(String(50), default="Fiber 100")
    balance = Column(Float, default=0.0)
    due_date = Column(Date, default=None)  # Was String, now proper Date
    address = Column(String(200), default="Unknown Address")
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_technician = Column(Boolean, default=False)
    technician_id = Column(UUID(as_uuid=True), ForeignKey("technicians.id"), nullable=True)

    # --- Relationships ---
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    technician = relationship("Technician", foreign_keys=[technician_id])

    def __repr__(self):
        return f"<User id={self.id} account={self.account_number} name={self.name}>"


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True)
    expires_at = Column(Date, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(Date, default=_utcnow)

    # --- Relationships ---
    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<RefreshToken id={self.id} user_id={self.user_id} revoked={self.revoked}>"