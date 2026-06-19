# backend/app/services/tools.py
import json
import os
import random
from sqlalchemy.orm import Session
from app.models.db_models import Ticket

# 1. Mock database of outages
MOCK_OUTAGES = {
    "tunis": "There is a confirmed fiber cut in Tunis. Estimated repair time: 2 hours.",
    "sfax": "There is a scheduled maintenance in Sfax. It will end at 14:00.",
    "sousse": "All systems are operational in Sousse."
}

def check_outage(city: str) -> str:
    """Checks the database for outages in the given city."""
    city = city.lower().strip()
    return MOCK_OUTAGES.get(city, f"No outage information available for {city}.")

# 2. Knowledge Base Setup
KB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "knowledge_base.json")

def search_knowledge_base(query: str) -> str:
    """Searches the knowledge base for information matching the query."""
    try:
        with open(KB_PATH, "r", encoding="utf-8") as f:
            knowledge = json.load(f)
        
        query_words = query.lower().split()
        results = []
        
        for item in knowledge:
            searchable_text = (item["topic"] + " " + " ".join(item["tags"]) + " " + item["content"]).lower()
            if any(word in searchable_text for word in query_words):
                results.append(item["content"])
        
        if results:
            return "\n\n".join(results)
        else:
            return "No information found in the knowledge base for this query."
            
    except Exception as e:
        return f"Error reading knowledge base: {str(e)}"

# 3. Database Ticket Creation
def create_ticket(db: Session, session_id: str, user_id: str, issue_summary: str) -> str:
    """Creates a support ticket in the database."""
    ticket_id = f"TKT-{random.randint(10000, 99999)}"
    
    new_ticket = Ticket(
        id=ticket_id,
        session_id=session_id,
        user_id=user_id,
        issue_summary=issue_summary,
        status="open"
    )
    db.add(new_ticket)
    db.commit()
    
    return f"Ticket {ticket_id} created successfully for user {user_id}."

# 4. Tool JSON Schemas (Tell the AI how to use these tools)
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "check_outage",
            "description": "Check if there is an internet outage in a specific Tunisian city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The name of the city in Tunisia, e.g., Tunis, Sfax, Sousse"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search the ISP knowledge base for technical guides, router setup, DNS configuration, and billing plans.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search term, e.g., 'dns', 'router reset', 'fiber plans'"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Create a support ticket if the issue cannot be resolved automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The ID of the user. If unknown, use 'guest'."
                    },
                    "issue_summary": {
                        "type": "string",
                        "description": "A brief summary of the technical issue."
                    }
                },
                "required": ["user_id", "issue_summary"]
            }
        }
    }
]

# 5. Tool Router
def execute_tool(db: Session, session_id: str, tool_name: str, arguments: dict) -> str:
    if tool_name == "check_outage":
        return check_outage(**arguments)
    elif tool_name == "create_ticket":
        return create_ticket(db=db, session_id=session_id, **arguments)
    elif tool_name == "search_knowledge_base":
        return search_knowledge_base(**arguments)
    else:
        return "Tool not found."