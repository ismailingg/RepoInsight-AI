import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")

# Rate limits
EMBEDDING_BATCH_SIZE = 20  # Google free tier: batch 20 chunks at once
MAX_FILES_PER_REPO = 1000

# Paths
CHROMA_DB_PATH = "./data/chroma_db"
TEMP_REPOS_PATH = "./data/temp_repos"