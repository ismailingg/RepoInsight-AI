repoinsight-ai/
│
├── backend/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py                      ← NEW: POST /register, POST /login
│   │   ├── keys.py                      ← NEW: POST /keys, GET /keys, DELETE /keys
│   │   ├── sessions.py                  ← NEW: GET /repos, GET /repos/{repo}/chat
│   │   ├── ingest.py                    ← UPDATED: auth + user keys
│   │   └── query.py                     ← UPDATED: auth + user keys
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── cloner.py                    ← unchanged
│   │   ├── chunker.py                   ← unchanged
│   │   ├── embedder.py                  ← UPDATED: accept keys as params
│   │   ├── retriever.py                 ← UPDATED: accept keys as params
│   │   ├── reranker.py                  ← UPDATED: accept keys as params
│   │   └── generator.py                 ← UPDATED: accept keys as params
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py                ← NEW: PostgreSQL connection pool
│   │   ├── models.py                    ← NEW: SQLAlchemy table definitions
│   │   └── migrations/
│   │       └── 001_initial.sql          ← NEW: schema creation script
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── blocklist.py                 ← unchanged
│   │   ├── llm.py                       ← UPDATED: multi-provider support
│   │   ├── embedding.py                 ← NEW: multi-provider embedding client
│   │   ├── auth.py                      ← NEW: JWT validation dependency
│   │   └── crypto.py                    ← NEW: AES encrypt/decrypt keys
│   │
│   └── config.py                        ← UPDATED: new env vars
│
├── frontend/
│   └── app.py                           ← FULL REWRITE: 4 pages + auth
│
├── data/
│   ├── chroma_db/
│   ├── temp_repos/
│   ├── cache_{hash}.json
│   └── embedding_checkpoint.json
│
├── tests/
│   └── ...
│
├── .env                                 ← UPDATED: DB_URL, SECRET_KEY, APP_SECRET
├── .gitignore
├── requirements.txt                     ← UPDATED: new packages
├── render.yaml                          ← NEW: Render deployment config
└── Dockerfile                           ← NEW: container config