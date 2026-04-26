import json
from backend.core.retriever import retrieve
from backend.core.reranker  import rerank
from backend.core.generator import generate

# Load cached chunks
with open("./data/chunks_cache.json", "r") as f:
    all_chunks = json.load(f)

REPO_URL    = "https://github.com/pallets/flask"
valid_files = list(set(c["relative_path"] for c in all_chunks))

def run_query(question: str):
    print("\n" + "="*60)
    print(f"QUESTION: {question}")
    print("="*60)

    # Phase 4
    retrieval = retrieve(question, REPO_URL, all_chunks)

    # Phase 5
    reranked  = rerank(question, retrieval["chunks"])

    # Phase 6
    result = generate(
        question     = question,
        final_chunks = reranked["final_chunks"],
        repo_url     = REPO_URL,
        all_chunks   = all_chunks,
        valid_files  = valid_files,
        retrieve_fn  = lambda q, url, chunks: retrieve(q, url, chunks),
        rerank_fn    = lambda q, chunks: rerank(q, chunks)
    )

    # Print result
    print("\n" + "="*60)
    print("ANSWER:")
    print("="*60)
    print(result["answer"])
    print(f"\nConfidence: {result['confidence']}")
    print(f"Sources:    {len(result['sources'])} chunks cited")
    print(f"Intent:     {result['intent']}")

# Test 1: Conceptual question
run_query("how does flask handle request context?")

# Test 2: Location question
run_query("where is teardown_appcontext used?")