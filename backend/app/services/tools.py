import json
import os
import random
import uuid
import httpx
import numpy as np
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from openai import OpenAI, AsyncOpenAI
from app.config import settings
from app.models.db_models import Ticket, User, Outage, Technician, TechnicianVisit, KBMiss

client = OpenAI(base_url=settings.nvidia_base_url, api_key=settings.nvidia_api_key)
async_client = AsyncOpenAI(base_url=settings.nvidia_base_url, api_key=settings.nvidia_api_key)

MOCK_OUTAGES = {
    "tunis": "There is a confirmed fiber cut in Tunis. Estimated repair time: 2 hours.",
    "sfax": "There is a scheduled maintenance in Sfax. It will end at 14:00.",
    "sousse": "All systems are operational in Sousse."
}

def check_outage(db: Session, city: str) -> str:
    city_formatted = city.lower().strip()
    outage = db.query(Outage).filter(func.lower(Outage.city) == city_formatted, Outage.is_deleted == False).first()
    if outage:
        if outage.is_active:
            return f"There is an active issue in {city.title()}: {outage.status}"
        else:
            return f"All systems are operational in {city.title()}."
    else:
        return f"No outage information available for {city.title()}."

KB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "knowledge_base.json")
def load_knowledge_base():
    with open(KB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

KB_DATA = load_knowledge_base()
KB_CHUNKS = []
KB_EMBEDDINGS = []
KB_CATEGORIES = []
BM25_CORPUS = []

def get_embedding_sync(text: str) -> list:
    response = client.embeddings.create(model="baai/bge-m3", input=text, encoding_format="float")
    return response.data[0].embedding

print("🧠 Generating KB Chunk Embeddings & BM25 Index...")
def build_kb_indices():
    global KB_CHUNKS, KB_EMBEDDINGS, BM25_CORPUS, KB_CATEGORIES
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
                    KB_CATEGORIES.append(item.get("category", "general"))
        print(f" {len(KB_CHUNKS)} KB Chunks Embedded & BM25 Indexed!")
    except Exception as e:
        print(f" Warning: Could not generate KB indices. RAG will be disabled. Error: {e}")

build_kb_indices()
bm25 = BM25Okapi(BM25_CORPUS) if BM25_CORPUS else None

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def classify_query(query: str) -> str:
    billing_keywords = ["price", "plan", "bill", "invoice", "pay", "tnd", "mbps"]
    if any(word in query.lower() for word in billing_keywords):
        return "billing"
    return "technical"

async def rerank_chunks(query: str, chunks: list) -> tuple:
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                "https://integrate.api.nvidia.com/v1/ranking",
                headers={"Authorization": f"Bearer {settings.nvidia_api_key}", "Content-Type": "application/json"},
                json={"model": "baai/bge-reranker-v2-m3", "query": query, "passages": [{"text": c} for c in chunks]},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            ranked_indices = sorted(data['rankings'], key=lambda x: x['logit'], reverse=True)
            top_chunks = [chunks[i['index']] for i in ranked_indices[:3]]
            top_logit = ranked_indices[0]['logit'] if ranked_indices else -10.0
            return top_chunks, top_logit
    except Exception as e:
        print(f"Reranker failed, falling back: {e}")
        return chunks[:3], 0.0 

async def search_knowledge_base(query: str, db: Session, user_id: str = None, session_id: str = None) -> str:
    try:
        k = 60
        rrf_scores = {}
        target_category = classify_query(query)

        # 1. VECTOR SEARCH
        response = await async_client.embeddings.create(model="baai/bge-m3", input=query, encoding_format="float")
        query_vector = response.data[0].embedding
        vector_scores = []
        for i, kb_vector in enumerate(KB_EMBEDDINGS):
            score = cosine_similarity(query_vector, kb_vector)
            if KB_CATEGORIES[i] == target_category:
                score *= 1.2  # Soft boost
            vector_scores.append((i, score))
        vector_scores.sort(key=lambda x: x[1], reverse=True)
        top_vector_indices = [idx for idx, score in vector_scores[:5]]

        # 2. BM25 KEYWORD SEARCH
        tokenized_query = query.lower().split()
        bm25_scores = bm25.get_scores(tokenized_query)
        top_bm25_indices = np.argsort(bm25_scores)[::-1][:5]

        # 3. RECIPROCAL RANK FUSION (RRF)
        for rank, idx in enumerate(top_vector_indices):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1 / (k + rank + 1)
        for rank, idx in enumerate(top_bm25_indices):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1 / (k + rank + 1)

        sorted_rrf = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        # KB Miss Detection Point 1 (RRF Score Threshold Check)
        best_rrf_score = sorted_rrf[0][1] if sorted_rrf else 0
        if best_rrf_score < 0.005:  # Tunable RRF threshold
            db_user_id = uuid.UUID(user_id) if user_id else None
            db.add(KBMiss(user_id=db_user_id, query=query))
            db.commit()
            return "No information found in the knowledge base for this query."
            
        top_candidate_indices = [idx for idx, score in sorted_rrf[:5]]
        candidate_chunks = [KB_CHUNKS[idx]["text"] for idx in top_candidate_indices]
        
        # 4. CROSS-ENCODER RE-RANKING
        final_chunks, top_logit = await rerank_chunks(query, candidate_chunks)
        
        # KB Miss Detection Point 2 (Re-ranker Logit Threshold Check)
        if top_logit < -2.0 and top_logit != 0.0:  # Tunable Logit threshold
            db_user_id = uuid.UUID(user_id) if user_id else None
            db.add(KBMiss(user_id=db_user_id, query=query))
            db.commit()
            return "No information found in the knowledge base for this query."

        # LOG KB HITS FOR FEEDBACK LOOP
        if session_id and final_chunks:
            for chunk in final_chunks:
                # Find the topic for this chunk inside the original candidate lookup indices
                topic = next(
                    (KB_CHUNKS[idx]["topic"] for idx in top_candidate_indices if KB_CHUNKS[idx]["text"] == chunk), 
                    "unknown"
                )
                db.add(KBHit(session_id=uuid.UUID(session_id), chunk_text=chunk, topic=topic))
            db.commit()
            
        return "\n".join(final_chunks)
            
    except Exception as e:
        return f"Error during hybrid search: {str(e)}"

def get_account_status(db: Session, user_id: str) -> str:
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user: return "User account not found."
    return f"Account Found: {user.name}. Current Plan: {user.plan}. Balance Due: {user.balance} TND by {user.due_date}."

def get_ticket_status(db: Session, ticket_id: str) -> str:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id.upper()).first()
    if not ticket: return f"Ticket {ticket_id} not found."
    return f"Ticket {ticket.id} status: {ticket.status}. Issue: {ticket.issue_summary}."

