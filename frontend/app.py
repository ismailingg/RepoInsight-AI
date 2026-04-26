import time
import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title = "RepoInsight AI",
    page_icon  = "🔍",
    layout     = "wide"
)

# ── Session state defaults ──────────────────────────────────────
if "ingested_repo"  not in st.session_state: st.session_state.ingested_repo  = None
if "ingested_at"    not in st.session_state: st.session_state.ingested_at    = None
if "chat_history"   not in st.session_state: st.session_state.chat_history   = []
if "job_id"         not in st.session_state: st.session_state.job_id         = None


# ── Sidebar ─────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔍 RepoInsight AI")
    st.caption("Ask questions about any GitHub repository")
    st.divider()

    page = st.radio(
        "Navigation",
        ["📥 Ingest Repository", "💬 Ask Questions"],
        label_visibility="collapsed"
    )

    if st.session_state.ingested_repo:
        st.divider()
        st.success(f"**Active repo:**")
        st.code(st.session_state.ingested_repo, language=None)

        if st.session_state.ingested_at:
            age_hours = (time.time() - st.session_state.ingested_at) / 3600
            if age_hours > 24:
                st.warning(f"⚠️ Index is {age_hours:.0f}h old — consider re-ingesting")
            else:
                st.caption(f"Indexed {age_hours:.1f}h ago")


# ════════════════════════════════════════════════════════════════
# PAGE 1 — INGEST
# ════════════════════════════════════════════════════════════════
if page == "📥 Ingest Repository":

    st.title("📥 Ingest a GitHub Repository")
    st.caption(
        "Paste a GitHub URL below. RepoInsight will clone it, chunk the code, "
        "and build a searchable index."
    )

    st.divider()

    # ── Inputs ───────────────────────────────────────────────────
    github_url = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/pallets/flask",
        help="Public or private repository URL"
    )

    token = st.text_input(
        "GitHub Personal Access Token (optional)",
        type="password",
        help="Only needed for private repositories"
    )

    st.subheader("Ingestion Options")
    st.caption(
        "By default, test files and examples are excluded to focus the index "
        "on core source code. Enable them if you need to query tests or examples."
    )

    col1, col2 = st.columns(2)
    with col1:
        include_tests = st.checkbox(
            "Include test files",
            value=False,
            help="Test files are indexed last. If the chunk limit is hit, "
                 "tests are skipped first to preserve core code."
        )
    with col2:
        include_examples = st.checkbox(
            "Include examples / tutorials",
            value=False,
            help="Example and tutorial folders are excluded by default."
        )

    # Checkbox → API flag conversion (inverted logic)
    # "Include tests" unchecked → skip_tests=True
    skip_tests    = not include_tests
    skip_examples = not include_examples

    st.divider()

    # ── Ingest button ────────────────────────────────────────────
    if st.button("🚀 Start Ingestion", type="primary", use_container_width=True):
        if not github_url.strip():
            st.error("Please enter a GitHub URL.")
        else:
            with st.spinner("Starting ingestion job..."):
                try:
                    resp = requests.post(
                        f"{API_BASE}/ingest",
                        json={
                            "github_url":    github_url.strip(),
                            "token":         token or None,
                            "skip_tests":    skip_tests,
                            "skip_examples": skip_examples
                        }
                    )
                    data = resp.json()
                    st.session_state.job_id = data["job_id"]
                    st.session_state.ingested_repo = github_url.strip()

                except Exception as e:
                    st.error(f"Failed to connect to API: {e}")
                    st.info("Make sure the backend is running: `uvicorn backend.main:app --reload`")

    # ── Progress polling ─────────────────────────────────────────
    if st.session_state.job_id:
        job_id = st.session_state.job_id

        status_placeholder  = st.empty()
        progress_placeholder = st.empty()
        message_placeholder = st.empty()

        # Poll until done
        while True:
            try:
                resp   = requests.get(f"{API_BASE}/status/{job_id}")
                status = resp.json()
            except Exception as e:
                st.error(f"Lost connection to API: {e}")
                break

            progress = status["progress"]
            message  = status["message"]
            state    = status["status"]

            # Update UI
            progress_placeholder.progress(progress / 100)
            message_placeholder.caption(f"Status: {message}")

            if state == "complete":
                result = status.get("result", {})
                status_placeholder.success("✅ Ingestion complete!")
                st.session_state.ingested_at = result.get("ingested_at")
                st.session_state.job_id      = None

                # Show summary
                col1, col2, col3 = st.columns(3)
                col1.metric("Files Found",      result.get("files_found", 0))
                col2.metric("Chunks Created",   result.get("chunks_created", 0))
                col3.metric("Chunks Embedded",  result.get("chunks_embedded", 0))

                st.info("💬 Go to **Ask Questions** in the sidebar to start querying!")
                break

            elif state == "failed":
                status_placeholder.error(f"❌ Ingestion failed: {status.get('error')}")
                st.session_state.job_id = None
                break

            else:
                status_placeholder.info(f"⏳ {state.capitalize()}...")
                time.sleep(3)
                st.rerun()


