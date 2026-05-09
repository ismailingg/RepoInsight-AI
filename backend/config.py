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

# Paths — use env vars so they work both locally and on Render
# Locally:  ./data/chroma_db  (relative)
# On Render: /data/chroma_db  (persistent disk mounted at /data)
CHROMA_DB_PATH  = os.getenv("CHROMA_DB_PATH",  "./data/chroma_db")
TEMP_REPOS_PATH = os.getenv("TEMP_REPOS_PATH", "./data/temp_repos")