# backend/app/routers/chat.py
from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.services.nvidia_client import get_ai_response_with_tools
from app.services.session import session_manager

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # 1. Get session and add user message
        session_id = session_manager.get_or_create_session(request.session_id)
        session_manager.add_message(session_id, "user", request.message)
        history = session_manager.get_history(session_id)
        
        # 2. Get AI response (this now checks for tools automatically!)
        ai_reply = get_ai_response_with_tools(history)
        
        # 3. Save the AI's response to memory
        session_manager.add_message(session_id, "assistant", ai_reply)
        
        return ChatResponse(session_id=session_id, reply=ai_reply)
        
    except Exception as e:
        print(f"Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))