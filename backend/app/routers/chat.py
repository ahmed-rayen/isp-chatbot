# backend/app/routers/chat.py
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from app.models.schemas import ChatRequest, ChatResponse
from app.services.nvidia_client import get_ai_response_with_tools
from app.services.session import get_or_create_session, add_message, get_history, get_full_history
from app.database import get_db
from app.models.db_models import ChatSession, Message, Ticket
from app.limiter import limiter
import uuid

router = APIRouter()

BLOCKLIST = [
    "ignore previous instructions",
    "system prompt",
    "ignore all rules",
    "act as admin",
    "jailbreak",
    "disregard your instructions",
    "pretend you are",
    "you are now",
]

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat_endpoint(request: Request, payload: ChatRequest, db: Session = Depends(get_db)):
    try:
        user_input_lower = payload.message.lower()
        for bad_phrase in BLOCKLIST:
            if bad_phrase in user_input_lower:
                return ChatResponse(
                    session_id=payload.session_id or "",
                    reply="I cannot process that request. How can I help you with your internet connection today?"
                )

        session_id = get_or_create_session(db, payload.session_id)
        add_message(db, session_id, "user", payload.message)
        history = get_history(db, session_id)

        full_transcript = get_full_history(db, session_id)
        transcript_str = "\n".join([f"{m['role']}: {m['content']}" for m in full_transcript])

        ai_reply = get_ai_response_with_tools(db, session_id, history, transcript_str)

        add_message(db, session_id, "assistant", ai_reply)

        session = db.query(ChatSession).filter(ChatSession.id == uuid.UUID(session_id)).first()
        if session and session.title == "New Conversation":
            session.title = payload.message[:30] + ("..." if len(payload.message) > 30 else "")
            db.commit()

        return ChatResponse(session_id=session_id, reply=ai_reply)

    except Exception as e:
        print(f"Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
def get_sessions(db: Session = Depends(get_db)):
    sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()
    return [{"id": str(s.id), "title": s.title} for s in sessions]


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    try:
        uid = uuid.UUID(session_id)
        db.query(Ticket).filter(Ticket.session_id == uid).delete()
        db.query(Message).filter(Message.session_id == uid).delete()
        db.query(ChatSession).filter(ChatSession.id == uid).delete()
        db.commit()
        return {"status": "deleted"}
    except Exception as e:
        print(f"Delete Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    msgs = db.query(Message).filter(
        Message.session_id == uuid.UUID(session_id)
    ).order_by(Message.created_at).all()
    return [{"role": m.role, "content": m.content} for m in msgs]