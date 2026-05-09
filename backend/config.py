import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY     = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL       = os.getenv("GEMINI_MODEL", "google/gemini-2.5-flash:free")
EMBEDDING_MODEL    = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Rate limits
EMBEDDING_BATCH_SIZE = 20
MAX_FILES_PER_REPO   = 1000

# Qdrant — cloud (Render) vs local (development)
# Set QDRANT_URL + QDRANT_API_KEY in .env / Render dashboard for cloud
# Leave blank to use local file-based storage for development
QDRANT_URL        = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY    = os.getenv("QDRANT_API_KEY", "")
QDRANT_LOCAL_PATH = os.getenv("QDRANT_LOCAL_PATH", "./data/qdrant")

# Legacy paths (kept for temp repo cloning)
TEMP_REPOS_PATH = os.getenv("TEMP_REPOS_PATH", "./data/temp_repos")

# Kept for backward compat — no longer used for vector storage
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")