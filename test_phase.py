import os
import json
from backend.core.cloner import ingest_repo
from backend.core.chunker import chunk_all_files
from backend.core.embedder import embed_and_store

CACHE_FILE  = "./data/chunks_cache.json"
REPO_URL    = "https://github.com/pallets/flask"

# ── Load from cache if available ────────────────────────────────
if os.path.exists(CACHE_FILE):
    print("=== Loaded cached chunks (skipping clone + chunk) ===")
    with open(CACHE_FILE, "r") as f:
        chunks = json.load(f)
    print(f"✓ {len(chunks)} chunks loaded from cache\n")
else:
    print("=== Phase 1: Cloning repo ===")
    files = ingest_repo(REPO_URL)

    print("\n=== Phase 2: Chunking files ===")
    chunks = chunk_all_files(files, skip_tests=True, skip_examples=True)

    os.makedirs("./data", exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(chunks, f)
    print(f"✓ Chunks cached — won't re-clone next run\n")

# ── Phase 3 ──────────────────────────────────────────────────────
stats = embed_and_store(chunks, REPO_URL)

print("\n=== Final Statistics ===")
print(f"Total chunks:        {stats['total_chunks']}")
print(f"Unique chunks:       {stats['unique_chunks']}")
print(f"Embedded:            {stats['embedded']}")
if "collection_name" in stats:
    print(f"ChromaDB collection: {stats['collection_name']}")