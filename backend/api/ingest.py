import uuid
import json
import hashlib
import threading
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.db.connection import get_db
from backend.db.models import User, RepoSession
from backend.utils.auth import get_current_user
from backend.api.keys import get_user_keys
from backend.core.cloner   import ingest_repo
from backend.core.chunker  import chunk_all_files
from backend.core.embedder import embed_and_store

router = APIRouter()

# In-memory job store (progress tracking only)
# { job_id: { status, progress, message, result, error } }
jobs = {}


# ── Request / Response models ───────────────────────────────────

class IngestRequest(BaseModel):
    github_url:    str
    token:         Optional[str] = None
    skip_tests:    bool = True
    skip_examples: bool = True


class IngestResponse(BaseModel):
    job_id:  str
    status:  str
    message: str


class StatusResponse(BaseModel):
    job_id:   str
    status:   str
    progress: int
    message:  str
    result:   Optional[dict] = None
    error:    Optional[str]  = None


# ── Background ingestion ────────────────────────────────────────

def run_ingestion(
    job_id:       str,
    github_url:   str,
    token:        Optional[str],
    skip_tests:   bool,
    skip_examples: bool,
    user_id:      str,
    user_keys:    dict
):
    """
    Runs in a background thread.
    Phases 1 → 2 → 3, then saves result to PostgreSQL.
    """
    from backend.db.connection import SessionLocal

    db = SessionLocal()

    try:
        # ── Phase 1: Clone ───────────────────────────────────────
        jobs[job_id].update({
            "status":   "running",
            "progress": 10,
            "message":  "Cloning repository..."
        })

        files = ingest_repo(github_url, token)

        jobs[job_id].update({
            "progress": 30,
            "message":  f"Found {len(files)} source files. Chunking..."
        })

        # ── Phase 2: Chunk ───────────────────────────────────────
        chunks = chunk_all_files(
            files,
            skip_tests    = skip_tests,
            skip_examples = skip_examples
        )

        jobs[job_id].update({
            "progress": 50,
            "message":  f"Created {len(chunks)} chunks. Embedding..."
        })

        # ── Phase 3: Embed + store ───────────────────────────────
        stats = embed_and_store(
            chunks   = chunks,
            repo_url = github_url,
            provider = user_keys.get("embedding_provider", "google"),
            api_key  = user_keys.get("embedding_key", ""),
            model    = user_keys.get("embedding_model")
        )

        # Save chunk cache for grep search
        cache_key  = hashlib.md5(github_url.encode()).hexdigest()[:16]
        cache_path = f"./data/cache_{cache_key}.json"
        import os
        os.makedirs("./data", exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(chunks, f)

        # ── Save to PostgreSQL ───────────────────────────────────
        session = db.query(RepoSession).filter(
            RepoSession.user_id  == user_id,
            RepoSession.repo_url == github_url
        ).first()

        now = datetime.utcnow()

        if session:
            # Update existing session
            session.status          = "complete"
            session.chunks_count    = len(chunks)
            session.files_count     = len(files)
            session.vectors_count   = stats.get("embedded", 0)
            session.collection_name = stats.get("collection_name", "")
            session.ingested_at     = now
            session.error_message   = None
            session.updated_at      = now
        else:
            # Create new session
            session = RepoSession(
                user_id         = user_id,
                repo_url        = github_url,
                status          = "complete",
                chunks_count    = len(chunks),
                files_count     = len(files),
                vectors_count   = stats.get("embedded", 0),
                collection_name = stats.get("collection_name", ""),
                ingested_at     = now,
                chat_history    = []
            )
            db.add(session)

        db.commit()

        # Update job
        jobs[job_id].update({
            "status":   "complete",
            "progress": 100,
            "message":  "Ingestion complete.",
            "result": {
                "files_found":     len(files),
                "chunks_created":  len(chunks),
                "chunks_embedded": stats.get("embedded", 0),
                "collection_name": stats.get("collection_name", ""),
                "ingested_at":     now.isoformat()
            }
        })

    except Exception as e:
        # Save failure to PostgreSQL
        try:
            session = db.query(RepoSession).filter(
                RepoSession.user_id  == user_id,
                RepoSession.repo_url == github_url
            ).first()
            if session:
                session.status        = "failed"
                session.error_message = str(e)
                session.updated_at    = datetime.utcnow()
                db.commit()
        except Exception:
            pass

        jobs[job_id].update({
            "status":  "failed",
            "progress": 0,
            "message": "Ingestion failed.",
            "error":   str(e)
        })

    finally:
        db.close()


# ── Endpoints ───────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse)
def start_ingest(
    req:          IngestRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    """
    Start ingestion of a GitHub repo.
    Requires authentication + saved API keys.
    Returns job_id immediately — poll /status/{job_id} for progress.
    """
    # Load user's API keys from DB
    user_keys = get_user_keys(current_user.id, db)

    if not user_keys.get("embedding_key"):
        raise HTTPException(
            status_code=400,
            detail="No embedding API key found. Save your keys in Settings first."
        )

    job_id = str(uuid.uuid4())[:8]

    jobs[job_id] = {
        "status":   "pending",
        "progress": 0,
        "message":  "Job queued...",
        "result":   None,
        "error":    None
    }

    # Create/update repo session in DB with pending status
    existing = db.query(RepoSession).filter(
        RepoSession.user_id  == current_user.id,
        RepoSession.repo_url == req.github_url
    ).first()

    if existing:
        existing.status      = "running"
        existing.updated_at  = datetime.utcnow()
    else:
        new_session = RepoSession(
            user_id      = current_user.id,
            repo_url     = req.github_url,
            status       = "running",
            chat_history = []
        )
        db.add(new_session)
    db.commit()

    # Start background thread
    thread = threading.Thread(
        target=run_ingestion,
        args=(
            job_id,
            req.github_url,
            req.token,
            req.skip_tests,
            req.skip_examples,
            str(current_user.id),
            user_keys
        ),
        daemon=True
    )
    thread.start()

    return IngestResponse(
        job_id  = job_id,
        status  = "pending",
        message = f"Ingestion started. Poll /status/{job_id} for progress."
    )


@router.get("/status/{job_id}", response_model=StatusResponse)
def get_status(job_id: str):
    """Poll this endpoint to check ingestion progress. No auth required."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return StatusResponse(
        job_id   = job_id,
        status   = job["status"],
        progress = job["progress"],
        message  = job["message"],
        result   = job.get("result"),
        error    = job.get("error")
    )