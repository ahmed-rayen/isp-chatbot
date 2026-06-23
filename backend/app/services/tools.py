import json
import uuid 
import os
import random
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from app.models.db_models import Ticket, User, Outage, Technician, TechnicianVisit
from openai import OpenAI
from app.config import settings

client = OpenAI(
    base_url=settings.nvidia_base_url,
    api_key=settings.nvidia_api_key
)

# ---------------------------------------------------------------------------
# 1. Outage Check (real DB)
# ---------------------------------------------------------------------------

def check_outage(db: Session, city: str) -> str:
    """Checks the PostgreSQL database for active outages in the given city."""
    from sqlalchemy import func # Import inside or at top
    city_formatted = city.lower().strip()
    outage = db.query(Outage).filter(func.lower(Outage.city) == city_formatted).first()
    
    if outage:
        if outage.is_deleted:
            return f"All systems are operational in {city.title()}."
        elif outage.is_active:
            return f"There is an active issue in {city.title()}: {outage.status}"
        else:
            return f"All systems are operational in {city.title()}."
    else:
        return f"No outage information available for {city.title()}."

# ---------------------------------------------------------------------------
# 2. Knowledge Base + Semantic Search
# ---------------------------------------------------------------------------

KB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "knowledge_base.json")

def load_knowledge_base():
    with open(KB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

KB_DATA = load_knowledge_base()

def get_embedding(text: str) -> list:
    response = client.embeddings.create(
        model="baai/bge-m3",
        input=text,
        encoding_format="float"
    )
    return response.data[0].embedding

print("Generating KB Embeddings...")
KB_EMBEDDINGS = []
try:
    for item in KB_DATA:
        text_to_embed = f"{item['topic']} {' '.join(item['tags'])} {item['content']}"
        KB_EMBEDDINGS.append(get_embedding(text_to_embed))
    print("KB Embeddings Ready.")
except Exception as e:
    print(f"Warning: Could not generate KB embeddings at startup. RAG disabled. Error: {e}")

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def search_knowledge_base(query: str) -> str:
    """Semantic search over the knowledge base using vector embeddings."""
    if not KB_EMBEDDINGS:
        return "The knowledge base is currently offline. Please try again later."
    try:
        query_vector = get_embedding(query)
        scores = sorted(
            [(i, cosine_similarity(query_vector, vec)) for i, vec in enumerate(KB_EMBEDDINGS)],
            key=lambda x: x[1],
            reverse=True
        )
        best_index, best_score = scores[0]
        if best_score > 0.5:
            return KB_DATA[best_index]["content"]
        return "No information found in the knowledge base for this query."
    except Exception as e:
        return f"Error during semantic search: {str(e)}"


# ---------------------------------------------------------------------------
# 3. Account & Ticket Tools (real DB)
# ---------------------------------------------------------------------------

def get_account_status(db: Session, user_id: str) -> str:
    """Looks up the authenticated user's account and billing plan from PostgreSQL."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return "User account not found."
    return (
        f"Account Found: {user.name}. "
        f"Current Plan: {user.plan}. "
        f"Balance Due: {user.balance} TND by {user.due_date}."
    )

def get_ticket_status(db: Session, ticket_id: str) -> str:
    """Checks the status of a support ticket from PostgreSQL."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id.upper()).first()
    if not ticket:
        return f"Ticket {ticket_id} not found."
    return (
        f"Ticket {ticket.id} status: {ticket.status}. "
        f"Issue: {ticket.issue_summary}. "
        f"Created at: {ticket.created_at}."
    )

def run_remote_diagnostics(session_id: str) -> str:
    """Simulates a fiber line signal check to the user's home."""
    signal_dbm = random.randint(-25, -15)
    if signal_dbm > -20:
        return f"Diagnostic complete. Fiber signal is excellent ({signal_dbm} dBm). The physical line is intact."
    return f"Diagnostic complete. Fiber signal is weak ({signal_dbm} dBm). Recommend dispatching a technician."


# ---------------------------------------------------------------------------
# 4. Ticket Creation
# ---------------------------------------------------------------------------

def create_ticket(db: Session, session_id: str, user_id: str, issue_summary: str, transcript: str = "") -> str:
    """Creates a support ticket in the database."""
    ticket_id = f"TKT-{random.randint(10000, 99999)}"
    new_ticket = Ticket(
        id=ticket_id,
        session_id=uuid.UUID(session_id),
        user_id=uuid.UUID(user_id),
        issue_summary=issue_summary,
        transcript=transcript, # ENSURE THIS IS HERE
        status="open"
    )
    db.add(new_ticket)
    db.commit()
    return f"Ticket {ticket_id} created successfully. A human agent will review the case."

def schedule_technician_visit(db: Session, session_id: str, user_id: str, issue_type: str, preferred_date: str, time_slot: str, transcript: str = "") -> str:
    """Schedules a technician visit for physical issues."""
    ticket_id = f"TKT-{random.randint(10000, 99999)}"
    new_ticket = Ticket(
        id=ticket_id,
        session_id=uuid.UUID(session_id),
        user_id=uuid.UUID(user_id),
        issue_summary=f"Technician Visit Required: {issue_type}",
        transcript=transcript, # ENSURE THIS IS HERE
        status="visit_scheduled"
    )
    db.add(new_ticket)
    db.flush()

    try:
        if "tomorrow" in preferred_date.lower() or "after tomorrow" in preferred_date.lower():
            days_add = 2 if "after" in preferred_date.lower() else 1
            visit_date = date.today() + timedelta(days=days_add)
        else:
            visit_date = date.fromisoformat(preferred_date)
    except:
        visit_date = date.today() + timedelta(days=1)

    tech_counts = db.query(TechnicianVisit.technician_id, func.count(TechnicianVisit.id))\
        .filter(TechnicianVisit.scheduled_date == visit_date)\
        .group_by(TechnicianVisit.technician_id).all()
    
    all_techs = db.query(Technician).all()
    chosen_tech = all_techs[0] if all_techs else None
    for tech, count in tech_counts:
        for t in all_techs:
            if t.id == tech and count < t.daily_capacity:
                chosen_tech = t
                break

    if not chosen_tech:
        db.rollback()
        return "Sorry, all technicians are fully booked for that date."

    new_visit = TechnicianVisit(
        ticket_id=ticket_id,
        user_id=uuid.UUID(user_id),
        technician_id=chosen_tech.id,
        scheduled_date=visit_date,
        time_slot=time_slot,
        status="scheduled"
    )
    db.add(new_visit)
    db.commit()

    return f"Success! Ticket {ticket_id} created. A technician named {chosen_tech.name} is scheduled for {visit_date.strftime('%A, %B %d')} during the {time_slot}. Reference ID: {ticket_id}."
    

# ---------------------------------------------------------------------------
# 6. Tool Schemas
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "check_outage",
            "description": "Check if there is an internet outage in a specific Tunisian city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name, e.g. Tunis, Sfax, Sousse"}
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
                    "query": {"type": "string", "description": "Search term, e.g. 'router reset', 'dns config'"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_account_status",
            "description": "Look up the authenticated user's account details, current plan, and billing balance.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_ticket_status",
            "description": "Check the current status of a support ticket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string", "description": "Ticket ID, e.g. TKT-12345"}
                },
                "required": ["ticket_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_remote_diagnostics",
            "description": "Run a remote signal test on the fiber line to the user's home.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Create a standard support ticket if the issue cannot be resolved automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_summary": {"type": "string", "description": "Brief summary of the issue."},
                    "transcript": {"type": "string", "description": "Full conversation history."}
                },
                "required": ["issue_summary"]
            }
        }
    },
        
            {
        "type": "function",
        "function": {
            "name": "schedule_technician_visit",
            "description": "Schedule a physical technician visit to the user's home. Use this instead of create_ticket if the issue is physical hardware failure, broken fiber cable, or if the user explicitly asks for a technician.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_type": {"type": "string", "description": "Brief description of the physical issue, e.g., 'Broken fiber cable', 'Router hardware failure'."},
                    "preferred_date": {"type": "string", "description": "The exact date the user requested, e.g., '2024-05-20' or 'tomorrow'."},
                    "time_slot": {"type": "string", "enum": ["morning", "afternoon", "evening"], "description": "The exact time slot the user requested."}
                },
                "required": ["issue_type"] # Only issue_type is required to start the process!
            }
        }
    }
]


