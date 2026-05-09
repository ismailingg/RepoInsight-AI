# RepoInsight AI

> Ask natural language questions about any GitHub repository and get cited, accurate answers grounded in actual source code.

**Live demo →** [your URL]

---

## What it does

You paste a GitHub URL. You ask a question. You get an answer that cites the exact file and line number where the answer lives.

Not a summary. Not a hallucination. Actual code, actual locations.

```
Q: How does authentication work?
A: Authentication is handled in backend/api/auth.py (lines 45-89).
   The login endpoint validates credentials using bcrypt, then issues
   a JWT token via create_token() defined in backend/utils/auth.py (line 34).
   [auth.py:45] [utils/auth.py:34]
```

---

## Architecture

The pipeline runs in six phases:

```
GitHub URL
    │
    ▼
Phase 1 — Clone & Filter
    GitPython clones the repo to a temp directory.
    Walks the file tree, filters to code files only,
    skips binary files, vendor directories, node_modules.
    │
    ▼
Phase 2 — AST Chunking
    tree-sitter parses Python and JavaScript into
    function and class boundaries. Not 50-line windows —
    actual semantic units. Unsupported languages fall
    back to sliding windows with 5-line overlap.
    │
    ▼
Phase 3 — Embed & Store
    Each chunk is embedded via the user's API key
    (Google text-embedding-004 or OpenAI).
    Vectors stored in Qdrant Cloud in a per-user,
    per-repo collection (isolated by MD5 hash of
    user_id + repo_url).
    │
    ▼
Phase 4 — Hybrid Retrieval
    Qdrant ANN search (top-10 semantic results)
    merged with regex grep for identifiers extracted
    from the question (snake_case, UPPER_CASE, PascalCase).
    Chunks found by both get a similarity boost.
    │
    ▼
Phase 5 — Intent Detection + Reranking
    LLM classifies the question:
    EXPLAIN → LLM scores chunks 1-10, keeps top 3
    FIND_ALL → returns all chunks above similarity
               threshold (bypasses top-3 reranking)
    │
    ▼
Phase 6 — Answer Generation
    Query expansion into 3 sub-questions for broader
    context. LLM generates a cited answer. Citation
    validator checks every referenced file actually
    exists in the indexed codebase.
    │
    ▼
Cited Answer
```

### Why hybrid retrieval?

Pure semantic search fails for developer queries. Ask *"where is MAX_RETRIES used?"* and your vector search returns the 3 most similar chunks — but MAX_RETRIES might appear in 23 different files. The FIND_ALL intent path exists specifically for this case.

### Why AST chunking?

Splitting code into fixed-size token windows destroys semantic context. A function that spans lines 1-80 gets split into two chunks that each make partial sense. Tree-sitter preserves function and class boundaries so retrieval operates on complete, meaningful units.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI + Uvicorn |
| Frontend | Streamlit |
| Vector DB | Qdrant Cloud |
| Relational DB | Neon PostgreSQL |
| ORM | SQLAlchemy |
| Code parsing | tree-sitter (Python + JS) |
| Embeddings | Google text-embedding-004 / OpenAI |
| LLM | OpenRouter / Groq / OpenAI / Anthropic |
| Auth | JWT (python-jose) + bcrypt |
| Encryption | AES-256 via Fernet (cryptography) |
| Email | EmailJS |
| Deployment | Render (free tier) |

---

## Bring Your Own Keys

RepoInsight AI has zero vendor lock-in. Users connect their own API keys for both embeddings and LLM inference. Keys are AES-256 encrypted before hitting the database — plaintext is never stored.

**Supported embedding providers:**
- Google (text-embedding-004) — free tier: 1,500 req/day
- OpenAI (text-embedding-3-small / large)

**Supported LLM providers:**
- OpenRouter (free models available: Gemini 2.5 Flash, Llama 3.3 70B)
- Groq (free tier: Llama 3.3 70B, 30 req/min)
- OpenAI
- Anthropic

The entire app can run for free using Google's embedding free tier + Groq's LLM free tier.

---

## Running locally

**Prerequisites:** Python 3.11+, PostgreSQL

**1. Clone and install:**
```bash
git clone https://github.com/yourusername/repoinsight-ai
cd repoinsight-ai
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```

**2. Set up environment variables:**

Create a `.env` file in the project root:
```env
# Database
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/repoinsight

# Auth
SECRET_KEY=your-secret-key-here
APP_SECRET=your-fernet-key-here  # generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Qdrant (leave blank to use local file storage)
QDRANT_URL=
QDRANT_API_KEY=

# Email (EmailJS)
EMAILJS_SERVICE_ID=your-service-id
EMAILJS_TEMPLATE_ID=your-template-id
EMAILJS_PUBLIC_KEY=your-public-key
EMAILJS_PRIVATE_KEY=your-private-key

# App URL (for email verification links)
APP_BASE_URL=http://localhost:8501
```

**3. Set up the database:**
```bash
# Create the database
psql -U postgres -c "CREATE DATABASE repoinsight;"

# Run migrations
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d repoinsight -f backend\db\migrations\001_initial.sql
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d repoinsight -f backend\db\migrations\002_email_verification.sql
```

