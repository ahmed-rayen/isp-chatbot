from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
import time
import json
import uuid
from app.logger import logger
from app.models.schemas import ChatRequest, ChatResponse
from app.services.nvidia_client import get_ai_response_with_tools
from app.services.session import get_or_create_session, add_message, get_history, get_full_history
from app.database import get_db
from app.models.db_models import ChatSession, Message, Ticket, User, TechnicianVisit, SessionSummary, Outage
from app.limiter import limiter
from app.routers.auth import get_current_user

router = APIRouter()
BLOCKLIST = ["ignore previous instructions", "system prompt", "ignore all rules", "act as admin"]

def get_chat_rate_limit(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if not user:
        return "5/minute"  # Unauthenticated limit
    if user.plan == "Fiber 1Giga":
        return "30/minute"  # Premium limit
    if user.plan == "Fiber 500":
        return "20/minute"  # Standard limit
    return "10/minute"  # Fiber 100 limit

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat_endpoint(request: Request, payload: ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    start_time = time.time()
    try:
        user_input_lower = payload.message.lower()
        for bad_phrase in BLOCKLIST:
            if bad_phrase in user_input_lower:
                return ChatResponse(session_id=payload.session_id or "", reply="I'm sorry, I cannot process that request. How can I help you with your internet connection today?")

        session_id = get_or_create_session(db, payload.session_id, str(current_user.id))
        add_message(db, session_id, "user", payload.message)
        history = get_history(db, session_id)
        
        handoff_data = {
            "user_info": {"name": current_user.name, "account": current_user.account_number, "plan": current_user.plan, "address": current_user.address},
            "chat_history": history
        }
        transcript_str = json.dumps(handoff_data, indent=2)

        ai_reply = await get_ai_response_with_tools(db, session_id, history, transcript_str, str(current_user.id))
        add_message(db, session_id, "assistant", ai_reply)
        
        latency = (time.time() - start_time) * 1000
        logger.info("Chat request processed", extra={"session_id": session_id, "user_id": str(current_user.id), "latency_ms": round(latency)})
        
        session = db.query(ChatSession).filter(ChatSession.id == uuid.UUID(session_id)).first()
        if session and session.title == "New Conversation":
            session.title = payload.message[:30] + ("..." if len(payload.message) > 30 else "")
            db.commit()
        
        return ChatResponse(session_id=session_id, reply=ai_reply)
    except Exception as e:
        logger.error(f"Endpoint Error: {e}")
        # HIGH-002 FIX: Generic error message
        raise HTTPException(status_code=500, detail="An internal error occurred.")

@router.get("/sessions")
def get_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sessions = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).order_by(ChatSession.created_at.desc()).all()
    return [{"id": str(s.id), "title": s.title} for s in sessions]

@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # HIGH-009 FIX: Verify session belongs to current user
    session = db.query(ChatSession).filter(
        ChatSession.id == uuid.UUID(session_id),
        ChatSession.user_id == current_user.id  # Ownership check
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    msgs = db.query(Message).filter(Message.session_id == uuid.UUID(session_id)).order_by(Message.created_at).all()
    return [{"role": m.role, "content": m.content} for m in msgs]

@router.post("/sessions/{session_id}/summarize")
async def summarize_session(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        # HIGH-009 FIX: Verify session belongs to current user
        session = db.query(ChatSession).filter(
            ChatSession.id == uuid.UUID(session_id),
            ChatSession.user_id == current_user.id  # Ownership check
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        history = get_full_history(db, session_id)
        if len(history) < 2: return {"status": "skipped", "message": "Not enough messages to summarize."}
        from app.services.nvidia_client import generate_session_summary
        summary_text, status = await generate_session_summary(history)
        new_summary = SessionSummary(user_id=current_user.id, session_id=uuid.UUID(session_id), summary=summary_text, status=status)
        db.add(new_summary)
        db.commit()
        return {"status": "summarized", "summary": summary_text}
    except HTTPException:
        raise
    except Exception as e:
        # HIGH-002 FIX: Generic error, don't expose internal details
        logger.error(f"Summarize Error: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred.")
    
@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        uid = uuid.UUID(session_id)
        tickets = db.query(Ticket).filter(Ticket.session_id == uid).all()
        for ticket in tickets:
            db.query(TechnicianVisit).filter(TechnicianVisit.ticket_id == ticket.id).delete()
        db.query(Ticket).filter(Ticket.session_id == uid).delete()
        db.query(Message).filter(Message.session_id == uid).delete()
        db.query(SessionSummary).filter(SessionSummary.session_id == uid).delete()
        db.query(ChatSession).filter(ChatSession.id == uid, ChatSession.user_id == current_user.id).delete()
        db.commit()
        return {"status": "deleted"}
    except Exception as e:
        print(f"Delete Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/outages/active")
def get_active_outages(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    outages = db.query(Outage).filter(Outage.is_active == True, Outage.is_deleted == False).all()
    return [{"city": o.city, "status": o.status} for o in outages]