# ---------------------------------------------------------------------------
# 7. Tool Router
# ---------------------------------------------------------------------------

def execute_tool(db: Session, session_id: str, user_id: str, tool_name: str, arguments: dict, transcript_str: str) -> str:
    if tool_name == "check_outage":
        return check_outage(db=db, **arguments)
    elif tool_name == "create_ticket":
        arguments["user_id"] = user_id
        # Pass transcript_str explicitly, and unpack the rest (issue_summary)
        return create_ticket(db=db, session_id=session_id, transcript=transcript_str, **arguments)
    elif tool_name == "schedule_technician_visit":
        arguments["user_id"] = user_id
        # Pass transcript_str explicitly, and unpack the rest (issue_type, preferred_date, time_slot)
        return schedule_technician_visit(db=db, session_id=session_id, transcript=transcript_str, **arguments)
    elif tool_name == "search_knowledge_base":
        return search_knowledge_base(**arguments)
    elif tool_name == "get_account_status":
        arguments["user_id"] = user_id
        return get_account_status(db=db, **arguments)
    elif tool_name == "get_ticket_status":
        return get_ticket_status(db=db, **arguments)
    elif tool_name == "run_remote_diagnostics":
        return run_remote_diagnostics(session_id=session_id)
    else:
        return "Tool not found."