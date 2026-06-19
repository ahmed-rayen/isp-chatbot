
import uuid
from typing import Dict, List

class SessionManager:
    def __init__(self):
        # In production, this would be Redis or a Database. 
        # For now, an in-memory dictionary works perfectly.
        self.sessions: Dict[str, List[dict]] = {}

    def get_or_create_session(self, session_id: str = None) -> str:
        """Returns an existing session ID, or creates a new one."""
        if not session_id or session_id not in self.sessions:
            session_id = str(uuid.uuid4())
            self.sessions[session_id] = []
        return session_id

    def add_message(self, session_id: str, role: str, content: str):
        """Appends a message to the session history."""
        if session_id in self.sessions:
            self.sessions[session_id].append({"role": role, "content": content})

    def get_history(self, session_id: str) -> List[dict]:
        """Retrieves the chat history for a given session."""
        return self.sessions.get(session_id, [])

# Create a single instance to be used across the app
session_manager = SessionManager()
