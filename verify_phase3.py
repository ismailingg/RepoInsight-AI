# test_grep.py
import json
from backend.core.retriever import extract_identifiers, grep_search

with open("./data/chunks_cache.json", "r") as f:
    all_chunks = json.load(f)

# Test with a function that definitely exists in Flask
questions = [
    "where is full_dispatch_request used?",
    "how does push_appctx work?",
    "where is AppContext defined?",
    "how does teardown_appcontext work?",
]

for question in questions:
    identifiers = extract_identifiers(question)
    chunks = grep_search(identifiers, None, all_chunks)
    print(f"\nQ: {question}")
    print(f"   Identifiers: {identifiers}")
    print(f"   Chunks found: {len(chunks)}")
    for c in chunks[:3]:
        print(f"     → {c['file']}:{c['start_line']}")