from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from app.models.schemas import ChatRequest, ChatResponse
from app.services.nvidia_client import get_ai_response_with_tools
from app.services.session import get_or_create_session, add_message, get_history, get_full_history
from app.database import get_db
from app.models.db_models import ChatSession, Message, Ticket, User, TechnicianVisit
from app.limiter import limiter
from app.routers.auth import get_current_user
from app.models.db_models import ChatSession, Message, Ticket, User, TechnicianVisit, SessionSummary
from app.services.nvidia_client import get_ai_response_with_tools, generate_session_summary
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
async def chat_endpoint(
    request: Request,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        user_input_lower = payload.message.lower()
        for bad_phrase in BLOCKLIST:
            if bad_phrase in user_input_lower:
                return ChatResponse(
                    session_id=payload.session_id or "",
                    reply="I cannot process that request. How can I help you with your internet connection today?"
                )

        session_id = get_or_create_session(db, payload.session_id, str(current_user.id))
        add_message(db, session_id, "user", payload.message)
        history = get_history(db, session_id)

        full_transcript = get_full_history(db, session_id)
        transcript_str = "\n".join([f"{m['role']}: {m['content']}" for m in full_transcript])

        ai_reply = get_ai_response_with_tools(db, session_id, history, transcript_str, str(current_user.id))

        add_message(db, session_id, "assistant", ai_reply)

        session = db.query(ChatSession).filter(ChatSession.id == uuid.UUID(session_id)).first()
        if session and session.title == "New Conversation":
            session.title = payload.message[:30] + ("..." if len(payload.message) > 30 else "")
            db.commit()

        return ChatResponse(session_id=session_id, reply=ai_reply)

    except Exception as e:
        print(f"Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{session_id}/summarize")
def summarize_session(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        # 1. Get full history
        history = get_full_history(db, session_id)
        if len(history) < 2:
            return {"status": "skipped", "message": "Not enough messages to summarize."}
            
        # 2. Call AI to generate summary
        summary_text, status = generate_session_summary(history)
        
        # 3. Save to DB
        new_summary = SessionSummary(
            user_id=current_user.id,
            session_id=uuid.UUID(session_id),
            summary=summary_text,
            status=status
        )
        db.add(new_summary)
        db.commit()
        
        return {"status": "summarized", "summary": summary_text}
    except Exception as e:
        print(f"Summarize Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions")
def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    return [{"id": str(s.id), "title": s.title} for s in sessions]


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        uid = uuid.UUID(session_id)
        
        # 1. Find all tickets for this session
        tickets = db.query(Ticket).filter(Ticket.session_id == uid).all()
        for ticket in tickets:
            # 2. Delete technician visits attached to these tickets
            db.query(TechnicianVisit).filter(TechnicianVisit.ticket_id == ticket.id).delete()
        
        # 3. Delete tickets, messages, and summaries
        db.query(Ticket).filter(Ticket.session_id == uid).delete()
        db.query(Message).filter(Message.session_id == uid).delete()
        db.query(SessionSummary).filter(SessionSummary.session_id == uid).delete() # <-- THE FIX
        
        # 4. Delete the session itself
        db.query(ChatSession).filter(ChatSession.id == uid, ChatSession.user_id == current_user.id).delete()
        
        db.commit()
        return {"status": "deleted"}
    except Exception as e:
        print(f"Delete Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}/messages")
def get_session_messages(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(ChatSession).filter(
        ChatSession.id == uuid.UUID(session_id),
        ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    msgs = (
        db.query(Message)
        .filter(Message.session_id == uuid.UUID(session_id))
        .order_by(Message.created_at)
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in msgs]