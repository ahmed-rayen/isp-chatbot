import json
import uuid 
import os
import random
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from rank_bm25 import BM25Okapi
from openai import OpenAI, AsyncOpenAI
from app.models.db_models import Ticket, User, Outage, Technician, TechnicianVisit
from app.config import settings
from app.services.notifications import send_notification

# ---------------------------------------------------------------------------
# 1. Client Instantiations
# ---------------------------------------------------------------------------
sync_client = OpenAI(
    base_url=settings.nvidia_base_url,
    api_key=settings.nvidia_api_key
)

async_client = AsyncOpenAI(
    base_url=settings.nvidia_base_url,
    api_key=settings.nvidia_api_key
)

# ---------------------------------------------------------------------------
# 2. Outage Check
# ---------------------------------------------------------------------------
def check_outage(db: Session, city: str) -> str:
    """Checks the PostgreSQL database for active outages in the given city."""
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
# 3. Knowledge Base + Hybrid Search Setup
# ---------------------------------------------------------------------------
KB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "knowledge_base.json")

def load_knowledge_base():
    with open(KB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

KB_DATA = load_knowledge_base()

def get_embedding_sync(text: str) -> list:
    """Retrieves text vectors synchronously using the sync client on initialization."""
    response = sync_client.embeddings.create(
        model="baai/bge-m3",
        input=text,
        encoding_format="float"
    )
    return response.data[0].embedding

print("🧠 Generating KB Chunk Embeddings & BM25 Index (Blocking Sync Pipeline)...")
KB_CHUNKS = []
KB_EMBEDDINGS = []
BM25_CORPUS = []

def build_kb_indices():
    global KB_CHUNKS, KB_EMBEDDINGS, BM25_CORPUS
    try:
        for item in KB_DATA:
            raw_chunks = item["content"].split("\n")
            for chunk in raw_chunks:
                chunk = chunk.strip()
                if len(chunk) > 15:
                    text_to_embed = f"{item['topic']} {' '.join(item['tags'])} {chunk}"
                    vector = get_embedding_sync(text_to_embed)
                    
                    KB_CHUNKS.append({"text": chunk, "topic": item["topic"]})
                    KB_EMBEDDINGS.append(vector)
                    BM25_CORPUS.append(text_to_embed.lower().split())
                    
        print(f"✅ {len(KB_CHUNKS)} KB Chunks Embedded & BM25 Indexed successfully!")
    except Exception as e:
        print(f"⚠️ Warning: Could not generate KB indices. RAG will be disabled. Error: {e}")

build_kb_indices()

bm25 = BM25Okapi(BM25_CORPUS) if BM25_CORPUS else None

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

async def search_knowledge_base(queries: list) -> str:
    """Hybrid search using Vector + BM25 for MULTIPLE expanded queries."""
    if not KB_CHUNKS or not bm25:
        return "The knowledge base is currently offline. Please try again later."
        
    try:
        k = 60
        rrf_scores = {}

        for query in queries:
            response = await async_client.embeddings.create(
                model="baai/bge-m3",
                input=query,
                encoding_format="float"
            )
            query_vector = response.data[0].embedding
            
            vector_scores = []
            for i, kb_vector in enumerate(KB_EMBEDDINGS):
                score = cosine_similarity(query_vector, kb_vector)
                vector_scores.append((i, score))
            vector_scores.sort(key=lambda x: x[1], reverse=True)
            top_vector_indices = [idx for idx, score in vector_scores[:5]]

            tokenized_query = query.lower().split()
            bm25_scores = bm25.get_scores(tokenized_query)
            top_bm25_indices = np.argsort(bm25_scores)[::-1][:5]

            for rank, idx in enumerate(top_vector_indices):
                rrf_scores[idx] = rrf_scores.get(idx, 0) + 1 / (k + rank + 1)
                
            for rank, idx in enumerate(top_bm25_indices):
                rrf_scores[idx] = rrf_scores.get(idx, 0) + 1 / (k + rank + 1)

        sorted_rrf = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        top_indices = [idx for idx, score in sorted_rrf[:3]]
        
        if not top_indices:
            return "No information found in the knowledge base for this query."
            
        result_chunks = [KB_CHUNKS[idx]["text"] for idx in top_indices]
        final_result = "\n".join(result_chunks)
        
        print(f"Hybrid Match Found! Returning {len(top_indices)} chunks based on {len(queries)} queries.")
        return final_result
            
    except Exception as e:
        return f"Error during hybrid search: {str(e)}"

# ---------------------------------------------------------------------------
# 4. Diagnostics & Account/Ticket Lookups
# ---------------------------------------------------------------------------
def get_account_status(db: Session, user_id: str) -> str:
    """Looks up the authenticated user's account and billing plan from PostgreSQL."""
    user = db.query(User).filter(User.id == uuid.UUID(user_id) if isinstance(user_id, str) else user_id).first()
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
# 5. Ticket Creation & Technician Scheduling (UUID Cast Safe)
# ---------------------------------------------------------------------------
def create_ticket(db: Session, session_id: str, user_id: str, issue_summary: str, transcript: str = "") -> str:
    """Creates a support ticket in the database with explicit UUID casting."""
    ticket_id = f"TKT-{random.randint(10000, 99999)}"
    
    # Casting string IDs explicitly to clean UUID instances
    clean_session_id = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
    clean_user_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

    new_ticket = Ticket(
        id=ticket_id,
        session_id=clean_session_id,
        user_id=clean_user_id,
        issue_summary=issue_summary,
        transcript=transcript,
        status="open"
    )
    db.add(new_ticket)
    db.commit()
    
    send_notification(db, user_id, f"Your support ticket {ticket_id} has been created. We will review it shortly.")
    return f"Ticket {ticket_id} created successfully. A human agent will review the case."

def schedule_technician_visit(db: Session, session_id: str, user_id: str, issue_type: str, preferred_date: str, time_slot: str, transcript: str = "") -> str:
    """Schedules a technician visit for physical issues with explicit UUID casting."""
    ticket_id = f"TKT-{random.randint(10000, 99999)}"
    
    # Casting string IDs explicitly to clean UUID instances
    clean_session_id = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
    clean_user_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

    new_ticket = Ticket(
        id=ticket_id,
        session_id=clean_session_id,
        user_id=clean_user_id,
        issue_summary=f"Technician Visit Required: {issue_type}",
        transcript=transcript,
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
        user_id=clean_user_id,
        technician_id=chosen_tech.id,
        scheduled_date=visit_date,
        time_slot=time_slot,
        status="scheduled"
    )
    db.add(new_visit)
    db.commit()
    
    send_notification(db, user_id, f"A technician ({chosen_tech.name}) has been scheduled for {visit_date.strftime('%A, %B %d')} ({time_slot}). Ticket ID: {ticket_id}.")
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
            "description": "Schedule a physical technician visit. YOU MUST CALL THIS TOOL to schedule a visit. NEVER tell the user a visit is scheduled without calling this tool. Use this if the issue is physical hardware failure, broken fiber cable, or if the user explicitly asks for a technician.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_type": {"type": "string", "description": "Brief description of the physical issue, e.g., 'Broken fiber cable', 'Router hardware failure'."},
                    "preferred_date": {"type": "string", "description": "The exact date the user requested, e.g., '2024-05-20' or 'tomorrow'."},
                    "time_slot": {"type": "string", "enum": ["morning", "afternoon", "evening"], "description": "The exact time slot the user requested."}
                },
                "required": ["issue_type", "preferred_date", "time_slot"] # <-- MAKE ALL REQUIRED
            }
        }
    }
]

