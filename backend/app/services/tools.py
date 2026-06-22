import json
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
    """Checks PostgreSQL for active outages in the given city."""
    city_normalized = city.lower().strip()
    outage = db.query(Outage).filter(Outage.city == city_normalized).first()
    if not outage:
        return f"No outage information available for {city.title()}."
    if outage.is_active:
        return f"There is an active issue in {city.title()}: {outage.status}"
    return f"All systems are operational in {city.title()}."


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
    """Creates a standard support ticket in PostgreSQL."""
    ticket_id = f"TKT-{random.randint(10000, 99999)}"
    db.add(Ticket(
        id=ticket_id,
        session_id=session_id,
        user_id=user_id,
        issue_summary=issue_summary,
        transcript=transcript,
        status="open"
    ))
    db.commit()
    return f"Ticket {ticket_id} created successfully. A human agent will review the case."


# ---------------------------------------------------------------------------
# 5. Technician Scheduling
# ---------------------------------------------------------------------------

def schedule_technician_visit(
    db: Session,
    session_id: str,
    user_id: str,
    issue_type: str,
    preferred_date: str,
    time_slot: str
) -> str:
    """Creates a ticket and schedules a technician visit for physical issues."""

    # Parse preferred date
    try:
        if "tomorrow" in preferred_date.lower():
            visit_date = date.today() + timedelta(days=1)
        else:
            visit_date = date.fromisoformat(preferred_date)
    except Exception:
        visit_date = date.today() + timedelta(days=1)

    # Create ticket first
    ticket_id = f"TKT-{random.randint(10000, 99999)}"
    db.add(Ticket(
        id=ticket_id,
        session_id=session_id,
        user_id=user_id,
        issue_summary=f"Technician Visit Required: {issue_type}",
        transcript="",
        status="visit_scheduled"
    ))
    db.flush()

    # Find least-busy technician for that date
    visit_counts = dict(
        db.query(TechnicianVisit.technician_id, func.count(TechnicianVisit.id))
        .filter(TechnicianVisit.scheduled_date == visit_date)
        .group_by(TechnicianVisit.technician_id)
        .all()
    )
    all_techs = db.query(Technician).all()
    if not all_techs:
        db.rollback()
        return "Sorry, no technicians are currently available."

    chosen_tech = min(
        all_techs,
        key=lambda t: visit_counts.get(t.id, 0)
    )
    if visit_counts.get(chosen_tech.id, 0) >= chosen_tech.daily_capacity:
        db.rollback()
        return "Sorry, all technicians are fully booked for that date."

    db.add(TechnicianVisit(
        ticket_id=ticket_id,
        user_id=user_id,
        technician_id=chosen_tech.id,
        scheduled_date=visit_date,
        time_slot=time_slot,
        status="scheduled"
    ))
    db.commit()

    return (
        f"Success! Ticket {ticket_id} created. "
        f"Technician {chosen_tech.name} is scheduled for "
        f"{visit_date.strftime('%A, %B %d')} ({time_slot}). "
        f"Reference: {ticket_id}."
    )


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

def execute_tool(db: Session, session_id: str, user_id: str, tool_name: str, arguments: dict) -> str:
    if tool_name == "check_outage":
        return check_outage(db=db, **arguments)

    elif tool_name == "search_knowledge_base":
        return search_knowledge_base(**arguments)

    elif tool_name == "get_account_status":
        # user_id always comes from the verified JWT, never from AI arguments
        return get_account_status(db=db, user_id=user_id)

    elif tool_name == "get_ticket_status":
        return get_ticket_status(db=db, **arguments)

    elif tool_name == "run_remote_diagnostics":
        return run_remote_diagnostics(session_id=session_id)

    elif tool_name == "create_ticket":
        return create_ticket(
            db=db,
            session_id=session_id,
            user_id=user_id,
            issue_summary=arguments.get("issue_summary", ""),
            transcript=arguments.get("transcript", "")
        )

    elif tool_name == "schedule_technician_visit":
        return schedule_technician_visit(
            db=db,
            session_id=session_id,
            user_id=user_id,
            issue_type=arguments.get("issue_type", ""),
            preferred_date=arguments.get("preferred_date", "tomorrow"),
            time_slot=arguments.get("time_slot", "morning")
        )

    return "Tool not found."