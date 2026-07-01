from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.database import Base

def _utcnow():
    return datetime.now(timezone.utc)

class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    method = Column(String(50), default="Unknown")  # e.g., "Bank Transfer", "Flouci", "Post Office"
    status = Column(String(20), default="successful") # successful, failed, pending
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    def __repr__(self):
        return f"<Payment id={self.id} amount={self.amount} status={self.status}>"