def run_remote_diagnostics(session_id: str) -> str:
    signal_dbm = random.randint(-25, -15)
    if signal_dbm > -20: return f"Diagnostic complete. Fiber signal is excellent ({signal_dbm} dBm). The physical line to the home is intact."
    else: return f"Diagnostic complete. Fiber signal is weak ({signal_dbm} dBm). Recommend dispatching a technician."

def create_ticket(db: Session, session_id: str, user_id: str, issue_summary: str, transcript: str = "") -> str:
    ticket_id = f"TKT-{random.randint(10000, 99999)}"
    new_ticket = Ticket(
        id=ticket_id, session_id=uuid.UUID(session_id), user_id=uuid.UUID(user_id),
        issue_summary=issue_summary, transcript=transcript, status="open"
    )
    db.add(new_ticket)
    db.commit()
    from app.services.notifications import send_notification
    send_notification(db, user_id, f"Your support ticket {ticket_id} has been created.")
    return f"Ticket {ticket_id} created successfully."

def schedule_technician_visit(db: Session, session_id: str, user_id: str, issue_type: str, preferred_date: str, time_slot: str, transcript: str = "") -> str:
    ticket_id = f"TKT-{random.randint(10000, 99999)}"
    new_ticket = Ticket(
        id=ticket_id, session_id=uuid.UUID(session_id), user_id=uuid.UUID(user_id),
        issue_summary=f"Technician Visit Required: {issue_type}", transcript=transcript, status="visit_scheduled"
    )
    db.add(new_ticket)
    db.flush()

    try:
        if "tomorrow" in preferred_date.lower() or "after tomorrow" in preferred_date.lower() or "demain" in preferred_date.lower():
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
        ticket_id=ticket_id, user_id=uuid.UUID(user_id), technician_id=chosen_tech.id,
        scheduled_date=visit_date, time_slot=time_slot, status="scheduled"
    )
    db.add(new_visit)
    db.commit()

    from app.services.notifications import send_notification
    send_notification(db, user_id, f"A technician ({chosen_tech.name}) has been scheduled for {visit_date.strftime('%A, %B %d')} ({time_slot}). Ticket ID: {ticket_id}.")
    return f"Success! Ticket {ticket_id} created. A technician named {chosen_tech.name} is scheduled for {visit_date.strftime('%A, %B %d')} during the {time_slot}."