# ---------------------------------------------------------------------------
# 7. Tool Router
# ---------------------------------------------------------------------------
async def execute_tool(db: Session, session_id: str, user_id: str, tool_name: str, arguments: dict, transcript_str: str) -> str:
    try:
        if tool_name == "check_outage":
            return check_outage(db=db, **arguments)
        elif tool_name == "create_ticket":
            arguments["user_id"] = user_id
            arguments["transcript"] = transcript_str  # <-- OVERWRITE IN DICT
            return create_ticket(db=db, session_id=session_id, **arguments)
        elif tool_name == "schedule_technician_visit":
            arguments["user_id"] = user_id
            arguments["transcript"] = transcript_str  # <-- OVERWRITE IN DICT
            return schedule_technician_visit(db=db, session_id=session_id, **arguments)
        elif tool_name == "search_knowledge_base":
            return await search_knowledge_base(**arguments)
        elif tool_name == "get_account_status":
            arguments["user_id"] = user_id
            return get_account_status(db=db, **arguments)
        elif tool_name == "get_ticket_status":
            return get_ticket_status(db=db, **arguments)
        elif tool_name == "run_remote_diagnostics":
            return run_remote_diagnostics(session_id=session_id)
        else:
            return "Tool not found."
    except Exception as e:
        print(f" EXECUTE_TOOL CRASHED: {e}")
        return "There was an error executing the tool."