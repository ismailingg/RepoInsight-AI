from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.ingest import router as ingest_router
from backend.api.query  import router as query_router

app = FastAPI(
    title       = "RepoInsight AI",
    description = "Ask natural language questions about any GitHub repository.",
    version     = "1.0.0"
)

# Allow Streamlit frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# Register routers
app.include_router(ingest_router, tags=["Ingestion"])
app.include_router(query_router,  tags=["Query"])


@app.get("/")
def root():
    return {
        "name":    "RepoInsight AI",
        "status":  "running",
        "endpoints": [
            "POST /ingest",
            "GET  /status/{job_id}",
            "POST /query"
        ]
    }