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