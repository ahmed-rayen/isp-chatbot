# backend/app/routers/chat.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.schemas import ChatRequest, ChatResponse
from app.services.nvidia_client import get_ai_response_with_tools
from app.services.session import get_or_create_session, add_message, get_history
from app.database import get_db
from app.models.db_models import ChatSession, Message
import uuid

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        session_id = get_or_create_session(db, request.session_id)
        add_message(db, session_id, "user", request.message)
        history = get_history(db, session_id)
        
        ai_reply = get_ai_response_with_tools(db, session_id, history)
        add_message(db, session_id, "assistant", ai_reply)
        
        # Update chat title if it's the first message
        session = db.query(ChatSession).filter(ChatSession.id == uuid.UUID(session_id)).first()
        if session and session.title == "New Conversation":
            session.title = request.message[:30] + ("..." if len(request.message) > 30 else "")
            db.commit()
        
        return ChatResponse(session_id=session_id, reply=ai_reply)
    except Exception as e:
        print(f"Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- NEW ENDPOINTS FOR SIDEBAR ---

@router.get("/sessions")
def get_sessions(db: Session = Depends(get_db)):
    sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()
    return [{"id": str(s.id), "title": s.title} for s in sessions]

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    # Delete messages first, then the session
    db.query(Message).filter(Message.session_id == uuid.UUID(session_id)).delete()
    db.query(ChatSession).filter(ChatSession.id == uuid.UUID(session_id)).delete()
    db.commit()
    return {"status": "deleted"}

@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    msgs = db.query(Message).filter(Message.session_id == uuid.UUID(session_id)).order_by(Message.created_at).all()
    return [{"role": m.role, "content": m.content} for m in msgs]