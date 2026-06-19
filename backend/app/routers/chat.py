# backend/app/routers/chat.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.schemas import ChatRequest, ChatResponse
from app.services.nvidia_client import get_ai_response_with_tools
from app.services.session import get_or_create_session, add_message, get_history
from app.database import get_db

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        # 1. DB Session
        session_id = get_or_create_session(db, request.session_id)
        add_message(db, session_id, "user", request.message)
        history = get_history(db, session_id)
        
        # 2. AI Response (Pass db and session_id)
        ai_reply = get_ai_response_with_tools(db, session_id, history)
        
        # 3. Save AI reply
        add_message(db, session_id, "assistant", ai_reply)
        
        return ChatResponse(session_id=session_id, reply=ai_reply)
    except Exception as e:
        print(f"Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))