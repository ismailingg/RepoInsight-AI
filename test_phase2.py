from backend.core.cloner import ingest_repo
from backend.core.chunker import chunk_all_files

# Step 1: Phase 1 - get files
print("=== Phase 1: Cloning repo ===")
files = ingest_repo("https://github.com/pallets/flask")

# Step 2: Phase 2 - chunk them
print("\n=== Phase 2: Chunking files ===")
chunks = chunk_all_files(files)

# Show sample output
print("\n=== Sample chunk ===")
sample = chunks[0]
print(f"File:       {sample['relative_path']}")
print(f"Lines:      {sample['start_line']} → {sample['end_line']}")
print(f"Type:       {sample['chunk_type']}")
print(f"Language:   {sample['language']}")
print(f"Chunk ID:   {sample['chunk_id']}")
print(f"Content preview:\n{sample['content'][:300]}")