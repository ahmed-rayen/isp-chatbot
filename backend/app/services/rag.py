import json
import os
import uuid
from dataclasses import dataclass, field

import httpx
import numpy as np
from openai import AsyncOpenAI, OpenAI
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from app.config import settings
from app.models.db_models import KBHit, KBMiss

# --- Constants ---
KB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "knowledge_base.json")
EMBEDDING_MODEL = "baai/bge-m3"
RERANKER_MODEL = "baai/bge-reranker-v2-m3"
RERANKER_URL = "https://integrate.api.nvidia.com/v1/ranking"

RRF_K = 60
VECTOR_TOP_K = 5
BM25_TOP_K = 5
RERANK_TOP_K = 3

RRF_SCORE_THRESHOLD = 0.005
RERANKER_LOGIT_THRESHOLD = -2.0
CATEGORY_BOOST = 1.2
MIN_CHUNK_LENGTH = 15

BILLING_KEYWORDS = ["price", "plan", "bill", "invoice", "pay", "tnd", "mbps"]


@dataclass
class RAGState:
    """Holds the in-memory RAG index."""
    chunks: list[dict] = field(default_factory=list)
    embeddings: list[list[float]] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    bm25: BM25Okapi | None = None
    is_initialized: bool = False


state = RAGState()
async_client = AsyncOpenAI(base_url=settings.nvidia_base_url, api_key=settings.nvidia_api_key)


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))


def classify_query(query: str) -> str:
    if any(word in query.lower() for word in BILLING_KEYWORDS):
        return "billing"
    return "technical"


async def initialize_rag() -> None:
    """Build KB embeddings and BM25 index. Call once at app startup."""
    if state.is_initialized:
        return

    sync_client = OpenAI(base_url=settings.nvidia_base_url, api_key=settings.nvidia_api_key)

    try:
        with open(KB_PATH, "r", encoding="utf-8") as f:
            kb_data = json.load(f)

        bm25_corpus: list[list[str]] = []

        for item in kb_data:
            for chunk in item["content"].split("\n"):
                chunk = chunk.strip()
                if len(chunk) <= MIN_CHUNK_LENGTH:
                    continue

                text_to_embed = f"{item['topic']} {' '.join(item['tags'])} {chunk}"
                vector = sync_client.embeddings.create(
                    model=EMBEDDING_MODEL, input=text_to_embed, encoding_format="float"
                ).data[0].embedding

                state.chunks.append({"text": chunk, "topic": item["topic"]})
                state.embeddings.append(vector)
                state.categories.append(item.get("category", "general"))
                bm25_corpus.append(text_to_embed.lower().split())

        if bm25_corpus:
            state.bm25 = BM25Okapi(bm25_corpus)

        state.is_initialized = True
        print(f"🧠 {len(state.chunks)} KB chunks embedded & BM25 indexed!")
    except Exception as e:
        print(f"⚠️ Could not generate KB indices. RAG will be disabled. Error: {e}")


async def _rerank_chunks(query: str, chunks: list[str]) -> tuple[list[str], float]:
    """Re-rank candidate chunks using NVIDIA cross-encoder."""
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                RERANKER_URL,
                headers={
                    "Authorization": f"Bearer {settings.nvidia_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": RERANKER_MODEL,
                    "query": query,
                    "passages": [{"text": c} for c in chunks],
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            ranked = sorted(data["rankings"], key=lambda x: x["logit"], reverse=True)
            top_chunks = [chunks[r["index"]] for r in ranked[:RERANK_TOP_K]]
            top_logit = ranked[0]["logit"] if ranked else -10.0
            return top_chunks, top_logit
    except Exception as e:
        print(f"Reranker failed, falling back: {e}")
        return chunks[:RERANK_TOP_K], 0.0


def _record_kb_miss(db: Session, user_id: str | None, query: str) -> str:
    db_user_id = uuid.UUID(user_id) if user_id else None
    db.add(KBMiss(user_id=db_user_id, query=query))
    db.commit()
    return "No information found in the knowledge base for this query."


async def search_knowledge_base(
    query: str,
    db: Session,
    user_id: str | None = None,
    session_id: str | None = None,
) -> str:
    """Hybrid search: vector + BM25 → RRF → cross-encoder reranking."""
    if not state.is_initialized:
        return "Knowledge base is not initialized."

    try:
        rrf_scores: dict[int, float] = {}
        target_category = classify_query(query)

        # 1. Vector search
        response = await async_client.embeddings.create(
            model=EMBEDDING_MODEL, input=query, encoding_format="float"
        )
        query_vector = response.data[0].embedding

        vector_scores = [
            (i, cosine_similarity(query_vector, vec) * (CATEGORY_BOOST if state.categories[i] == target_category else 1.0))
            for i, vec in enumerate(state.embeddings)
        ]
        vector_scores.sort(key=lambda x: x[1], reverse=True)
        top_vector_indices = [idx for idx, _ in vector_scores[:VECTOR_TOP_K]]

        # 2. BM25 keyword search
        bm25_scores = state.bm25.get_scores(query.lower().split())
        top_bm25_indices = np.argsort(bm25_scores)[::-1][:BM25_TOP_K]

        # 3. Reciprocal Rank Fusion
        for rank, idx in enumerate(top_vector_indices):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1 / (RRF_K + rank + 1)
        for rank, idx in enumerate(top_bm25_indices):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1 / (RRF_K + rank + 1)

        sorted_rrf = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        # KB Miss: RRF score too low
        if not sorted_rrf or sorted_rrf[0][1] < RRF_SCORE_THRESHOLD:
            return _record_kb_miss(db, user_id, query)

        top_candidate_indices = [idx for idx, _ in sorted_rrf[:5]]
        candidate_chunks = [state.chunks[idx]["text"] for idx in top_candidate_indices]

        # 4. Cross-encoder re-ranking
        final_chunks, top_logit = await _rerank_chunks(query, candidate_chunks)

        # KB Miss: Re-ranker logit too low
        if top_logit < RERANKER_LOGIT_THRESHOLD and top_logit != 0.0:
            return _record_kb_miss(db, user_id, query)

        # Log KB hits for feedback loop
        if session_id and final_chunks:
            for chunk in final_chunks:
                topic = next(
                    (state.chunks[idx]["topic"] for idx in top_candidate_indices if state.chunks[idx]["text"] == chunk),
                    "unknown",
                )
                db.add(KBHit(session_id=uuid.UUID(session_id), chunk_text=chunk, topic=topic))
            db.commit()

        return "\n".join(final_chunks)

    except Exception as e:
        return f"Error during hybrid search: {str(e)}"