# ════════════════════════════════════════════════════════════════
# PAGE 2 — Q&A CHAT
# ════════════════════════════════════════════════════════════════
elif page == "💬 Ask Questions":

    st.title("💬 Ask Questions About the Codebase")

    # Guard — must ingest first
    if not st.session_state.ingested_repo:
        st.warning("⚠️ No repository ingested yet. Go to **Ingest Repository** first.")
        st.stop()

    st.caption(f"Querying: `{st.session_state.ingested_repo}`")
    st.divider()

    # ── Chat history ─────────────────────────────────────────────
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # Show sources for assistant messages
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander(
                    f"📎 {len(msg['sources'])} sources cited  |  "
                    f"confidence: {msg.get('confidence', 0):.2f}  |  "
                    f"intent: {msg.get('intent', '')}"
                ):
                    for src in msg["sources"]:
                        st.code(
                            f"# {src['file']} — line {src['line']}\n"
                            f"{src['snippet']}",
                            language="python"
                        )

    # ── Question input ───────────────────────────────────────────
    question = st.chat_input("Ask something about the codebase...")

    if question:
        # Add user message
        st.session_state.chat_history.append({
            "role":    "user",
            "content": question
        })

        with st.chat_message("user"):
            st.markdown(question)

        # Call API
        with st.chat_message("assistant"):
            with st.spinner("Searching codebase..."):
                try:
                    resp = requests.post(
                        f"{API_BASE}/query",
                        json={
                            "github_url": st.session_state.ingested_repo,
                            "question":   question
                        },
                        timeout=120
                    )

                    if resp.status_code == 404:
                        answer = ("⚠️ This repo hasn't been ingested yet, "
                                  "or the index was cleared. Please re-ingest.")
                        sources    = []
                        confidence = 0.0
                        intent     = "error"

                    elif resp.status_code != 200:
                        answer = f"❌ API error {resp.status_code}: {resp.text}"
                        sources    = []
                        confidence = 0.0
                        intent     = "error"

                    else:
                        data       = resp.json()
                        answer     = data["answer"]
                        sources    = data["sources"]
                        confidence = data["confidence"]
                        intent     = data["intent"]

                except requests.exceptions.Timeout:
                    answer = "⏱️ Request timed out. Try a simpler question."
                    sources    = []
                    confidence = 0.0
                    intent     = "error"

                except Exception as e:
                    answer = f"❌ Failed to connect to API: {e}"
                    sources    = []
                    confidence = 0.0
                    intent     = "error"

            # Display answer
            st.markdown(answer)

            # Display sources in expander
            if sources:
                with st.expander(
                    f"📎 {len(sources)} sources cited  |  "
                    f"confidence: {confidence:.2f}  |  "
                    f"intent: {intent}"
                ):
                    for src in sources:
                        st.code(
                            f"# {src['file']} — line {src['line']}\n"
                            f"{src['snippet']}",
                            language="python"
                        )

        # Save to chat history
        st.session_state.chat_history.append({
            "role":       "assistant",
            "content":    answer,
            "sources":    sources,
            "confidence": confidence,
            "intent":     intent
        })

    # ── Clear chat ───────────────────────────────────────────────
    if st.session_state.chat_history:
        if st.button("🗑️ Clear chat history"):
            st.session_state.chat_history = []
            st.rerun()