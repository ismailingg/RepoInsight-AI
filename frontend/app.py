import time
import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="RepoInsight AI",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Global CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Syne:wght@400;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"] {
    background-color: #0a0a0a !important;
    color: #e8e8e8 !important;
    font-family: 'Space Mono', monospace !important;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse 80% 50% at 20% 0%, rgba(255,80,0,0.06) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 100%, rgba(255,200,0,0.04) 0%, transparent 60%),
        #0a0a0a !important;
}

[data-testid="stSidebar"] {
    background: #0f0f0f !important;
    border-right: 1px solid #1e1e1e !important;
}
[data-testid="stSidebar"] * { font-family: 'Space Mono', monospace !important; }

#MainMenu, footer, header, [data-testid="stToolbar"],
[data-testid="stDecoration"] { display: none !important; }

h1, h2, h3 { font-family: 'Syne', sans-serif !important; letter-spacing: -0.02em; }

[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #111 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 0 !important;
    color: #e8e8e8 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 13px !important;
    transition: border-color 0.2s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #ff5000 !important;
    box-shadow: 0 0 0 1px #ff5000 !important;
}

[data-testid="stButton"] button[kind="primary"] {
    background: #ff5000 !important;
    color: #0a0a0a !important;
    border: none !important;
    border-radius: 0 !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    transition: all 0.15s !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    background: #ff6a1f !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(255,80,0,0.3) !important;
}

[data-testid="stButton"] button[kind="secondary"] {
    background: transparent !important;
    color: #444 !important;
    border: 1px solid #222 !important;
    border-radius: 0 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 0.08em !important;
    transition: all 0.15s !important;
}
[data-testid="stButton"] button[kind="secondary"]:hover {
    border-color: #ff5000 !important;
    color: #ff5000 !important;
}

