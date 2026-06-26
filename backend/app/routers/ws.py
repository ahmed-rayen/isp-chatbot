# backend/app/routers/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.auth import decode_access_token
from app.ticket_ws_manager import ticket_manager

router = APIRouter()

@router.websocket("/ws/tickets/{ticket_id}")
async def ticket_websocket(websocket: WebSocket, ticket_id: str):
    # 1. Authenticate via query parameter
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return
        
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        await websocket.close(code=1008)
        return

    # 2. Accept and join the ticket room
    await ticket_manager.connect(websocket, ticket_id.upper())
    
    try:
        # Keep connection open. We don't receive messages here; 
        # frontend sends via REST to keep DB logic secure.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ticket_manager.disconnect(websocket, ticket_id.upper())