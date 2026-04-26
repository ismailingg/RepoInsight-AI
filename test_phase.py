import json
from backend.core.retriever import retrieve
from backend.core.reranker import rerank

with open("./data/chunks_cache.json", "r") as f:
    all_chunks = json.load(f)

REPO_URL = "https://github.com/pallets/flask"

# ── Test 1: Should detect EXPLAIN ───────────────────────────────
question1 = "how does flask handle request context?"

print("\n" + "="*50)
print(f"TEST 1 (expect EXPLAIN): {question1}")
print("="*50)

retrieval1 = retrieve(question1, REPO_URL, all_chunks)
result1    = rerank(question1, retrieval1["chunks"])

print(f"\n✓ Intent:  {result1['intent']}")
print(f"✓ Chunks in:  {result1['stats']['input_chunks']}")
print(f"✓ Chunks out: {result1['stats']['output_chunks']}")

# ── Test 2: Should detect FIND_ALL ──────────────────────────────
question2 = "where is teardown_appcontext used?"

print("\n" + "="*50)
print(f"TEST 2 (expect FIND_ALL): {question2}")
print("="*50)

retrieval2 = retrieve(question2, REPO_URL, all_chunks)
result2    = rerank(question2, retrieval2["chunks"])

print(f"\n✓ Intent:  {result2['intent']}")
print(f"✓ Chunks in:  {result2['stats']['input_chunks']}")
print(f"✓ Chunks out: {result2['stats']['output_chunks']}")

# ── Test 3: Ambiguous — should default to FIND_ALL ──────────────
question3 = "how and where is AppContext used?"

print("\n" + "="*50)
print(f"TEST 3 (expect FIND_ALL): {question3}")
print("="*50)

retrieval3 = retrieve(question3, REPO_URL, all_chunks)
result3    = rerank(question3, retrieval3["chunks"])

print(f"\n✓ Intent:  {result3['intent']}")
print(f"✓ Chunks in:  {result3['stats']['input_chunks']}")
print(f"✓ Chunks out: {result3['stats']['output_chunks']}")