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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Syne:wght@400;600;700;800&display=swap');

/* ── Force dark mode regardless of browser theme ── */
:root {
    color-scheme: dark !important;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #0a0a0a !important;
    color: #e8e8e8 !important;
    font-family: 'Space Mono', monospace !important;
    color-scheme: dark !important;
}
[data-testid="stAppViewContainer"] {
    background: radial-gradient(ellipse 80% 50% at 20% 0%, rgba(255,80,0,0.06) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 100%, rgba(255,200,0,0.04) 0%, transparent 60%), #0a0a0a !important;
}
[data-testid="stSidebar"] { background: #0f0f0f !important; border-right: 1px solid #1e1e1e !important; }
[data-testid="stSidebar"] * { font-family: 'Space Mono', monospace !important; color-scheme: dark !important; }
#MainMenu, footer, header, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
h1, h2, h3 { font-family: 'Syne', sans-serif !important; letter-spacing: -0.02em; }
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
    background: #111 !important; border: 1px solid #2a2a2a !important;
    border-radius: 0 !important; color: #e8e8e8 !important;
    font-family: 'Space Mono', monospace !important; font-size: 13px !important;
    color-scheme: dark !important;
}
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
    border-color: #ff5000 !important; box-shadow: 0 0 0 1px #ff5000 !important;
}
[data-testid="stButton"] button[kind="primary"] {
    background: #ff5000 !important; color: #0a0a0a !important; border: none !important;
    border-radius: 0 !important; font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important; font-size: 13px !important; letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    background: #ff6a1f !important; box-shadow: 0 4px 20px rgba(255,80,0,0.3) !important;
}
[data-testid="stButton"] button[kind="secondary"] {
    background: transparent !important; color: #444 !important;
    border: 1px solid #222 !important; border-radius: 0 !important;
    font-family: 'Space Mono', monospace !important; font-size: 11px !important;
}
[data-testid="stButton"] button[kind="secondary"]:hover { border-color: #ff5000 !important; color: #ff5000 !important; }
[data-testid="stProgressBar"] > div > div { background: linear-gradient(90deg, #ff5000, #ffaa00) !important; border-radius: 0 !important; }
[data-testid="stProgressBar"] > div { background: #1a1a1a !important; border-radius: 0 !important; height: 2px !important; }
[data-testid="stMetric"] { background: #0d0d0d !important; border: 1px solid #1e1e1e !important; border-top: 2px solid #ff5000 !important; padding: 20px !important; border-radius: 0 !important; }
[data-testid="stMetricLabel"] { color: #444 !important; font-size: 10px !important; text-transform: uppercase !important; letter-spacing: 0.12em !important; font-family: 'Space Mono', monospace !important; }
[data-testid="stMetricValue"] { color: #e8e8e8 !important; font-family: 'Syne', sans-serif !important; font-size: 32px !important; font-weight: 700 !important; }
[data-testid="stCheckbox"] label { color: #666 !important; font-size: 12px !important; font-family: 'Space Mono', monospace !important; }
[data-testid="stAlert"] { border-radius: 0 !important; border-left: 3px solid #ff5000 !important; background: #0d0d0d !important; font-family: 'Space Mono', monospace !important; font-size: 12px !important; }
[data-testid="stCode"], [data-testid="stCodeBlock"] { border-radius: 0 !important; border: 1px solid #1a1a1a !important; background: #0d0d0d !important; }
[data-testid="stExpander"] { border: 1px solid #1a1a1a !important; border-radius: 0 !important; background: #0d0d0d !important; }
[data-testid="stExpander"] summary { font-family: 'Space Mono', monospace !important; font-size: 11px !important; color: #444 !important; }
[data-testid="stExpander"] summary:hover { color: #ff5000 !important; }
[data-testid="stChatMessage"] { background: transparent !important; border-bottom: 1px solid #0f0f0f !important; padding: 20px 0 !important; }
[data-testid="stChatMessageContent"] p { font-family: 'Space Mono', monospace !important; font-size: 13px !important; line-height: 1.9 !important; color: #bbb !important; }
[data-testid="stChatInput"] textarea { background: #111 !important; border: 1px solid #2a2a2a !important; border-radius: 0 !important; font-family: 'Space Mono', monospace !important; font-size: 13px !important; color: #e8e8e8 !important; color-scheme: dark !important; }
[data-testid="stChatInput"] textarea:focus { border-color: #ff5000 !important; }
[data-testid="stChatInput"] button { background: #ff5000 !important; border-radius: 0 !important; }
[data-testid="stRadio"] label { font-family: 'Space Mono', monospace !important; font-size: 11px !important; color: #aaa !important; letter-spacing: 0.1em !important; }
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background: #111 !important; border-color: #2a2a2a !important; color: #e8e8e8 !important; border-radius: 0 !important;
}
[data-baseweb="popover"] ul { background: #111 !important; }
[data-baseweb="popover"] li { color: #e8e8e8 !important; }
[data-baseweb="popover"] li:hover { background: #1e1e1e !important; }
hr { border-color: #1a1a1a !important; }
::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: #0a0a0a; }
::-webkit-scrollbar-thumb { background: #222; }
::-webkit-scrollbar-thumb:hover { background: #ff5000; }
div[data-baseweb="tab-list"] { background: transparent !important; border-bottom: 1px solid #1a1a1a !important; }
div[data-baseweb="tab"] { font-family: 'Space Mono', monospace !important; font-size: 11px !important; color: #444 !important; letter-spacing: 0.1em !important; background: transparent !important; }
div[data-baseweb="tab"][aria-selected="true"] { color: #ff5000 !important; border-bottom: 2px solid #ff5000 !important; }
/* Light mode override — force dark everywhere */
@media (prefers-color-scheme: light) {
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"],
    [data-testid="stSidebar"], [data-testid="stHeader"] {
        background-color: #0a0a0a !important;
        color: #e8e8e8 !important;
    }
    [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
    [data-testid="stChatInput"] textarea {
        background: #111 !important;
        color: #e8e8e8 !important;
        border-color: #2a2a2a !important;
    }
}
</style>
""", unsafe_allow_html=True)


# ── Session state ────────────────────────────────────────────────
defaults = {
    "token": None, "user_email": None,
    "page": "login", "active_repo": None,
    "repos": {}, "job_id": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Token persistence via query params ───────────────────────────
def save_token_to_url(token: str, email: str):
    st.query_params["t"] = token
    st.query_params["e"] = email


def clear_token_from_url():
    st.query_params.clear()


# ── Restore session from URL on page refresh ─────────────────────
if not st.session_state.token:
    saved_token = st.query_params.get("t")
    saved_email = st.query_params.get("e")
    if saved_token and saved_email:
        try:
            r = requests.get(
                f"{API_BASE}/auth/me",
                headers={"Authorization": f"Bearer {saved_token}"},
                timeout=5
            )
            if r.status_code == 200:
                st.session_state.token      = saved_token
                st.session_state.user_email = saved_email
                st.session_state.page       = "ingest"
            else:
                clear_token_from_url()
        except Exception:
            clear_token_from_url()


# ── Email verification from URL (?verify=token) ─────────────────
if not st.session_state.token:
    verify_token = st.query_params.get("verify")
    if verify_token:
        try:
            r = requests.get(f"{API_BASE}/auth/verify", params={"token": verify_token}, timeout=10)
            st.query_params.clear()
            if r.status_code == 200:
                d = r.json()
                st.session_state.token      = d["token"]
                st.session_state.user_email = d["email"]
                st.session_state.page       = "settings"
                save_token_to_url(d["token"], d["email"])
                st.success("✓ Email verified! Welcome to RepoInsight. Add your API keys below.")
            else:
                st.error(r.json().get("detail", "Verification failed. Try registering again."))
        except Exception as e:
            st.error(f"Could not reach server: {e}")


# ── API helper ───────────────────────────────────────────────────
def api(method, path, **kwargs):
    headers = kwargs.pop("headers", {})
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    try:
        return requests.request(method, f"{API_BASE}{path}", headers=headers, **kwargs)
    except Exception as e:
        st.error(f"Cannot reach API: {e}")
        return None


def load_repos():
    resp = api("GET", "/repos/")
    if resp and resp.status_code == 200:
        for repo in resp.json()["repos"]:
            url = repo["repo_url"]
            if url not in st.session_state.repos:
                chat_resp = api("GET", f"/repos/chat?repo_url={url}")
                chat_history = chat_resp.json()["chat_history"] if chat_resp and chat_resp.status_code == 200 else []
            else:
                chat_history = st.session_state.repos[url].get("chat_history", [])
            st.session_state.repos[url] = {
                "status": repo["status"], "chunks": repo["chunks_count"],
                "files": repo["files_count"], "vectors": repo["vectors_count"],
                "ingested_at": repo["ingested_at"], "chat_history": chat_history
            }


def save_message(repo_url, message):
    api("POST", "/repos/chat/append", json={"repo_url": repo_url, "message": message})


def get_saved_keys():
    """Return dict of saved keys for current user, or empty dict on failure."""
    resp = api("GET", "/keys/")
    if resp and resp.status_code == 200:
        existing = {}
        for k in resp.json()["keys"]:
            existing[f"{k['provider']}_{k['key_type']}"] = k.get("model_name", "")
        return existing
    return {}


# ══════════════════════════════════════════════════════════════════
# PAGE: LOGIN / REGISTER
# ══════════════════════════════════════════════════════════════════
def show_login():
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
        <div style='text-align:center;padding:60px 0 48px 0;'>
            <div style='font-family:Syne,sans-serif;font-size:52px;font-weight:800;
                        color:#e8e8e8;letter-spacing:-0.04em;line-height:1;'>
                REPO<span style='color:#ff5000;'>INSIGHT</span>
            </div>
            <div style='font-size:10px;color:#333;letter-spacing:0.25em;
                        text-transform:uppercase;font-family:Space Mono,monospace;margin-top:8px;'>
                Codebase Intelligence
            </div>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["LOGIN", "REGISTER"])

        with tab1:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            email    = st.text_input("EMAIL", placeholder="you@example.com", key="login_email")
            password = st.text_input("PASSWORD", type="password", placeholder="••••••••", key="login_pass")
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button("LOGIN →", type="primary", use_container_width=True, key="do_login"):
                if email and password:
                    r = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password})
                    if r.status_code == 200:
                        d = r.json()
                        st.session_state.token      = d["token"]
                        st.session_state.user_email = d["email"]
                        save_token_to_url(d["token"], d["email"])
                        load_repos()
                        # Check if user has keys saved — if not, send to settings first
                        keys = get_saved_keys()
                        has_embedding = any("embedding" in k for k in keys)
                        has_llm       = any("llm" in k for k in keys)
                        if has_embedding and has_llm:
                            st.session_state.page = "ingest"
                        else:
                            st.session_state.page = "settings"
                        st.rerun()
                    elif r.status_code == 403 and r.json().get("detail") == "EMAIL_NOT_VERIFIED":
                        st.markdown("""
                        <div style='border:1px solid #2a1a00;border-left:3px solid #ff5000;
                                    background:#110900;padding:16px 20px;margin-top:8px;'>
                            <div style='font-size:11px;color:#ff5000;font-family:Space Mono,monospace;
                                        font-weight:700;margin-bottom:6px;'>✉ Email not verified</div>
                            <div style='font-size:11px;color:#888;font-family:Space Mono,monospace;
                                        line-height:1.9;'>
                                Check your inbox for the verification link.<br>
                                Didn't get it? Enter your details and click Resend.
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button("Resend verification email", type="secondary", use_container_width=True, key="resend_btn"):
                            resend = requests.post(
                                f"{API_BASE}/auth/resend-verification",
                                json={"email": email, "password": password}
                            )
                            if resend.status_code == 200:
                                st.success("Verification email resent. Check your inbox.")
                            else:
                                st.error(resend.json().get("detail", "Could not resend"))
                    else:
                        st.error(r.json().get("detail", "Login failed"))
                else:
                    st.error("Email and password required")

        with tab2:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            # ── Show inbox prompt after successful registration ───────
            if st.session_state.get("pending_verify_email"):
                pv_email = st.session_state["pending_verify_email"]
                st.markdown(f"""
                <div style='border:1px solid #0a2a00;border-left:3px solid #00cc44;
                            background:#050f00;padding:20px 24px;margin-bottom:16px;'>
                    <div style='font-size:11px;color:#00cc44;font-family:Space Mono,monospace;
                                font-weight:700;letter-spacing:0.08em;text-transform:uppercase;
                                margin-bottom:8px;'>✓ Check your inbox</div>
                    <div style='font-size:11px;color:#888;font-family:Space Mono,monospace;
                                line-height:1.9;'>
                        A verification link was sent to<br>
                        <span style='color:#e8e8e8;'>{pv_email}</span><br><br>
                        Click the link to activate your account,<br>
                        then log in using the LOGIN tab.
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("← Use a different email", type="secondary", use_container_width=True):
                    del st.session_state["pending_verify_email"]
                    st.rerun()
                st.stop()

            reg_email = st.text_input("EMAIL", placeholder="you@example.com", key="reg_email")
            reg_pass  = st.text_input("PASSWORD", type="password", placeholder="min 8 characters", key="reg_pass")
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button("CREATE ACCOUNT →", type="primary", use_container_width=True, key="do_reg"):
                if reg_email and reg_pass:
                    r = requests.post(f"{API_BASE}/auth/register", json={"email": reg_email, "password": reg_pass})
                    if r.status_code in (200, 201):
                        # Don't log in yet — show "check your inbox" message
                        st.session_state["pending_verify_email"] = reg_email
                        st.rerun()
                    else:
                        st.error(r.json().get("detail", "Registration failed"))
                else:
                    st.error("Email and password required")


# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
def show_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style='padding:12px 0 20px 0;'>
            <div style='font-family:Syne,sans-serif;font-size:22px;font-weight:800;
                        color:#e8e8e8;letter-spacing:-0.03em;'>
                REPO<span style='color:#ff5000;'>INSIGHT</span>
            </div>
            <div style='font-size:9px;color:#2a2a2a;margin-top:5px;
                        font-family:Space Mono,monospace;letter-spacing:0.2em;text-transform:uppercase;'>
                Codebase Intelligence / v1.0
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style='font-size:10px;color:#444;font-family:Space Mono,monospace;
                    padding:8px 10px;background:#111;border-left:2px solid #ff5000;margin-bottom:12px;'>
            {st.session_state.user_email}
        </div>
        """, unsafe_allow_html=True)

        page = st.radio("", ["INGEST", "QUERY", "SETTINGS"],
                        format_func=lambda x: {"INGEST":"▸  INGEST","QUERY":"◈  QUERY","SETTINGS":"⚙  SETTINGS"}[x],
                        label_visibility="collapsed", key="nav_radio")
        st.session_state.page = page.lower()

        st.divider()

        if st.session_state.repos:
            st.markdown("""
            <div style='font-size:9px;color:#555;letter-spacing:0.18em;text-transform:uppercase;
                        font-family:Space Mono,monospace;margin-bottom:10px;'>
                Indexed Repos
            </div>""", unsafe_allow_html=True)

            for repo_url in list(st.session_state.repos.keys()):
                short     = repo_url.replace("https://github.com/", "")
                is_active = (st.session_state.active_repo == repo_url)
                label     = f"{'● ' if is_active else '○ '}{short[:26]}{'…' if len(short)>26 else ''}"
                if st.button(label, key=f"repo_{repo_url}", type="secondary", use_container_width=True):
                    st.session_state.active_repo = repo_url
                    chat_resp = api("GET", f"/repos/chat?repo_url={repo_url}")
                    if chat_resp and chat_resp.status_code == 200:
                        st.session_state.repos[repo_url]["chat_history"] = chat_resp.json()["chat_history"]
                    st.session_state.page = "query"
                    st.rerun()
        else:
            st.markdown("""
            <div style='font-size:10px;color:#2a2a2a;font-family:Space Mono,monospace;'>
                ○ no repos indexed yet
            </div>""", unsafe_allow_html=True)

        st.divider()
        if st.button("LOGOUT", type="secondary", use_container_width=True):
            clear_token_from_url()
            for k, v in defaults.items():
                st.session_state[k] = v
            st.rerun()


# ══════════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ══════════════════════════════════════════════════════════════════
def show_settings():
    st.markdown("""
    <div style='padding:40px 0 36px 0;border-bottom:1px solid #111;margin-bottom:40px;'>
        <div style='font-size:9px;color:#ff5000;letter-spacing:0.22em;text-transform:uppercase;
                    font-family:Space Mono,monospace;margin-bottom:14px;'>⚙ / Settings</div>
        <div style='font-family:Syne,sans-serif;font-size:44px;font-weight:800;
                    color:#e8e8e8;letter-spacing:-0.035em;line-height:1;margin-bottom:16px;'>
            API Keys</div>
        <div style='font-size:12px;color:#666;font-family:Space Mono,monospace;max-width:520px;line-height:1.8;'>
            Keys are AES-256 encrypted before storage.<br>Never logged or exposed in any response.</div>
    </div>
    """, unsafe_allow_html=True)

    resp = api("GET", "/keys/")
    existing = {}
    if resp and resp.status_code == 200:
        for k in resp.json()["keys"]:
            existing[f"{k['provider']}_{k['key_type']}"] = k.get("model_name", "")

    has_embedding = any("embedding" in k for k in existing)
    has_llm       = any("llm" in k for k in existing)

    # ── Setup banner for new users ───────────────────────────────
    if not has_embedding or not has_llm:
        missing = []
        if not has_embedding: missing.append("embedding")
        if not has_llm:       missing.append("LLM")
        st.markdown(f"""
        <div style='border:1px solid #2a1a00;border-left:3px solid #ff5000;background:#110900;
                    padding:20px 24px;margin-bottom:32px;'>
            <div style='font-size:11px;color:#ff5000;font-family:Syne,sans-serif;font-weight:700;
                        letter-spacing:0.08em;text-transform:uppercase;margin-bottom:10px;'>
                ⚠ Setup required — missing: {" + ".join(missing)} key{"s" if len(missing)>1 else ""}
            </div>
            <div style='font-size:11px;color:#888;font-family:Space Mono,monospace;line-height:1.9;'>
                You need both an <span style='color:#e8e8e8;'>embedding key</span> and an
                <span style='color:#e8e8e8;'>LLM key</span> before you can index or query a repo.<br>
                Save both below, then head to <span style='color:#ff5000;'>▸ INGEST</span> in the sidebar.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Free key guide ───────────────────────────────────────────
    with st.expander("🆓  Get free API keys — no credit card needed"):
        st.markdown("""
        <div style='font-family:Space Mono,monospace;font-size:11px;color:#888;line-height:2.2;padding:4px 0;'>

        <div style='color:#ff5000;font-size:9px;letter-spacing:0.18em;text-transform:uppercase;
                    margin-bottom:10px;'>Embedding key (Google — free tier)</div>
        <div style='color:#aaa;margin-bottom:4px;'>
            1. Go to <span style='color:#ff5000;'>aistudio.google.com/app/apikey</span><br>
            2. Sign in with your Google account<br>
            3. Click <span style='color:#e8e8e8;'>Create API Key</span><br>
            4. Copy the key and paste it below under <span style='color:#e8e8e8;'>Embedding Provider → Google</span><br>
            <span style='color:#555;'>Free tier: 1,500 requests/day · no credit card required</span>
        </div>

        <div style='border-top:1px solid #1a1a1a;margin:16px 0;'></div>

        <div style='color:#ff5000;font-size:9px;letter-spacing:0.18em;text-transform:uppercase;
                    margin-bottom:10px;'>LLM key — pick one (both free)</div>

        <div style='color:#e8e8e8;margin-bottom:2px;'>Option A — Groq (fastest, recommended)</div>
        <div style='color:#aaa;margin-bottom:12px;'>
            1. Go to <span style='color:#ff5000;'>console.groq.com</span><br>
            2. Sign up → Dashboard → API Keys → Create API Key<br>
            3. Paste below under <span style='color:#e8e8e8;'>LLM Provider → Groq</span><br>
            <span style='color:#555;'>Free tier: 30 req/min on Llama 3.3 70B · no credit card</span>
        </div>

        <div style='color:#e8e8e8;margin-bottom:2px;'>Option B — OpenRouter (more model choices)</div>
        <div style='color:#aaa;'>
            1. Go to <span style='color:#ff5000;'>openrouter.ai</span> → Sign up<br>
            2. Keys → Create Key<br>
            3. Paste below under <span style='color:#e8e8e8;'>LLM Provider → OpenRouter</span><br>
            4. Use model <span style='color:#e8e8e8;'>google/gemini-2.5-flash:free</span> (already in the dropdown)<br>
            <span style='color:#555;'>Free models available · no credit card required for free tier</span>
        </div>

        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    left, right = st.columns(2, gap="large")

    with left:
        st.markdown('<div style="font-size:9px;color:#ff5000;letter-spacing:0.18em;text-transform:uppercase;font-family:Space Mono,monospace;margin-bottom:16px;">Embedding Provider</div>', unsafe_allow_html=True)
        ep = st.selectbox("EP", ["google", "openai"],
            format_func=lambda x: {"google": "Google (free tier)", "openai": "OpenAI (paid)"}[x],
            label_visibility="collapsed", key="ep")

        em_models = {
            "google": ["models/gemini-embedding-001", "models/gemini-embedding-2", "Enter a model name"],
            "openai": ["text-embedding-3-small", "text-embedding-3-large", "Enter a model name"]
        }
        em_selected = st.selectbox("EM", em_models[ep], label_visibility="collapsed", key="em")

        if em_selected == "Enter a model name":
            em = st.text_input(
                "Custom embedding model name",
                placeholder="e.g. models/gemini-embedding-3",
                key="em_custom"
            )
            st.markdown("""
            <div style='font-size:10px;color:#444;font-family:Space Mono,monospace;margin-top:4px;'>
                Check provider docs for available embedding models
            </div>""", unsafe_allow_html=True)
        else:
            em = em_selected

        ex_em = existing.get(f"{ep}_embedding")
        if ex_em:
            st.markdown(f'<div style="font-size:10px;color:#ff5000;font-family:Space Mono,monospace;margin-bottom:8px;">✓ Key saved — {ex_em}</div>', unsafe_allow_html=True)

        ek = st.text_input("Embedding API Key", type="password", placeholder="Paste key here", key="ek")

        if st.button("SAVE EMBEDDING KEY →", type="primary", use_container_width=True, key="save_ek"):
            if not ek:
                st.error("Paste your key first")
            elif not em:
                st.error("Enter a model name")
            else:
                r = api("POST", "/keys/", json={"provider": ep, "key_type": "embedding", "api_key": ek, "model_name": em})
                if r and r.status_code == 201:
                    st.success(f"✓ {ep} embedding key saved"); st.rerun()
                else:
                    st.error(r.json().get("detail") if r else "Failed")

    with right:
        st.markdown('<div style="font-size:9px;color:#ff5000;letter-spacing:0.18em;text-transform:uppercase;font-family:Space Mono,monospace;margin-bottom:16px;">LLM Provider</div>', unsafe_allow_html=True)
        lp = st.selectbox("LP", ["openrouter", "groq", "openai", "anthropic"],
            format_func=lambda x: {"openrouter": "OpenRouter (free models)", "groq": "Groq (free, fast)", "openai": "OpenAI (paid)", "anthropic": "Anthropic (paid)"}[x],
            label_visibility="collapsed", key="lp")

        lm_models = {
            "openrouter": ["google/gemini-2.5-flash:free", "meta-llama/llama-3.3-70b-instruct:free", "Enter a model name"],
            "groq":       ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "Enter a model name"],
            "openai":     ["gpt-4o-mini", "gpt-4o", "Enter a model name"],
            "anthropic":  ["claude-haiku-4-5", "claude-sonnet-4-5", "Enter a model name"]
        }
        lm_selected = st.selectbox("LM", lm_models[lp], label_visibility="collapsed", key="lm")

        if lm_selected == "Enter a model name":
            lm = st.text_input(
                "Custom model name",
                placeholder="e.g. anthropic/claude-opus-4",
                key="lm_custom"
            )
            st.markdown("""
            <div style='font-size:10px;color:#444;font-family:Space Mono,monospace;margin-top:4px;'>
                Browse models at openrouter.ai/models
            </div>""", unsafe_allow_html=True)
        else:
            lm = lm_selected

        ex_lm = existing.get(f"{lp}_llm")
        if ex_lm:
            st.markdown(f'<div style="font-size:10px;color:#ff5000;font-family:Space Mono,monospace;margin-bottom:8px;">✓ Key saved — {ex_lm}</div>', unsafe_allow_html=True)

        lk = st.text_input("LLM API Key", type="password", placeholder="Paste key here", key="lk")

        if st.button("SAVE LLM KEY →", type="primary", use_container_width=True, key="save_lk"):
            if not lk:
                st.error("Paste your key first")
            elif not lm:
                st.error("Enter a model name")
            else:
                r = api("POST", "/keys/", json={"provider": lp, "key_type": "llm", "api_key": lk, "model_name": lm})
                if r and r.status_code == 201:
                    st.success(f"✓ {lp} LLM key saved"); st.rerun()
                else:
                    st.error(r.json().get("detail") if r else "Failed")

    if existing:
        st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:9px;color:#555;letter-spacing:0.18em;text-transform:uppercase;font-family:Space Mono,monospace;margin-bottom:16px;">Saved Keys</div>', unsafe_allow_html=True)
        cols = st.columns(len(existing))
        for i, (key_id, model) in enumerate(existing.items()):
            provider, key_type = key_id.rsplit("_", 1)
            with cols[i]:
                st.markdown(f"""
                <div style='border:1px solid #1e1e1e;border-top:2px solid #ff5000;padding:16px;background:#0d0d0d;'>
                    <div style='font-size:9px;color:#ff5000;letter-spacing:0.15em;text-transform:uppercase;font-family:Space Mono,monospace;'>{provider}</div>
                    <div style='font-size:10px;color:#666;margin-top:4px;font-family:Space Mono,monospace;'>{key_type} / {model or 'default'}</div>
                </div>""", unsafe_allow_html=True)

        # Show "ready" callout once both keys are saved
        if has_embedding and has_llm:
            st.markdown("""
            <div style='border:1px solid #0a2a00;border-left:3px solid #00cc44;background:#050f00;
                        padding:16px 20px;margin-top:24px;'>
                <div style='font-size:11px;color:#00cc44;font-family:Space Mono,monospace;'>
                    ✓ Both keys saved — you're ready to ingest a repo.<br>
                    <span style='color:#555;'>Head to <span style='color:#e8e8e8;'>▸ INGEST</span> in the sidebar.</span>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# PAGE: INGEST
# ══════════════════════════════════════════════════════════════════
def show_ingest():
    st.markdown("""
    <div style='padding:40px 0 36px 0;border-bottom:1px solid #111;margin-bottom:40px;'>
        <div style='font-size:9px;color:#ff5000;letter-spacing:0.22em;text-transform:uppercase;font-family:Space Mono,monospace;margin-bottom:14px;'>01 / Ingest</div>
        <div style='font-family:Syne,sans-serif;font-size:44px;font-weight:800;color:#e8e8e8;letter-spacing:-0.035em;line-height:1;margin-bottom:16px;'>Index a Repository</div>
        <div style='font-size:12px;color:#666;font-family:Space Mono,monospace;max-width:480px;line-height:1.8;'>Clone → parse → chunk → embed → store.<br>Ask questions in minutes.</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Missing keys warning banner ──────────────────────────────
    existing     = get_saved_keys()
    has_embedding = any("embedding" in k for k in existing)
    has_llm       = any("llm" in k for k in existing)

    if not has_embedding or not has_llm:
        missing = []
        if not has_embedding: missing.append("embedding")
        if not has_llm:       missing.append("LLM")
        st.markdown(f"""
        <div style='border:1px solid #2a1a00;border-left:3px solid #ff5000;background:#110900;
                    padding:20px 24px;margin-bottom:32px;'>
            <div style='font-size:11px;color:#ff5000;font-family:Syne,sans-serif;font-weight:700;
                        letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px;'>
                ⚠ API keys required before ingestion
            </div>
            <div style='font-size:11px;color:#888;font-family:Space Mono,monospace;line-height:1.9;'>
                Missing: <span style='color:#e8e8e8;'>{" + ".join(missing)} key{"s" if len(missing)>1 else ""}</span><br>
                Go to <span style='color:#ff5000;'>⚙ SETTINGS</span> in the sidebar to add your API keys.<br>
                <span style='color:#555;'>Need free keys? The Settings page has step-by-step instructions.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    left, right = st.columns([3, 2], gap="large")

    with left:
        github_url = st.text_input("GITHUB URL", placeholder="https://github.com/owner/repository")
        token      = st.text_input("ACCESS TOKEN", type="password", placeholder="ghp_xxxxxxxx  (optional)")
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:9px;color:#666;letter-spacing:0.18em;text-transform:uppercase;font-family:Space Mono,monospace;margin-bottom:14px;">Index Scope</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: include_tests    = st.checkbox("Include test files", value=False)
        with c2: include_examples = st.checkbox("Include examples",   value=False)
        skip_tests    = not include_tests
        skip_examples = not include_examples
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

        if st.button("START INGESTION →", type="primary", use_container_width=True):
            if not github_url.strip():
                st.error("GitHub URL required.")
            elif not has_embedding or not has_llm:
                # Proactive client-side check before even calling the API
                missing = []
                if not has_embedding: missing.append("embedding")
                if not has_llm:       missing.append("LLM")
                st.error(f"Cannot ingest — missing {' and '.join(missing)} API key{'s' if len(missing)>1 else ''}.")
                st.info("Go to ⚙ SETTINGS in the sidebar to add your keys. Free options are available.")
            else:
                resp = api("POST", "/ingest", json={
                    "github_url": github_url.strip(), "token": token or None,
                    "skip_tests": skip_tests, "skip_examples": skip_examples
                })
                if resp and resp.status_code == 200:
                    data = resp.json()
                    st.session_state.job_id      = data["job_id"]
                    st.session_state.active_repo = github_url.strip()
                    if github_url.strip() not in st.session_state.repos:
                        st.session_state.repos[github_url.strip()] = {
                            "status":"running","chunks":0,"files":0,
                            "vectors":0,"ingested_at":None,"chat_history":[]
                        }
                elif resp and resp.status_code == 400:
                    detail = resp.json().get("detail", "Error")
                    st.error(detail)
                    if "key" in detail.lower() or "embedding" in detail.lower():
                        st.info("Go to ⚙ SETTINGS in the sidebar to save your API keys. Free options are available — check the Settings page for a step-by-step guide.")

    with right:
        st.markdown("""
        <div style='border:1px solid #161616;padding:28px;background:#0d0d0d;margin-top:28px;'>
            <div style='font-size:9px;color:#ff5000;letter-spacing:0.18em;text-transform:uppercase;font-family:Space Mono,monospace;margin-bottom:18px;'>Pipeline</div>
            <div style='font-family:Space Mono,monospace;font-size:11px;color:#555;line-height:2.4;'>
                <span style='color:#ff5000;margin-right:12px;'>01</span>Clone to temp dir<br>
                <span style='color:#ff5000;margin-right:12px;'>02</span>Filter non-code files<br>
                <span style='color:#ff5000;margin-right:12px;'>03</span>Parse AST boundaries<br>
                <span style='color:#ff5000;margin-right:12px;'>04</span>Chunk at function level<br>
                <span style='color:#ff5000;margin-right:12px;'>05</span>Embed via your API key<br>
                <span style='color:#ff5000;margin-right:12px;'>06</span>Store vectors in ChromaDB
            </div>
        </div>
        <div style='border:1px solid #161616;padding:20px;background:#0d0d0d;margin-top:1px;'>
            <div style='font-size:9px;color:#555;letter-spacing:0.18em;text-transform:uppercase;font-family:Space Mono,monospace;margin-bottom:10px;'>Languages</div>
            <div style='font-family:Space Mono,monospace;font-size:10px;color:#555;line-height:2;'>py · js · ts · java · go · rs · rb · cpp · cs · swift</div>
        </div>
        """, unsafe_allow_html=True)

    if st.session_state.job_id:
        st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:9px;color:#333;letter-spacing:0.18em;text-transform:uppercase;font-family:Space Mono,monospace;margin-bottom:16px;">Progress</div>', unsafe_allow_html=True)
        job_id = st.session_state.job_id
        s_box = st.empty(); p_bar = st.empty(); m_line = st.empty()

        while True:
            try:
                resp   = requests.get(f"{API_BASE}/status/{job_id}")
                status = resp.json()
                if resp.status_code == 404:
                    st.error(f"Error: {status.get('detail')} — The server likely restarted and lost the job memory.")
                    st.session_state.job_id = None
                    break
            except:
                st.error("Lost connection to API."); break

            progress = status.get("progress", 0)
            message  = status.get("message", "")
            state    = status.get("status", "unknown")

            p_bar.progress(progress / 100)
            m_line.markdown(f'<div style="font-family:Space Mono,monospace;font-size:10px;color:#333;margin-top:8px;">{message}</div>', unsafe_allow_html=True)

            if state == "complete":
                result   = status.get("result", {})
                repo_url = st.session_state.active_repo
                st.session_state.job_id = None
                if repo_url:
                    st.session_state.repos[repo_url].update({
                        "status":"complete","chunks":result.get("chunks_created",0),
                        "files":result.get("files_found",0),"vectors":result.get("chunks_embedded",0),
                        "ingested_at":result.get("ingested_at")
                    })
                s_box.empty(); p_bar.empty(); m_line.empty()
                st.markdown('<div style="font-size:9px;color:#ff5000;letter-spacing:0.18em;text-transform:uppercase;font-family:Space Mono,monospace;margin:32px 0 20px 0;">✓ Index ready</div>', unsafe_allow_html=True)
                m1,m2,m3 = st.columns(3)
                m1.metric("Files",   result.get("files_found",0))
                m2.metric("Chunks",  result.get("chunks_created",0))
                m3.metric("Vectors", result.get("chunks_embedded",0))
                st.markdown('<div style="margin-top:24px;font-family:Space Mono,monospace;font-size:11px;color:#333;border-left:2px solid #ff5000;padding-left:14px;">Switch to QUERY in the sidebar.</div>', unsafe_allow_html=True)
                break
            elif state == "failed":
                error_msg = status.get("error", "Unknown error")
                s_box.error(f"Failed: {error_msg}")
                if "key" in error_msg.lower() or "embedding" in error_msg.lower() or "api" in error_msg.lower():
                    st.info("This looks like an API key issue. Go to ⚙ SETTINGS to verify your keys are correct.")
                st.session_state.job_id = None
                break
            else:
                s_box.markdown(f'<div style="font-family:Space Mono,monospace;font-size:10px;color:#ff5000;">● {state.upper()}</div>', unsafe_allow_html=True)
                time.sleep(3); st.rerun()


# ══════════════════════════════════════════════════════════════════
# PAGE: QUERY
# ══════════════════════════════════════════════════════════════════
def show_query():
    st.markdown("""
    <div style='padding:40px 0 36px 0;border-bottom:1px solid #111;margin-bottom:32px;'>
        <div style='font-size:9px;color:#ff5000;letter-spacing:0.22em;text-transform:uppercase;font-family:Space Mono,monospace;margin-bottom:14px;'>02 / Query</div>
        <div style='font-family:Syne,sans-serif;font-size:44px;font-weight:800;color:#e8e8e8;letter-spacing:-0.035em;line-height:1;margin-bottom:16px;'>Ask the Codebase</div>
        <div style='font-size:12px;color:#666;font-family:Space Mono,monospace;max-width:480px;line-height:1.8;'>Every answer cites its source — file, line, snippet.</div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.active_repo:
        st.markdown('<div style="border:1px solid #1a1a1a;border-left:2px solid #ff5000;padding:20px;background:#0d0d0d;"><div style="font-family:Space Mono,monospace;font-size:11px;color:#444;">Select a repo from the sidebar or go to INGEST first.</div></div>', unsafe_allow_html=True)
        st.stop()

    repo_url     = st.session_state.active_repo
    repo_data    = st.session_state.repos.get(repo_url, {})
    chat_history = repo_data.get("chat_history", [])
    short        = repo_url.replace("https://github.com/", "")

    st.markdown(f'<div style="font-family:Space Mono,monospace;font-size:10px;color:#444;border-left:2px solid #ff5000;padding:8px 14px;background:#0d0d0d;margin-bottom:24px;">● {short}</div>', unsafe_allow_html=True)

    for msg in chat_history:
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.markdown(f'<div style="font-family:Space Mono,monospace;font-size:13px;color:#e8e8e8;">{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(msg["content"])
                if msg.get("sources"):
                    with st.expander(f"  {len(msg['sources'])} sources  ·  conf {msg.get('confidence',0):.2f}  ·  {msg.get('intent','').upper()}"):
                        for i, src in enumerate(msg["sources"]):
                            st.markdown(f'<div style="font-size:9px;color:#444;font-family:Space Mono,monospace;margin:14px 0 4px 0;letter-spacing:0.1em;text-transform:uppercase;">[{i+1}]  {src["file"]}  —  ln {src["line"]}</div>', unsafe_allow_html=True)
                            st.code(src["snippet"], language="python")

    question = st.chat_input("how does X work?  /  where is Y used?  /  what does Z do?")

    if question:
        user_msg = {"role":"user","content":question}
        chat_history.append(user_msg)
        st.session_state.repos[repo_url]["chat_history"] = chat_history
        save_message(repo_url, user_msg)

        with st.chat_message("user"):
            st.markdown(f'<div style="font-family:Space Mono,monospace;font-size:13px;color:#e8e8e8;">{question}</div>', unsafe_allow_html=True)

        with st.chat_message("assistant"):
            thinking = st.markdown('<div style="font-family:Space Mono,monospace;font-size:10px;color:#2a2a2a;letter-spacing:0.12em;">● searching index...</div>', unsafe_allow_html=True)
            try:
                resp = api("POST", "/query", json={"github_url":repo_url,"question":question}, timeout=120)
                thinking.empty()
                if resp is None:
                    answer="Cannot reach API.";sources=[];confidence=0.0;intent="error"
                elif resp.status_code == 404:
                    answer="Index not found — please re-ingest.";sources=[];confidence=0.0;intent="error"
                elif resp.status_code == 400:
                    answer=resp.json().get("detail","Error");sources=[];confidence=0.0;intent="error"
                elif resp.status_code != 200:
                    answer=f"API error {resp.status_code}";sources=[];confidence=0.0;intent="error"
                else:
                    d=resp.json();answer=d["answer"];sources=d["sources"];confidence=d["confidence"];intent=d["intent"]
            except requests.exceptions.Timeout:
                thinking.empty();answer="Request timed out.";sources=[];confidence=0.0;intent="error"
            except Exception as e:
                thinking.empty();answer=f"Error: {e}";sources=[];confidence=0.0;intent="error"

            st.markdown(answer)
            if sources:
                with st.expander(f"  {len(sources)} sources  ·  conf {confidence:.2f}  ·  {intent.upper()}"):
                    for i,src in enumerate(sources):
                        st.markdown(f'<div style="font-size:9px;color:#444;font-family:Space Mono,monospace;margin:14px 0 4px 0;letter-spacing:0.1em;text-transform:uppercase;">[{i+1}]  {src["file"]}  —  ln {src["line"]}</div>', unsafe_allow_html=True)
                        st.code(src["snippet"],language="python")

        assistant_msg = {"role":"assistant","content":answer,"sources":sources,"confidence":confidence,"intent":intent}
        chat_history.append(assistant_msg)
        st.session_state.repos[repo_url]["chat_history"] = chat_history
        save_message(repo_url, assistant_msg)

    if chat_history:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("CLEAR HISTORY", type="secondary"):
            api("POST", "/repos/chat/clear", json={"repo_url":repo_url})
            st.session_state.repos[repo_url]["chat_history"] = []
            st.rerun()


# ── Router ───────────────────────────────────────────────────────
if not st.session_state.token:
    show_login()
else:
    if st.session_state.token and not st.session_state.repos:
        load_repos()
    show_sidebar()
    page = st.session_state.page
    if page == "ingest":     show_ingest()
    elif page == "query":    show_query()
    elif page == "settings": show_settings()