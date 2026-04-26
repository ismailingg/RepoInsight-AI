import json
import hashlib
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
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
    sources:    list[Source]
    confidence: float
    intent:     str


# ── Endpoint ────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
def query_repo(req: QueryRequest):
    """
    Ask a question about an ingested repo.
    Returns a cited answer with file + line references.
    """
    # Load chunk cache for this repo (needed for grep search)
    cache_key  = hashlib.md5(req.github_url.encode()).hexdigest()[:16]
    cache_path = f"./data/cache_{cache_key}.json"

    try:
        with open(cache_path, "r") as f:
            all_chunks = json.load(f)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Repo not ingested yet. Call POST /ingest first."
        )

    # Valid files list for citation validation
    valid_files = list(set(c["relative_path"] for c in all_chunks))

    # Phase 4: Retrieve
    retrieval = retrieve(req.question, req.github_url, all_chunks)

    # Phase 5: Re-rank
    reranked = rerank(req.question, retrieval["chunks"])

    # Phase 6: Generate
    result = generate(
        question     = req.question,
        final_chunks = reranked["final_chunks"],
        repo_url     = req.github_url,
        all_chunks   = all_chunks,
        valid_files  = valid_files,
        retrieve_fn  = lambda q, url, chunks: retrieve(q, url, chunks),
        rerank_fn    = lambda q, chunks: rerank(q, chunks)
    )

    return QueryResponse(
        answer     = result["answer"],
        sources    = result["sources"],
        confidence = result["confidence"],
        intent     = result["intent"]
    )