TOOL_DEFINITIONS = [
    {
        "type": "function", "function": {
            "name": "check_outage", "description": "Check if there is an internet outage in a specific city.",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
        }
    },
    {
        "type": "function", "function": {
            "name": "search_knowledge_base", "description": "Search the knowledge base for technical guides, setup, and billing plans.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
        }
    },
    {
        "type": "function", "function": {
            "name": "create_ticket", "description": "Create a support ticket if the issue cannot be resolved automatically.",
            "parameters": {"type": "object", "properties": {"issue_summary": {"type": "string"}}, "required": ["issue_summary"]}
        }
    },
    {
        "type": "function", "function": {
            "name": "schedule_technician_visit", "description": "Schedule a physical technician visit. YOU MUST CALL THIS TOOL to schedule a visit. NEVER tell the user a visit is scheduled without calling this tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_type": {"type": "string"},
                    "preferred_date": {"type": "string"},
                    "time_slot": {"type": "string", "enum": ["morning", "afternoon", "evening"]}
                },
                "required": ["issue_type", "preferred_date", "time_slot"]
            }
        }
    },
    {
        "type": "function", "function": {
            "name": "get_account_status", "description": "Look up the user's specific account details, current internet plan, and billing balance.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function", "function": {
            "name": "get_ticket_status", "description": "Check the current status of a support ticket.",
            "parameters": {"type": "object", "properties": {"ticket_id": {"type": "string"}}, "required": ["ticket_id"]}
        }
    },
    {
        "type": "function", "function": {
            "name": "run_remote_diagnostics", "description": "Run a remote signal test on the fiber line connecting to the user's home.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]

async def execute_tool(db: Session, session_id: str, user_id: str, tool_name: str, arguments: dict, transcript_str: str) -> str:
    try:
        if tool_name == "check_outage":
            return check_outage(db=db, city=arguments.get("city", ""))
        elif tool_name == "create_ticket":
            # Explicit extraction (Fix #2)
            return create_ticket(
                db=db,
                session_id=session_id,
                user_id=user_id,
                issue_summary=arguments.get("issue_summary", "No summary provided"),
                transcript=transcript_str
            )
        elif tool_name == "schedule_technician_visit":
            # Explicit extraction (Fix #2)
            return schedule_technician_visit(
                db=db,
                session_id=session_id,
                user_id=user_id,
                issue_type=arguments.get("issue_type", "Unknown issue"),
                preferred_date=arguments.get("preferred_date", "tomorrow"),
                time_slot=arguments.get("time_slot", "morning"),
                transcript=transcript_str
            )
        elif tool_name == "search_knowledge_base":
            return await search_knowledge_base(query=arguments.get("query", ""), db=db, user_id=user_id, session_id=session_id)
        elif tool_name == "get_account_status":
            # Explicit injection (Fix #3)
            return get_account_status(db=db, user_id=user_id)
        elif tool_name == "get_ticket_status":
            # Explicit extraction (Fix #2 applied to get_ticket_status)
            return get_ticket_status(db=db, ticket_id=arguments.get("ticket_id", ""))
        elif tool_name == "run_remote_diagnostics":
            return run_remote_diagnostics(session_id=session_id)
        else:
            return "Tool not found."
    except Exception as e:
        print(f"EXECUTE_TOOL CRASHED: {e}")
        return "There was an error executing the tool."