
from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    # Optional because the first message won't have a session_id yet
    session_id: Optional[str] = None
    message: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str