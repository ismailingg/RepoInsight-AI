import json
import hashlib
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List
from backend.db.connection import get_db
from backend.db.models import User, RepoSession
from backend.utils.auth import get_current_user
from backend.api.keys import get_user_keys
from backend.core.retriever import retrieve
from backend.core.reranker  import rerank
from backend.core.generator import generate

router = APIRouter()


# ── Request / Response models ───────────────────────────────────

class QueryRequest(BaseModel):
    github_url: str
    question:   str


class Source(BaseModel):
    file:    str
    line:    int
    snippet: str


class QueryResponse(BaseModel):
    answer:     str
    sources:    List[Source]
    confidence: float
    intent:     str


# ── Endpoint ────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
def query_repo(
    req:          QueryRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    """
    Ask a question about an ingested repo.
    Requires authentication + saved API keys.
    """
    # Load user's API keys
    user_keys = get_user_keys(current_user.id, db)

    if not user_keys.get("embedding_key"):
        raise HTTPException(
            status_code=400,
            detail="No embedding API key found. Save your keys in Settings first."
        )

    if not user_keys.get("llm_key"):
        raise HTTPException(
            status_code=400,
            detail="No LLM API key found. Save your keys in Settings first."
        )

    # Verify repo is ingested for this user
    session = db.query(RepoSession).filter(
        RepoSession.user_id  == current_user.id,
        RepoSession.repo_url == req.github_url
    ).first()

    if not session or session.status != "complete":
        raise HTTPException(
            status_code=404,
            detail="Repo not ingested yet. Call POST /ingest first."
        )

    # Load chunk cache for grep search
    cache_key  = hashlib.md5(req.github_url.encode()).hexdigest()[:16]
    cache_path = f"./data/cache_{cache_key}.json"

    try:
        with open(cache_path, "r") as f:
            all_chunks = json.load(f)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Chunk cache not found. Please re-ingest this repository."
        )

    # Valid files for citation validation
    valid_files = list(set(c["relative_path"] for c in all_chunks))

    # Phase 4: Retrieve
    retrieval = retrieve(
        question   = req.question,
        repo_url   = req.github_url,
        all_chunks = all_chunks,
        provider   = user_keys.get("embedding_provider", "google"),
        api_key    = user_keys.get("embedding_key", ""),
        model      = user_keys.get("embedding_model")
    )

    # Phase 5: Re-rank
    reranked = rerank(
        question = req.question,
        chunks   = retrieval["chunks"],
        provider = user_keys.get("llm_provider", "openrouter"),
        api_key  = user_keys.get("llm_key", ""),
        model    = user_keys.get("llm_model")
    )

    # Phase 6: Generate
    result = generate(
        question     = req.question,
        final_chunks = reranked["final_chunks"],
        repo_url     = req.github_url,
        all_chunks   = all_chunks,
        valid_files  = valid_files,
        provider     = user_keys.get("llm_provider", "openrouter"),
        api_key      = user_keys.get("llm_key", ""),
        model        = user_keys.get("llm_model"),
        retrieve_fn  = lambda q, url, chunks: retrieve(
            q, url, chunks,
            provider = user_keys.get("embedding_provider", "google"),
            api_key  = user_keys.get("embedding_key", ""),
            model    = user_keys.get("embedding_model")
        ),
        rerank_fn = lambda q, chunks: rerank(
            q, chunks,
            provider = user_keys.get("llm_provider", "openrouter"),
            api_key  = user_keys.get("llm_key", ""),
            model    = user_keys.get("llm_model")
        )
    )

    return QueryResponse(
        answer     = result["answer"],
        sources    = result["sources"],
        confidence = result["confidence"],
        intent     = result["intent"]
    )