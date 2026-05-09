from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.db.connection import init_db
from backend.api.ingest   import router as ingest_router
from backend.api.query    import router as query_router
from backend.api.auth     import router as auth_router
from backend.api.keys     import router as keys_router
from backend.api.sessions import router as sessions_router

app = FastAPI(
    title       = "RepoInsight AI",
    description = "Ask natural language questions about any GitHub repository.",
    version     = "1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

@app.on_event("startup")
def startup():
    import os
    from backend.config import CHROMA_DB_PATH, TEMP_REPOS_PATH
    # Ensure data directories exist (important on Render persistent disk)
    os.makedirs(CHROMA_DB_PATH,  exist_ok=True)
    os.makedirs(TEMP_REPOS_PATH, exist_ok=True)
    print(f"[STARTUP] Data dirs ready: {CHROMA_DB_PATH}, {TEMP_REPOS_PATH}")
    # Run SQLAlchemy table creation (idempotent)
    init_db()
    # Run SQL migrations
    try:
        from migrate import run_migrations
        run_migrations()
    except Exception as e:
        print(f"[STARTUP] Migration warning: {e}")

app.include_router(auth_router,     tags=["Auth"])
app.include_router(keys_router,     tags=["API Keys"])
app.include_router(sessions_router, tags=["Repo Sessions"])
app.include_router(ingest_router,   tags=["Ingestion"])
app.include_router(query_router,    tags=["Query"])


@app.get("/")
def root():
    return {
        "name":    "RepoInsight AI",
        "status":  "running",
        "endpoints": [
            "POST /auth/register",
            "POST /auth/login",
            "GET  /auth/me",
            "POST /keys",
            "GET  /keys",
            "DELETE /keys/{provider}/{key_type}",
            "GET  /repos",
            "GET  /repos/chat?repo_url=...",
            "POST /repos/chat/append",
            "POST /repos/chat/clear",
            "POST /ingest",
            "GET  /status/{job_id}",
            "POST /query"
        ]
    }