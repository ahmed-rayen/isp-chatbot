import json
import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.logger import logger
from app.models.schemas import ChatRequest, ChatResponse
from app.models.db_models import ChatSession
from app.routers.auth import get_current_user
from app.models.db_models import User
from app.services.nvidia_client import get_ai_response_with_tools
from app.services.session import get_or_create_session, add_message, get_history

router = APIRouter()

BLOCKLIST = [
    "ignore previous instructions",
    "system prompt",
    "ignore all rules",
    "act as admin",
]



@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat_endpoint(
    request: Request,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start_time = time.time()

    if any(phrase in payload.message.lower() for phrase in BLOCKLIST):
        return ChatResponse(
            session_id=payload.session_id or "",
            reply="I'm sorry, I cannot process that request. How can I help you with your internet connection today?",
        )

    session_id = get_or_create_session(db, payload.session_id, str(current_user.id))
    add_message(db, session_id, "user", payload.message)
    history = get_history(db, session_id)

    handoff_data = {
        "user_info": {
            "name": current_user.name,
            "account": current_user.account_number,
            "plan": current_user.plan,
            "address": current_user.address,
        },
        "chat_history": history,
    }
    transcript_str = json.dumps(handoff_data, indent=2)

    ai_reply = await get_ai_response_with_tools(
        db, session_id, history, transcript_str, str(current_user.id)
    )
    add_message(db, session_id, "assistant", ai_reply)

    latency = (time.time() - start_time) * 1000
    logger.info(
        "Chat request processed",
        extra={"session_id": session_id, "user_id": str(current_user.id), "latency_ms": round(latency)},
    )

    # Auto-title new sessions
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session and session.title == "New Conversation":
        session.title = payload.message[:30] + ("..." if len(payload.message) > 30 else "")
        db.commit()

    return ChatResponse(session_id=session_id, reply=ai_reply)