import json
from backend.core.retriever import retrieve

# Load cached chunks for grep search
with open("./data/chunks_cache.json", "r") as f:
    all_chunks = json.load(f)

REPO_URL = "https://github.com/pallets/flask"

# Test 1: Meaning-based question (semantic should shine)
print("\n" + "="*50)
print("TEST 1: Meaning-based question")
print("="*50)
result1 = retrieve(
    question="how does flask handle request context?",
    repo_url=REPO_URL,
    all_chunks=all_chunks
)

# Test 2: Name-based question (grep should shine)
print("\n" + "="*50)
print("TEST 2: Identifier-based question")
print("="*50)
result2 = retrieve(
    question="where is push_appctx used?",
    repo_url=REPO_URL,
    all_chunks=all_chunks
)

# Show results
print("\n" + "="*50)
print("TOP 5 RESULTS — Test 1")
print("="*50)
for chunk in result1["chunks"][:5]:
    print(f"\n  File:       {chunk['file']}")
    print(f"  Lines:      {chunk['start_line']} → {chunk['end_line']}")
    print(f"  Similarity: {chunk['similarity']}")
    print(f"  Source:     {chunk['source']}")
    print(f"  Preview:    {chunk['content'][:100]}...")

print("\n" + "="*50)
print("TOP 5 RESULTS — Test 2")
print("="*50)
for chunk in result2["chunks"][:5]:
    print(f"\n  File:       {chunk['file']}")
    print(f"  Lines:      {chunk['start_line']} → {chunk['end_line']}")
    print(f"  Similarity: {chunk['similarity']}")
    print(f"  Source:     {chunk['source']}")
    if "matched_identifier" in chunk:
        print(f"  Matched:    {chunk['matched_identifier']}")
    print(f"  Preview:    {chunk['content'][:100]}...")