# backend/app/services/tools.py
import json
import os
import random
from sqlalchemy.orm import Session
from app.models.db_models import Ticket
import numpy as np
from openai import OpenAI
from app.config import settings
client = OpenAI(
    base_url=settings.nvidia_base_url,
    api_key=settings.nvidia_api_key
)
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

def load_knowledge_base():
    with open(KB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

KB_DATA = load_knowledge_base()

# 2. Generate Embeddings for the KB on startup
def get_embedding(text: str) -> list:
    response = client.embeddings.create(
        model="baai/bge-m3", # NVIDIA's free multilingual embedding model
        input=text,
        encoding_format="float"
    )
    return response.data[0].embedding

# Pre-compute vectors for all KB items (so we don't call the API every time)
print(" Generating KB Embeddings...")
KB_EMBEDDINGS = []
for item in KB_DATA:
    # We embed the topic, tags, and content together for best semantic matching
    text_to_embed = f"{item['topic']} {' '.join(item['tags'])} {item['content']}"
    vector = get_embedding(text_to_embed)
    KB_EMBEDDINGS.append(vector)
print("KB Embeddings Ready!")

def cosine_similarity(vec1, vec2):
    """Calculates how similar two vectors are (1.0 = identical, 0.0 = unrelated)"""
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def search_knowledge_base(query: str) -> str:
    """Semantic search using Vector Embeddings."""
    try:
        # 1. Get the vector for the user's query
        query_vector = get_embedding(query)
        
        # 2. Compare query vector against all KB vectors
        scores = []
        for i, kb_vector in enumerate(KB_EMBEDDINGS):
            score = cosine_similarity(query_vector, kb_vector)
            scores.append((i, score))
            
        # 3. Sort by highest score
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # 4. Get the best match (if score is above 0.5, otherwise it's unrelated)
        best_match_index, best_score = scores[0]
        
        if best_score > 0.5: # Threshold for relevance
            print(f"Semantic Match Found! (Score: {best_score:.2f})")
            return KB_DATA[best_match_index]["content"]
        else:
            return "No information found in the knowledge base for this query."
            
    except Exception as e:
        return f"Error during semantic search: {str(e)}"

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
    
def get_account_status(user_id: str) -> str:
    """Mocks a lookup of the user's specific account and billing plan."""
    # In reality, this hits your ISP billing database
    if user_id == "guest" or not user_id:
        return "User not authenticated. Please ask the user for their Client ID."
    
    # Mock data for a specific user
    mock_accounts = {
        "4821": {"name": "Ahmed H.", "plan": "Fiber 500", "speed": "500 Mbps", "balance": "0 TND", "due_date": "2024-06-01"},
        "1234": {"name": "Sara B.", "plan": "Fiber 100", "speed": "100 Mbps", "balance": "99 TND", "due_date": "2024-05-15"}
    }
    
    account = mock_accounts.get(str(user_id))
    if account:
        return f"Account Found: {account['name']}. Current Plan: {account['plan']} ({account['speed']}). Balance Due: {account['balance']} by {account['due_date']}."
    return f"No account found for ID {user_id}."

def run_remote_diagnostics(session_id: str) -> str:
    """Simulates checking the fiber line signal to the user's home."""
    # In reality, this hits your network management system (NMS)
    import random
    signal_dbm = random.randint(-25, -15) # -15 to -25 is good signal
    if signal_dbm > -20:
        return f"Diagnostic complete. Fiber signal is excellent ({signal_dbm} dBm). The physical line to the home is intact. The issue is likely with the user's router or Wi-Fi."
    else:
        return f"Diagnostic complete. Fiber signal is weak ({signal_dbm} dBm). There may be a physical issue with the fiber cable outside the home. Recommend dispatching a technician."

# Update the create_ticket function to accept and save the transcript
def create_ticket(db: Session, session_id: str, user_id: str, issue_summary: str, transcript: str = "") -> str:
    """Creates a support ticket in the database with the full chat transcript."""
    ticket_id = f"TKT-{random.randint(10000, 99999)}"
    
    new_ticket = Ticket(
        id=ticket_id,
        session_id=session_id,
        user_id=user_id,
        issue_summary=issue_summary,
        transcript=transcript, # Save the transcript!
        status="open"
    )
    db.add(new_ticket)
    db.commit()
    
    return f"Ticket {ticket_id} created successfully. A human agent will review the case and call the user back."

# Update TOOL_DEFINITIONS to include the new tools...
TOOL_DEFINITIONS = [
    # ... (keep check_outage and search_knowledge_base) ...
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Create a support ticket if the issue cannot be resolved automatically. Use this if the user explicitly asks to escalate, speak to a human, or if a physical issue is detected.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "The ID of the user. If unknown, use 'guest'."},
                    "issue_summary": {"type": "string", "description": "A brief summary of the technical issue."},
                    "transcript": {"type": "string", "description": "The full conversation history to attach to the ticket."}
                },
                "required": ["user_id", "issue_summary"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_account_status",
            "description": "Look up a user's specific account details, current internet plan, and billing balance. Use this instead of the knowledge base if a user asks 'What plan do I have?' or 'What is my balance?'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "The client ID of the user."}
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_remote_diagnostics",
            "description": "Run a remote signal test on the fiber line connecting to the user's home. Use this if the user has no internet at all, or if you suspect a physical cable issue.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# Update execute_tool to route the new tools...
def execute_tool(db: Session, session_id: str, tool_name: str, arguments: dict) -> str:
    if tool_name == "check_outage":
        return check_outage(**arguments)
    elif tool_name == "create_ticket":
        # We need to fetch the transcript from the DB and pass it here.
        # For now, we pass an empty string, we'll update the router to fetch it.
        return create_ticket(db=db, session_id=session_id, transcript=arguments.get("transcript", ""), **{k:v for k,v in arguments.items() if k != "transcript"})
    elif tool_name == "search_knowledge_base":
        return search_knowledge_base(**arguments)
    elif tool_name == "get_account_status":
        return get_account_status(**arguments)
    elif tool_name == "run_remote_diagnostics":
        return run_remote_diagnostics(session_id=session_id)
    else:
        return "Tool not found."