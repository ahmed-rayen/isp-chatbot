from sqlalchemy.orm import Session
from app.models.db_models import ChatSession, Message
import uuid

def get_or_create_session(db: Session, session_id: str = None) -> str:
    if session_id:
        existing = db.query(ChatSession).filter(ChatSession.id == uuid.UUID(session_id)).first()
        if existing:
            return session_id
            
    new_session = ChatSession()
    db.add(new_session)
    db.commit()
    return str(new_session.id)

def add_message(db: Session, session_id: str, role: str, content: str):
    msg = Message(session_id=uuid.UUID(session_id), role=role, content=content)
    db.add(msg)
    db.commit()

def get_history(db: Session, session_id: str) -> list:
    msgs = db.query(Message).filter(Message.session_id == uuid.UUID(session_id)).order_by(Message.created_at).all()
    # Sliding window: only keep the last 6 messages for the AI prompt
    recent_msgs = msgs[-6:]
    return [{"role": m.role, "content": m.content} for m in recent_msgs]

def get_full_history(db: Session, session_id: str) -> list:
    """Gets ALL messages in a session (not just the last 6) for the ticket transcript."""
    msgs = db.query(Message).filter(Message.session_id == uuid.UUID(session_id)).order_by(Message.created_at).all()
    return [{"role": m.role, "content": m.content} for m in msgs]