[data-testid="stProgressBar"] > div > div {
    background: linear-gradient(90deg, #ff5000, #ffaa00) !important;
    border-radius: 0 !important;
}
[data-testid="stProgressBar"] > div {
    background: #1a1a1a !important;
    border-radius: 0 !important;
    height: 2px !important;
}

[data-testid="stMetric"] {
    background: #0d0d0d !important;
    border: 1px solid #1e1e1e !important;
    border-top: 2px solid #ff5000 !important;
    padding: 20px !important;
    border-radius: 0 !important;
}
[data-testid="stMetricLabel"] {
    color: #444 !important;
    font-size: 10px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    font-family: 'Space Mono', monospace !important;
}
[data-testid="stMetricValue"] {
    color: #e8e8e8 !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 32px !important;
    font-weight: 700 !important;
}

[data-testid="stCheckbox"] label {
    color: #666 !important;
    font-size: 12px !important;
    font-family: 'Space Mono', monospace !important;
}

[data-testid="stAlert"] {
    border-radius: 0 !important;
    border-left: 3px solid #ff5000 !important;
    background: #0d0d0d !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 12px !important;
}

[data-testid="stCode"], [data-testid="stCodeBlock"] {
    border-radius: 0 !important;
    border: 1px solid #1a1a1a !important;
    background: #0d0d0d !important;
}

[data-testid="stExpander"] {
    border: 1px solid #1a1a1a !important;
    border-radius: 0 !important;
    background: #0d0d0d !important;
}
[data-testid="stExpander"] summary {
    font-family: 'Space Mono', monospace !important;
    font-size: 11px !important;
    color: #444 !important;
    letter-spacing: 0.06em !important;
}
[data-testid="stExpander"] summary:hover { color: #ff5000 !important; }

[data-testid="stChatMessage"] {
    background: transparent !important;
    border-bottom: 1px solid #0f0f0f !important;
    padding: 20px 0 !important;
}

[data-testid="stChatMessageContent"] p {
    font-family: 'Space Mono', monospace !important;
    font-size: 13px !important;
    line-height: 1.9 !important;
    color: #bbb !important;
}

[data-testid="stChatInput"] textarea {
    background: #111 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 0 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 13px !important;
    color: #e8e8e8 !important;
}
[data-testid="stChatInput"] textarea:focus { border-color: #ff5000 !important; }
[data-testid="stChatInput"] button { background: #ff5000 !important; border-radius: 0 !important; }

[data-testid="stRadio"] label {
    font-family: 'Space Mono', monospace !important;
    font-size: 11px !important;
    color: #555 !important;
    letter-spacing: 0.1em !important;
}

hr { border-color: #1a1a1a !important; }

::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: #0a0a0a; }
::-webkit-scrollbar-thumb { background: #222; }
::-webkit-scrollbar-thumb:hover { background: #ff5000; }
</style>
""", unsafe_allow_html=True)


# ── Session state ────────────────────────────────────────────────
if "ingested_repo"  not in st.session_state: st.session_state.ingested_repo  = None
if "ingested_at"    not in st.session_state: st.session_state.ingested_at    = None
if "chat_history"   not in st.session_state: st.session_state.chat_history   = []
if "job_id"         not in st.session_state: st.session_state.job_id         = None


# ── Sidebar ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding:12px 0 28px 0;'>
        <div style='font-family:Syne,sans-serif;font-size:24px;font-weight:800;
                    color:#e8e8e8;letter-spacing:-0.03em;line-height:1.05;'>
            REPO<span style='color:#ff5000;'>INSIGHT</span>
        </div>
        <div style='font-size:9px;color:#2a2a2a;margin-top:5px;
                    font-family:Space Mono,monospace;letter-spacing:0.2em;
                    text-transform:uppercase;'>
            Codebase Intelligence / v1.0
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    page = st.radio(
        "",
        ["INGEST", "QUERY"],
        format_func=lambda x: ("▸  INGEST" if x == "INGEST" else "◈  QUERY"),
        label_visibility="collapsed"
    )

    st.divider()

    if st.session_state.ingested_repo:
        st.markdown("""
        <div style='font-size:9px;color:#ff5000;letter-spacing:0.18em;
                    text-transform:uppercase;margin-bottom:8px;
                    font-family:Space Mono,monospace;'>
            ● Active Index
        </div>
        """, unsafe_allow_html=True)
        repo_short = st.session_state.ingested_repo.replace("https://github.com/","")
        st.code(repo_short, language=None)

        if st.session_state.ingested_at:
            age = (time.time() - st.session_state.ingested_at) / 3600
            if age > 24:
                st.warning(f"⚠ Index is {age:.0f}h old")
            else:
                st.markdown(f"""
                <div style='font-size:10px;color:#333;font-family:Space Mono,monospace;
                            margin-top:6px;'>
                    indexed {age:.1f}h ago
                </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='font-size:10px;color:#2a2a2a;font-family:Space Mono,monospace;'>
            ○ no index loaded
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# PAGE 1 — INGEST
# ══════════════════════════════════════════════════════════════════
if page == "INGEST":

    st.markdown("""
    <div style='padding:40px 0 36px 0;border-bottom:1px solid #111;margin-bottom:40px;'>
        <div style='font-size:9px;color:#ff5000;letter-spacing:0.22em;
                    text-transform:uppercase;font-family:Space Mono,monospace;
                    margin-bottom:14px;'>
            01 / Ingest
        </div>
        <div style='font-family:Syne,sans-serif;font-size:44px;font-weight:800;
                    color:#e8e8e8;letter-spacing:-0.035em;line-height:1;
                    margin-bottom:16px;'>
            Index a Repository
        </div>
        <div style='font-size:12px;color:#3a3a3a;font-family:Space Mono,monospace;
                    max-width:480px;line-height:1.8;'>
            Clone → parse → chunk → embed → store.<br>
            Ask questions in minutes.
        </div>
    </div>
    """, unsafe_allow_html=True)

    left, right = st.columns([3, 2], gap="large")

    with left:
        github_url = st.text_input(
            "GITHUB URL",
            placeholder="https://github.com/owner/repository",
        )
        token = st.text_input(
            "ACCESS TOKEN",
            type="password",
            placeholder="ghp_xxxxxxxx  (optional, private repos only)",
        )

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size:9px;color:#333;letter-spacing:0.18em;
                    text-transform:uppercase;font-family:Space Mono,monospace;
                    margin-bottom:14px;'>
            Index Scope
        </div>""", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            include_tests = st.checkbox("Include test files", value=False)
        with c2:
            include_examples = st.checkbox("Include examples", value=False)

        skip_tests    = not include_tests
        skip_examples = not include_examples

        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

        if st.button("START INGESTION →", type="primary", use_container_width=True):
            if not github_url.strip():
                st.error("GitHub URL required.")
            else:
                try:
                    resp = requests.post(f"{API_BASE}/ingest", json={
                        "github_url":    github_url.strip(),
                        "token":         token or None,
                        "skip_tests":    skip_tests,
                        "skip_examples": skip_examples
                    })
                    data = resp.json()
                    st.session_state.job_id        = data["job_id"]
                    st.session_state.ingested_repo = github_url.strip()
                except Exception:
                    st.error("Cannot reach API.")
                    st.code("uvicorn backend.main:app --reload", language="bash")

    with right:
        st.markdown("""
        <div style='border:1px solid #161616;padding:28px;background:#0d0d0d;
                    margin-top:28px;'>
            <div style='font-size:9px;color:#ff5000;letter-spacing:0.18em;
                        text-transform:uppercase;font-family:Space Mono,monospace;
                        margin-bottom:18px;'>
                Pipeline
            </div>
            <div style='font-family:Space Mono,monospace;font-size:11px;
                        color:#2e2e2e;line-height:2.4;'>
                <span style='color:#ff5000;margin-right:12px;'>01</span>Clone to temp dir<br>
                <span style='color:#ff5000;margin-right:12px;'>02</span>Filter non-code files<br>
                <span style='color:#ff5000;margin-right:12px;'>03</span>Parse AST boundaries<br>
                <span style='color:#ff5000;margin-right:12px;'>04</span>Chunk at function level<br>
                <span style='color:#ff5000;margin-right:12px;'>05</span>Embed via Google API<br>
                <span style='color:#ff5000;margin-right:12px;'>06</span>Store vectors in ChromaDB
            </div>
        </div>
        <div style='border:1px solid #161616;border-top:1px solid #161616;
                    padding:20px;background:#0d0d0d;margin-top:1px;'>
            <div style='font-size:9px;color:#2a2a2a;letter-spacing:0.18em;
                        text-transform:uppercase;font-family:Space Mono,monospace;
                        margin-bottom:10px;'>
                Languages
            </div>
            <div style='font-family:Space Mono,monospace;font-size:10px;color:#2e2e2e;
                        line-height:2;'>
                py · js · ts · java · go · rs · rb · cpp · cs · swift
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Progress
    if st.session_state.job_id:
        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size:9px;color:#333;letter-spacing:0.18em;
                    text-transform:uppercase;font-family:Space Mono,monospace;
                    margin-bottom:16px;'>
            Progress
        </div>""", unsafe_allow_html=True)

        job_id   = st.session_state.job_id
        s_box    = st.empty()
        p_bar    = st.empty()
        m_line   = st.empty()

        while True:
            try:
                status = requests.get(f"{API_BASE}/status/{job_id}").json()
            except:
                st.error("Lost connection to API.")
                break

            p_bar.progress(status["progress"] / 100)
            m_line.markdown(f"""
            <div style='font-family:Space Mono,monospace;font-size:10px;
                        color:#333;margin-top:8px;'>
                {status["message"]}
            </div>""", unsafe_allow_html=True)

            if status["status"] == "complete":
                result = status.get("result", {})
                st.session_state.ingested_at = result.get("ingested_at")
                st.session_state.job_id      = None
                s_box.empty(); p_bar.empty(); m_line.empty()

                st.markdown("""
                <div style='font-size:9px;color:#ff5000;letter-spacing:0.18em;
                            text-transform:uppercase;font-family:Space Mono,monospace;
                            margin:32px 0 20px 0;'>
                    ✓ Index ready
                </div>""", unsafe_allow_html=True)

                m1, m2, m3 = st.columns(3)
                m1.metric("Files",    result.get("files_found", 0))
                m2.metric("Chunks",   result.get("chunks_created", 0))
                m3.metric("Vectors",  result.get("chunks_embedded", 0))

                st.markdown("""
                <div style='margin-top:24px;font-family:Space Mono,monospace;
                            font-size:11px;color:#333;border-left:2px solid #ff5000;
                            padding-left:14px;'>
                    Switch to QUERY in the sidebar.
                </div>""", unsafe_allow_html=True)
                break

            elif status["status"] == "failed":
                s_box.error(f"Failed: {status.get('error')}")
                st.session_state.job_id = None
                break
            else:
                s_box.markdown(f"""
                <div style='font-family:Space Mono,monospace;font-size:10px;
                            color:#ff5000;letter-spacing:0.1em;'>
                    ● {status["status"].upper()}
                </div>""", unsafe_allow_html=True)
                time.sleep(3)
                st.rerun()


# ══════════════════════════════════════════════════════════════════
# PAGE 2 — QUERY
# ══════════════════════════════════════════════════════════════════
elif page == "QUERY":

    st.markdown("""
    <div style='padding:40px 0 36px 0;border-bottom:1px solid #111;margin-bottom:32px;'>
        <div style='font-size:9px;color:#ff5000;letter-spacing:0.22em;
                    text-transform:uppercase;font-family:Space Mono,monospace;
                    margin-bottom:14px;'>
            02 / Query
        </div>
        <div style='font-family:Syne,sans-serif;font-size:44px;font-weight:800;
                    color:#e8e8e8;letter-spacing:-0.035em;line-height:1;
                    margin-bottom:16px;'>
            Ask the Codebase
        </div>
        <div style='font-size:12px;color:#3a3a3a;font-family:Space Mono,monospace;
                    max-width:480px;line-height:1.8;'>
            Every answer cites its source — file, line, snippet.
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.ingested_repo:
        st.markdown("""
        <div style='border:1px solid #1a1a1a;border-left:2px solid #ff5000;
                    padding:20px;background:#0d0d0d;'>
            <div style='font-family:Space Mono,monospace;font-size:11px;color:#444;'>
                No index loaded — go to INGEST first.
            </div>
        </div>""", unsafe_allow_html=True)
        st.stop()

    # Chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.markdown(f"""
                <div style='font-family:Space Mono,monospace;font-size:13px;
                            color:#e8e8e8;line-height:1.6;'>
                    {msg["content"]}
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(msg["content"])
                if msg.get("sources"):
                    with st.expander(
                        f"  {len(msg['sources'])} sources  ·  "
                        f"conf {msg.get('confidence',0):.2f}  ·  "
                        f"{msg.get('intent','').upper()}"
                    ):
                        for i, src in enumerate(msg["sources"]):
                            st.markdown(f"""
                            <div style='font-size:9px;color:#444;
                                        font-family:Space Mono,monospace;
                                        margin:14px 0 4px 0;
                                        letter-spacing:0.1em;text-transform:uppercase;'>
                                [{i+1}]  {src['file']}  —  ln {src['line']}
                            </div>""", unsafe_allow_html=True)
                            st.code(src["snippet"], language="python")

    # Input
    question = st.chat_input("how does X work?  /  where is Y used?  /  what does Z do?")

    if question:
        st.session_state.chat_history.append({"role":"user","content":question})

        with st.chat_message("user"):
            st.markdown(f"""
            <div style='font-family:Space Mono,monospace;font-size:13px;
                        color:#e8e8e8;'>
                {question}
            </div>""", unsafe_allow_html=True)

        with st.chat_message("assistant"):
            thinking = st.markdown("""
            <div style='font-family:Space Mono,monospace;font-size:10px;
                        color:#2a2a2a;letter-spacing:0.12em;animation:pulse 1.5s infinite;'>
                ● searching index...
            </div>""", unsafe_allow_html=True)

            try:
                resp = requests.post(
                    f"{API_BASE}/query",
                    json={"github_url": st.session_state.ingested_repo, "question": question},
                    timeout=120
                )
                thinking.empty()

                if resp.status_code == 404:
                    answer = "Index not found — please re-ingest this repository."
                    sources = []; confidence = 0.0; intent = "error"
                elif resp.status_code != 200:
                    answer = f"API error {resp.status_code}: {resp.text}"
                    sources = []; confidence = 0.0; intent = "error"
                else:
                    data       = resp.json()
                    answer     = data["answer"]
                    sources    = data["sources"]
                    confidence = data["confidence"]
                    intent     = data["intent"]

            except requests.exceptions.Timeout:
                thinking.empty()
                answer = "Request timed out. Try a more specific question."
                sources = []; confidence = 0.0; intent = "error"
            except Exception as e:
                thinking.empty()
                answer = f"Cannot reach API: {e}"
                sources = []; confidence = 0.0; intent = "error"

            st.markdown(answer)

            if sources:
                with st.expander(
                    f"  {len(sources)} sources  ·  conf {confidence:.2f}  ·  {intent.upper()}"
                ):
                    for i, src in enumerate(sources):
                        st.markdown(f"""
                        <div style='font-size:9px;color:#444;
                                    font-family:Space Mono,monospace;
                                    margin:14px 0 4px 0;letter-spacing:0.1em;
                                    text-transform:uppercase;'>
                            [{i+1}]  {src['file']}  —  ln {src['line']}
                        </div>""", unsafe_allow_html=True)
                        st.code(src["snippet"], language="python")

        st.session_state.chat_history.append({
            "role":"assistant","content":answer,
            "sources":sources,"confidence":confidence,"intent":intent
        })

    if st.session_state.chat_history:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("CLEAR HISTORY", type="secondary"):
            st.session_state.chat_history = []
            st.rerun()