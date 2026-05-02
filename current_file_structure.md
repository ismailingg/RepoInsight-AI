repoinsight-ai/
│
├── backend/
│   ├── __init__.py
│   ├── main.py                          ← FastAPI app entry point
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── ingest.py                    ← POST /ingest, GET /status/{job_id}
│   │   └── query.py                     ← POST /query
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── cloner.py                    ← Phase 1: clone + walk repo
│   │   ├── chunker.py                   ← Phase 2: tree-sitter chunking
│   │   ├── embedder.py                  ← Phase 3: embed + store in ChromaDB
│   │   ├── retriever.py                 ← Phase 4: hybrid search
│   │   ├── reranker.py                  ← Phase 5: intent detection + rerank
│   │   └── generator.py                 ← Phase 6: answer generation
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── blocklist.py                 ← file extension filters
│   │   └── llm.py                       ← OpenRouter call_llm() helper
│   │
│   └── config.py                        ← env vars, constants
│
├── frontend/
│   └── app.py                           ← Streamlit UI (2 pages)
│
├── data/
│   ├── chroma_db/                       ← ChromaDB vector storage (git-ignored)
│   ├── temp_repos/                      ← cloned repos (git-ignored)
│   ├── cache_{hash}.json                ← per-repo chunk cache (git-ignored)
│   └── embedding_checkpoint.json        ← resume checkpoint (git-ignored)
│
├── tests/
│   ├── test_phase1.py
│   ├── test_phase2.py
│   ├── test_phase3.py
│   ├── test_phase4.py
│   ├── test_phase5.py
│   └── test_phase6.py
│
├── .env                                 ← API keys (git-ignored)
├── .gitignore
└── requirements.txt