**4. Start the backend:**
```bash
venv\Scripts\python -m uvicorn backend.Main:app --reload --port 8000
```

**5. Start the frontend (new terminal):**
```bash
streamlit run frontend/app.py
```

Open `http://localhost:8501` in your browser.

---

## Deploying to Render (free)

This repo includes a `render.yaml` Blueprint that creates both services automatically.

**External services you need (all free):**
- [Neon](https://neon.tech) — serverless PostgreSQL, free forever
- [Qdrant Cloud](https://cloud.qdrant.io) — vector database, 1GB free forever
- [EmailJS](https://emailjs.com) — transactional email, 200/month free

**Steps:**

1. Fork this repo and push to your GitHub
2. Go to [render.com](https://render.com) → New → Blueprint → connect your repo
3. Render creates both services automatically from `render.yaml`
4. Set these environment variables manually in the Render dashboard:

**Backend service:**
| Variable | Value |
|---|---|
| `DATABASE_URL` | Neon connection string |
| `QDRANT_URL` | Qdrant cluster URL |
| `QDRANT_API_KEY` | Qdrant API key |
| `APP_BASE_URL` | `https://your-frontend.onrender.com` |
| `EMAILJS_SERVICE_ID` | EmailJS service ID |
| `EMAILJS_TEMPLATE_ID` | EmailJS template ID |
| `EMAILJS_PUBLIC_KEY` | EmailJS public key |
| `EMAILJS_PRIVATE_KEY` | EmailJS private key |

**Frontend service:**
| Variable | Value |
|---|---|
| `API_BASE` | `https://your-backend.onrender.com` |

5. Redeploy the backend — it will run migrations automatically on startup

---

## API Reference

The backend exposes a REST API documented at `/docs` (Swagger UI) when running.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register new account |
| GET | `/auth/verify` | Verify email address |
| POST | `/auth/login` | Login, returns JWT |
| GET | `/auth/me` | Get current user |
| POST | `/keys/` | Save API key |
| GET | `/keys/` | List saved keys |
| DELETE | `/keys/{provider}/{type}` | Delete a key |
| GET | `/repos/` | List indexed repos |
| GET | `/repos/chat` | Get chat history |
| POST | `/repos/chat/append` | Append message |
| POST | `/repos/chat/clear` | Clear chat history |
| DELETE | `/repos/{repo_url}` | Delete repo index |
| POST | `/ingest` | Start repo ingestion |
| GET | `/status/{job_id}` | Poll ingestion progress |
| POST | `/query` | Ask a question |
| DELETE | `/auth/account` | Delete account |

---

## Project Structure

```
repoinsight-ai/
├── backend/
│   ├── Main.py                  # FastAPI app entry point
│   ├── config.py                # Environment configuration
│   ├── api/
│   │   ├── auth.py              # Auth endpoints
│   │   ├── keys.py              # API key management
│   │   ├── sessions.py          # Repo session + chat history
│   │   ├── ingest.py            # Ingestion pipeline trigger
│   │   └── query.py             # Query pipeline trigger
│   ├── core/
│   │   ├── cloner.py            # Phase 1: Clone & filter
│   │   ├── chunker.py           # Phase 2: AST chunking
│   │   ├── embedder.py          # Phase 3: Embed & store
│   │   ├── retriever.py         # Phase 4: Hybrid retrieval
│   │   ├── reranker.py          # Phase 5: Intent + rerank
│   │   └── generator.py         # Phase 6: Answer generation
│   ├── db/
│   │   ├── connection.py        # SQLAlchemy engine + session
│   │   ├── models.py            # User, ApiKey, RepoSession
│   │   └── migrations/          # SQL migration files
│   └── utils/
│       ├── auth.py              # JWT helpers + FastAPI dependency
│       ├── crypto.py            # AES-256 encrypt/decrypt
│       ├── embedding.py         # Multi-provider embedding client
│       ├── llm.py               # Multi-provider LLM client
│       ├── mailer.py            # Email via EmailJS
│       └── blocklist.py         # File/dir filter lists
├── frontend/
│   └── app.py                   # Streamlit UI
├── migrate.py                   # DB migration runner
├── render.yaml                  # Render Blueprint
└── requirements.txt
```

---

## Design Decisions

**Why not an agentic approach?**
Agentic pipelines (LLM decides what tools to call) introduce non-determinism and latency. For a well-scoped problem like codebase Q&A, a structured pipeline with clear phases is faster, cheaper, and more predictable.

**Why Qdrant over ChromaDB/Pinecone?**
Qdrant Cloud offers 1GB free tier with no expiry, cloud persistence (no ephemeral filesystem issues on Render), and a clean Python client. ChromaDB is great locally but doesn't work well on free-tier cloud hosting.

**Why per-user vector collections?**
Shared collections across users create isolation bugs — one user's corrupted or deleted index affects others. MD5(user_id + repo_url) as collection name gives complete isolation with minimal overhead.

**Why store chunk cache as JSON?**
The grep search phase needs to scan all chunks for exact identifier matches — this can't be done efficiently in Qdrant (which is optimized for ANN, not exact string search). The JSON cache gives O(n) grep access without a second database.

---

## License

MIT