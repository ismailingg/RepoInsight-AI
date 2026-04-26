import uuid
import json
import hashlib
import threading
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from backend.core.cloner   import ingest_repo
from backend.core.chunker  import chunk_all_files
from backend.core.embedder import embed_and_store
from backend.config        import TEMP_REPOS_PATH

router = APIRouter()

# In-memory job store
# { job_id: { status, progress, message, result, error } }
jobs = {}


# ── Request / Response models ───────────────────────────────────

class IngestRequest(BaseModel):
    github_url:    str
    token:         Optional[str] = None
    skip_tests:    bool = True      # controlled by UI checkbox
    skip_examples: bool = True      # controlled by UI checkbox


class IngestResponse(BaseModel):
    job_id:  str
    status:  str
    message: str


class StatusResponse(BaseModel):
    job_id:   str
    status:   str             # pending / running / complete / failed
    progress: int             # 0-100
    message:  str
    result:   Optional[dict] = None
    error:    Optional[str]  = None


# ── Background ingestion ────────────────────────────────────────

def run_ingestion(job_id: str, github_url: str,
                  token: Optional[str],
                  skip_tests: bool, skip_examples: bool):
    """
    Runs in a background thread.
    Executes Phase 1 → Phase 2 → Phase 3 and updates job status.
    """
    try:
        # ── Phase 1: Clone + filter ──────────────────────────────
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
            skip_tests=skip_tests,
            skip_examples=skip_examples
        )

        jobs[job_id].update({
            "progress": 50,
            "message":  f"Created {len(chunks)} chunks. Embedding..."
        })

        # ── Phase 3: Embed + store ───────────────────────────────
        stats = embed_and_store(chunks, github_url)

        # Save chunk cache so /query can use grep search
        cache_key  = hashlib.md5(github_url.encode()).hexdigest()[:16]
        cache_path = f"./data/cache_{cache_key}.json"
        with open(cache_path, "w") as f:
            json.dump(chunks, f)

        # Done
        jobs[job_id].update({
            "status":   "complete",
            "progress": 100,
            "message":  "Ingestion complete.",
            "result": {
                "files_found":       len(files),
                "chunks_created":    len(chunks),
                "chunks_embedded":   stats.get("embedded", 0),
                "collection_name":   stats.get("collection_name", ""),
                "skip_tests":        skip_tests,
                "skip_examples":     skip_examples,
                "ingested_at":       __import__("time").time()
            }
        })

    except Exception as e:
        jobs[job_id].update({
            "status":  "failed",
            "progress": 0,
            "message": "Ingestion failed.",
            "error":   str(e)
        })


# ── Endpoints ───────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse)
def start_ingest(req: IngestRequest):
    """
    Start ingestion of a GitHub repo.
    Runs asynchronously — returns job_id immediately.
    Poll GET /status/{job_id} to track progress.
    """
    job_id = str(uuid.uuid4())[:8]

    jobs[job_id] = {
        "status":   "pending",
        "progress": 0,
        "message":  "Job queued...",
        "result":   None,
        "error":    None
    }

    # Run ingestion in background thread
    thread = threading.Thread(
        target=run_ingestion,
        args=(job_id, req.github_url, req.token,
              req.skip_tests, req.skip_examples),
        daemon=True
    )
    thread.start()

    return IngestResponse(
        job_id=job_id,
        status="pending",
        message="Ingestion started. Poll /status/{job_id} for progress."
    )


@router.get("/status/{job_id}", response_model=StatusResponse)
def get_status(job_id: str):
    """Poll this endpoint to check ingestion progress."""
    if job_id not in jobs:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return StatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        message=job["message"],
        result=job.get("result"),
        error=job.get("error")
    )