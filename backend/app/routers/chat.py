# backend/app/routers/chat.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.models.schemas import ChatRequest
from app.services.nvidia_client import stream_ai_response
from app.services.session import session_manager

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # 1. Get session and add user message
        session_id = session_manager.get_or_create_session(request.session_id)
        session_manager.add_message(session_id, "user", request.message)
        history = session_manager.get_history(session_id)
        
        def stream_and_save():
            full_reply = ""
            for chunk in stream_ai_response(history):
                full_reply += chunk
                yield chunk
            
            # Save the full reply to session memory after streaming finishes
            session_manager.add_message(session_id, "assistant", full_reply)
        
        # 2. Pass the session_id in the headers!
        return StreamingResponse(
            stream_and_save(), 
            media_type="text/plain",
            headers={"X-Session-ID": session_id}  # <-- HERE IS THE FIX
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))