import os
import re
import json
import uuid
import html
import time
import concurrent.futures
from datetime import datetime
from urllib.parse import quote_plus, urlparse, parse_qs, unquote

import requests
import streamlit as st

from auth_db import (
    init_db,
    register_user,
    authenticate_user,
    load_user_conversations,
    save_user_conversation,
    delete_user_conversation,
    get_all_users_for_admin,
    toggle_user_block,
    change_user_password,
    get_db_connection,
)


# ============================================================
# CONFIGURATION
# ============================================================

APP_NAME = "Hallucination Detector"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Free answer models. The app automatically falls through the list
# when a provider returns 429/404/5xx or another model error.
ANSWER_MODELS = [
    # Proven fast instruct/chat models currently active on OpenRouter:free
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "qwen/qwen3.8-27b:free",
    "poolside/laguna-s-2.1:free",
]

# Dynamic free router for independent verification.
VERIFIER_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
    "qwen/qwen3.8-27b:free",
    "openrouter/free",
]

# Used only when the live OpenRouter catalog can't be fetched.
FALLBACK_ANSWER_MODELS = list(ANSWER_MODELS)
FALLBACK_VERIFIER_MODELS = list(VERIFIER_MODELS)
MODEL_LIST_TTL_SECONDS = 1800

MAX_HISTORY_MESSAGES = 30
MAX_SOURCES = 12
MAX_SOURCE_CONTENT = 5000
MAX_TOTAL_EVIDENCE_CHARS = 18000
SEARCH_TIMEOUT = 8
OPENROUTER_TIMEOUT = 20

PAGE_TITLE = "Hallucination Detector — Web-Grounded AI"
PAGE_DESC = "Ask questions, get web-grounded answers, and independently verify AI-generated claims."
PRODUCTION_DOMAIN = "https://hallucinationdetector.com"

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# PRODUCTION DARK UI (ChatGPT / Claude Style)
# ============================================================

CLAUDE_CUSTOM_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {
font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
-webkit-font-smoothing: antialiased;
}

/* Claude Warm Obsidian Palette */
.stApp {
background-color: #1F1E1D !important;
color: #EDEBE8 !important;
}

/* Hide Streamlit default header decoration */
header[data-testid="stHeader"] {
background-color: transparent !important;
}

/* Sidebar Warm Graphite Panel */
[data-testid="stSidebar"] {
background-color: #171716 !important;
border-right: 1px solid rgba(255, 255, 255, 0.07) !important;
}

[data-testid="stSidebar"] * {
color: #C2BFB6;
}

/* Claude Centered Empty State Hero */
.claude-hero-container {
text-align: center;
max-width: 720px;
margin: 2.8rem auto 1.8rem auto;
padding: 0 1rem;
}

.claude-hero-icon {
width: 48px;
height: 48px;
margin: 0 auto 1.2rem auto;
background: rgba(218, 119, 86, 0.12);
border: 1px solid rgba(218, 119, 86, 0.35);
border-radius: 14px;
display: flex;
align-items: center;
justify-content: center;
font-size: 1.5rem;
color: #DA7756;
box-shadow: 0 4px 20px rgba(218, 119, 86, 0.15);
}

.claude-hero-title {
font-size: 2.2rem;
font-weight: 700;
color: #FAF9F5;
letter-spacing: -0.025em;
margin: 0 0 0.6rem 0;
line-height: 1.25;
}

.claude-hero-subtitle {
color: #A3A199;
font-size: 1.05rem;
font-weight: 400;
line-height: 1.55;
margin: 0 auto;
max-width: 580px;
}

.claude-hero-pill {
display: inline-flex;
align-items: center;
gap: 0.45rem;
padding: 0.25rem 0.75rem;
background: rgba(34, 197, 94, 0.12);
border: 1px solid rgba(34, 197, 94, 0.3);
border-radius: 9999px;
font-size: 0.72rem;
font-weight: 700;
color: #4ADE80;
text-transform: uppercase;
letter-spacing: 0.04em;
margin-top: 1rem;
}

.claude-pulse {
width: 6px;
height: 6px;
background: #22C55E;
border-radius: 50%;
box-shadow: 0 0 8px #22C55E;
}

/* Prompt Starter Cards (Claude Style) */
div[data-testid="column"] button {
border-radius: 14px !important;
border: 1px solid rgba(255, 255, 255, 0.08) !important;
background: #262522 !important;
color: #EDEBE8 !important;
font-weight: 500 !important;
font-size: 0.88rem !important;
text-align: left !important;
padding: 0.9rem 1.1rem !important;
transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
}

div[data-testid="column"] button:hover {
border-color: rgba(218, 119, 86, 0.5) !important;
background: #2D2C28 !important;
color: #FAF9F5 !important;
transform: translateY(-1px) !important;
box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35) !important;
}

/* Claude Primary Action Button */
div.stButton > button[kind="primary"], div.stButton > button[type="primary"] {
background: #DA7756 !important;
color: #FFFFFF !important;
border: none !important;
font-weight: 600 !important;
border-radius: 10px !important;
padding: 0.55rem 1rem !important;
box-shadow: 0 2px 10px rgba(218, 119, 86, 0.25) !important;
}

div.stButton > button[kind="primary"]:hover, div.stButton > button[type="primary"]:hover {
background: #E58B66 !important;
box-shadow: 0 4px 15px rgba(218, 119, 86, 0.4) !important;
}

/* General Secondary Buttons */
div.stButton > button {
border-radius: 10px !important;
border: 1px solid rgba(255, 255, 255, 0.08) !important;
background: #262522 !important;
color: #C2BFB6 !important;
font-weight: 500 !important;
font-size: 0.85rem !important;
transition: all 0.15s ease !important;
}

div.stButton > button:hover {
border-color: rgba(218, 119, 86, 0.3) !important;
background: #2D2C28 !important;
color: #FAF9F5 !important;
}

/* Chat Input Claude Styling */
[data-testid="stChatInput"] {
border-radius: 16px !important;
background: #262523 !important;
border: 1px solid rgba(255, 255, 255, 0.12) !important;
box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35) !important;
}

[data-testid="stChatInput"]:focus-within {
border-color: #DA7756 !important;
box-shadow: 0 0 0 1px #DA7756, 0 4px 24px rgba(218, 119, 86, 0.15) !important;
}

/* User Message Bubble on the RIGHT (like ChatGPT / Claude / attached screenshot) */
.user-msg-row {
display: flex;
justify-content: flex-end;
width: 100%;
max-width: 820px;
margin: 1.2rem auto 0.8rem auto;
padding: 0 0.5rem;
}

.user-msg-bubble {
background: linear-gradient(135deg, #1D3B5C 0%, #152E4A 100%);
color: #FFFFFF;
padding: 0.85rem 1.3rem;
border-radius: 20px 20px 4px 20px;
max-width: 76%;
font-size: 0.95rem;
line-height: 1.55;
font-weight: 400;
box-shadow: 0 4px 16px rgba(0, 0, 0, 0.28);
border: 1px solid rgba(56, 189, 248, 0.2);
word-wrap: break-word;
}

/* Assistant message container on the LEFT (warm dark surface) */
[data-testid="stChatMessage"] {
background-color: #262522 !important;
border: 1px solid rgba(255, 255, 255, 0.07) !important;
border-radius: 16px !important;
padding: 1.1rem 1.35rem !important;
max-width: 820px !important;
margin: 0.8rem auto 1.4rem auto !important;
box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2) !important;
}

/* Assistant avatar icon */
[data-testid="stChatMessage"] div[data-testid="stChatMessageAvatarAssistant"],
div[data-testid="stChatMessage"] > div:first-child {
background: rgba(218, 119, 86, 0.15) !important;
color: #DA7756 !important;
border: 1px solid rgba(218, 119, 86, 0.3) !important;
border-radius: 10px !important;
}

/* Chat Disclaimer */
.chat-disclaimer {
text-align: center;
color: #8C8A84;
font-size: 0.76rem;
margin-top: 0.4rem;
margin-bottom: 0.8rem;
letter-spacing: -0.01em;
}

/* Verification Result Cards (Claude Style) */
.verif-card {
border-radius: 12px;
padding: 0.85rem 1.15rem;
margin: 0.75rem 0;
display: flex;
flex-direction: column;
gap: 0.35rem;
box-shadow: 0 2px 10px rgba(0, 0, 0, 0.25);
}

.verif-card-header {
display: flex;
align-items: center;
gap: 0.75rem;
}

.verif-card-icon {
font-size: 1.25rem;
font-weight: 800;
line-height: 1;
}

.verif-card-title-group {
display: flex;
flex-direction: column;
flex-grow: 1;
}

.verif-card-title {
font-weight: 700;
font-size: 0.92rem;
letter-spacing: -0.01em;
}

.verif-card-desc {
font-size: 0.82rem;
font-weight: 400;
opacity: 0.92;
margin-top: 0.1rem;
}

.verif-tag {
padding: 0.2rem 0.55rem;
border-radius: 6px;
font-size: 0.74rem;
font-weight: 700;
letter-spacing: 0.02em;
}

/* Verified (Emerald) */
.verif-card-verified {
background: rgba(34, 197, 94, 0.08);
border: 1px solid rgba(34, 197, 94, 0.28);
color: #4ADE80;
}
.verif-card-verified .verif-tag {
background: rgba(34, 197, 94, 0.18);
color: #86EFAC;
border: 1px solid rgba(34, 197, 94, 0.35);
}

/* Partially Supported (Amber) */
.verif-card-partial {
background: rgba(245, 158, 11, 0.08);
border: 1px solid rgba(245, 158, 11, 0.3);
color: #FBBF24;
}
.verif-card-partial .verif-tag {
background: rgba(245, 158, 11, 0.18);
color: #FDE68A;
border: 1px solid rgba(245, 158, 11, 0.35);
}

/* Not Supported (Red/Rose) */
.verif-card-unsupported {
background: rgba(244, 63, 94, 0.08);
border: 1px solid rgba(244, 63, 94, 0.3);
color: #FB7185;
}

/* Unable to Verify (Slate/Muted) */
.verif-card-unable {
background: rgba(163, 161, 153, 0.08);
border: 1px solid rgba(163, 161, 153, 0.22);
color: #C2BFB6;
}

/* Source Citation Cards */
.citation-card {
background: #262522;
border: 1px solid rgba(255, 255, 255, 0.07);
border-radius: 10px;
padding: 0.85rem 1.1rem;
margin: 0.5rem 0;
transition: border-color 0.2s ease, background 0.2s ease;
}

.citation-card:hover {
border-color: rgba(218, 119, 86, 0.4);
background: #2C2B27;
}

.citation-header {
display: flex;
align-items: center;
justify-content: space-between;
gap: 0.6rem;
margin-bottom: 0.35rem;
}

.citation-badge {
font-size: 0.7rem;
font-weight: 700;
text-transform: uppercase;
padding: 0.15rem 0.5rem;
border-radius: 5px;
background: rgba(218, 119, 86, 0.12);
color: #DA7756;
border: 1px solid rgba(218, 119, 86, 0.25);
}

.citation-title {
color: #FAF9F5;
font-weight: 600;
font-size: 0.9rem;
flex-grow: 1;
overflow: hidden;
text-overflow: ellipsis;
white-space: nowrap;
}

.citation-link {
font-size: 0.76rem;
font-weight: 600;
color: #DA7756 !important;
text-decoration: none !important;
display: inline-flex;
align-items: center;
gap: 0.2rem;
padding: 0.2rem 0.55rem;
border-radius: 6px;
background: rgba(218, 119, 86, 0.1);
border: 1px solid rgba(218, 119, 86, 0.25);
}

.citation-link:hover {
background: rgba(218, 119, 86, 0.22);
}

.citation-snippet {
color: #A3A199;
font-size: 0.82rem;
line-height: 1.45;
margin-top: 0.35rem;
}

/* Insufficient Evidence Card */
.insufficient-evidence-card {
background: rgba(163, 161, 153, 0.08);
border: 1px solid rgba(163, 161, 153, 0.2);
border-radius: 12px;
padding: 1rem 1.25rem;
display: flex;
gap: 0.9rem;
align-items: flex-start;
margin: 0.8rem 0;
}

.insufficient-evidence-icon {
font-size: 1.4rem;
margin-top: 0.1rem;
}

.insufficient-evidence-title {
font-weight: 700;
font-size: 0.95rem;
color: #FAF9F5;
margin-bottom: 0.25rem;
}

.insufficient-evidence-desc {
font-size: 0.84rem;
color: #A3A199;
line-height: 1.5;
margin: 0;
}

/* Metrics Grid */
.metric-grid {
display: grid;
grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
gap: 0.6rem;
margin: 0.7rem 0;
}

.metric-card {
background: #1F1E1D;
border: 1px solid rgba(255, 255, 255, 0.08);
border-radius: 8px;
padding: 0.6rem 0.8rem;
text-align: center;
}

.metric-card-label {
color: #8C8A84;
font-size: 0.7rem;
font-weight: 600;
text-transform: uppercase;
margin-bottom: 0.15rem;
}

.metric-card-val {
color: #FAF9F5;
font-size: 1.1rem;
font-weight: 700;
font-family: 'JetBrains Mono', monospace;
}

/* Expanders (Claude Warm Styling) */
.streamlit-expanderHeader {
background: #262522 !important;
border: 1px solid rgba(255, 255, 255, 0.08) !important;
border-radius: 8px !important;
color: #C2BFB6 !important;
font-weight: 600 !important;
font-size: 0.86rem !important;
}

.streamlit-expanderContent {
border: 1px solid rgba(255, 255, 255, 0.08) !important;
border-top: none !important;
border-bottom-left-radius: 8px !important;
border-bottom-right-radius: 8px !important;
background: #1F1E1D !important;
}

/* Provider Status in Settings */
.provider-row {
display: flex;
align-items: center;
justify-content: space-between;
padding: 0.4rem 0.6rem;
margin-bottom: 0.35rem;
background: #262522;
border-radius: 6px;
border: 1px solid rgba(255, 255, 255, 0.05);
font-size: 0.82rem;
}

.status-badge-ok {
display: inline-flex;
align-items: center;
gap: 0.25rem;
font-size: 0.7rem;
font-weight: 700;
color: #4ADE80;
background: rgba(34, 197, 94, 0.15);
border: 1px solid rgba(34, 197, 94, 0.3);
padding: 0.12rem 0.5rem;
border-radius: 9999px;
}

.status-badge-missing {
display: inline-flex;
align-items: center;
gap: 0.25rem;
font-size: 0.7rem;
font-weight: 600;
color: #8C8A84;
background: rgba(140, 138, 132, 0.12);
border: 1px solid rgba(140, 138, 132, 0.2);
padding: 0.12rem 0.5rem;
border-radius: 9999px;
}

/* Authentication & User Management Styling */
.auth-box-container {
max-width: 460px;
margin: 1.5rem auto 2.5rem auto;
background: #262522;
border: 1px solid rgba(255, 255, 255, 0.08);
border-radius: 16px;
padding: 1.8rem 2rem;
box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
}

.auth-box-header {
text-align: center;
margin-bottom: 1.5rem;
}

.auth-box-title {
font-size: 1.4rem;
font-weight: 700;
color: #FAF9F5;
margin-bottom: 0.35rem;
}

.auth-box-desc {
font-size: 0.85rem;
color: #A3A199;
line-height: 1.4;
}

.user-badge-chip {
display: inline-flex;
align-items: center;
gap: 0.35rem;
padding: 0.2rem 0.55rem;
border-radius: 6px;
font-size: 0.72rem;
font-weight: 700;
}

.admin-badge {
background: rgba(218, 119, 86, 0.15);
border: 1px solid rgba(218, 119, 86, 0.35);
color: #DA7756;
}

.user-badge {
background: rgba(52, 211, 153, 0.12);
border: 1px solid rgba(52, 211, 153, 0.25);
color: #34D399;
}

.blocked-badge {
background: rgba(239, 68, 68, 0.15);
border: 1px solid rgba(239, 68, 68, 0.35);
color: #F87171;
}
</style>"""

st.markdown(CLAUDE_CUSTOM_CSS, unsafe_allow_html=True)


# ============================================================
# FILE / JSON HELPERS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHAT_HISTORY_FILE = os.path.join(BASE_DIR, "chat_history.json")
MEMORY_FILE = os.path.join(BASE_DIR, "memory.json")


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def save_json(path, value):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(value, f, indent=2, ensure_ascii=False)
    except PermissionError:
        raise RuntimeError(
            f"Access denied while saving {path}. "
            "Make sure the file is not open in another program."
        )


def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


# ============================================================
# CONVERSATION MANAGEMENT
# ============================================================


def make_title(text):
    text = re.sub(r"\s+", " ", str(text).strip())
    if not text:
        return "New Chat"
    return text[:42].rstrip() + ("..." if len(text) > 42 else "")


def create_conversation(title="New Chat"):
    ts = now_iso()
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "created_at": ts,
        "updated_at": ts,
        "messages": [],
    }


def normalize_message(message):
    if not isinstance(message, dict):
        return None

    role = message.get("role")
    if role not in ("user", "assistant"):
        return None

    content = message.get("content", "")
    if not isinstance(content, str):
        content = str(content)

    result = {
        "role": role,
        "content": content,
    }

    for key in ("status", "sources", "verification", "timestamp", "answer_model", "error"):
        if key in message:
            result[key] = message[key]

    return result


def normalize_conversation(conversation):
    if not isinstance(conversation, dict):
        conversation = {}

    conversation_id = conversation.get("id")
    if not isinstance(conversation_id, str) or not conversation_id:
        conversation_id = str(uuid.uuid4())

    title = conversation.get("title")
    if not isinstance(title, str) or not title.strip():
        title = "New Chat"

    created_at = conversation.get("created_at") or now_iso()
    updated_at = conversation.get("updated_at") or created_at

    raw_messages = conversation.get("messages", [])
    if not isinstance(raw_messages, list):
        raw_messages = []

    messages = []
    for item in raw_messages:
        normalized = normalize_message(item)
        if normalized:
            messages.append(normalized)

    return {
        "id": conversation_id,
        "title": title,
        "created_at": created_at,
        "updated_at": updated_at,
        "messages": messages,
    }


def convert_old_history(old_history):
    if not isinstance(old_history, list):
        return []

    conversation = create_conversation()

    for item in old_history:
        if not isinstance(item, dict):
            continue

        question = item.get("question")
        answer = item.get("answer")
        if question is None and answer is None:
            continue

        if question is not None:
            conversation["messages"].append({
                "role": "user",
                "content": str(question),
                "timestamp": now_iso(),
            })
            if conversation["title"] == "New Chat":
                conversation["title"] = make_title(question)

        if answer is not None:
            assistant = {
                "role": "assistant",
                "content": str(answer),
                "timestamp": now_iso(),
            }
            for key in ("sources", "verification", "status", "answer_model", "error"):
                if key in item:
                    assistant[key] = item[key]
            conversation["messages"].append(assistant)

    if conversation["messages"]:
        conversation["updated_at"] = now_iso()
        return [conversation]
    return []


def load_user_saved_conversations(user_id: int):
    try:
        user_convs = load_user_conversations(user_id)
        if user_convs:
            return [normalize_conversation(item) for item in user_convs]
    except Exception:
        pass
    return []


def save_conversations():
    try:
        user = st.session_state.get("authenticated_user")
        if user and "conversations" in st.session_state:
            for conv in st.session_state.conversations:
                save_user_conversation(user["id"], conv)
        elif "conversations" in st.session_state:
            save_json(CHAT_HISTORY_FILE, st.session_state.conversations)
    except Exception:
        pass


# Initialize Auth DB
init_db()

if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

if "conversations" not in st.session_state:
    st.session_state.conversations = []

if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None

if "answer_model_index" not in st.session_state:
    st.session_state.answer_model_index = 0

if "last_successful_model" not in st.session_state:
    st.session_state.last_successful_model = None


def get_current_conversation():
    current_id = st.session_state.get("current_conversation_id")

    for conversation in st.session_state.get("conversations", []):
        if conversation.get("id") == current_id:
            return conversation

    if st.session_state.get("conversations"):
        st.session_state.current_conversation_id = st.session_state.conversations[0]["id"]
        return st.session_state.conversations[0]

    conversation = create_conversation()
    if st.session_state.get("authenticated_user"):
        if "conversations" not in st.session_state:
            st.session_state.conversations = []
        st.session_state.conversations.insert(0, conversation)
        st.session_state.current_conversation_id = conversation["id"]
        save_conversations()
    return conversation


def start_new_chat():
    conversation = create_conversation()
    if "conversations" not in st.session_state:
        st.session_state.conversations = []
    st.session_state.conversations.insert(0, conversation)
    st.session_state.current_conversation_id = conversation["id"]
    save_conversations()


def delete_current_chat():
    current_id = st.session_state.get("current_conversation_id")
    user = st.session_state.get("authenticated_user")
    if user and current_id:
        delete_user_conversation(user["id"], current_id)

    st.session_state.conversations = [
        c for c in st.session_state.get("conversations", [])
        if c.get("id") != current_id
    ]

    if not st.session_state.conversations:
        new_conv = create_conversation()
        st.session_state.conversations = [new_conv]
        if user:
            save_user_conversation(user["id"], new_conv)

    st.session_state.current_conversation_id = st.session_state.conversations[0]["id"]
    save_conversations()


def rename_current_chat(new_title):
    conv = get_current_conversation()
    if conv and new_title.strip():
        conv["title"] = new_title.strip()
        conv["updated_at"] = now_iso()
        save_conversations()


def clear_all_chats():
    user = st.session_state.get("authenticated_user")
    if user:
        for c in st.session_state.get("conversations", []):
            delete_user_conversation(user["id"], c.get("id"))
    new_conv = create_conversation()
    st.session_state.conversations = [new_conv]
    st.session_state.current_conversation_id = new_conv["id"]
    if user:
        save_user_conversation(user["id"], new_conv)
    save_conversations()



# ============================================================
# OPENROUTER API
# ============================================================


class OpenRouterError(RuntimeError):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(f"OpenRouter HTTP {status_code}: {message}")


def api_headers():
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": APP_NAME,
    }


def extract_response_content(data):
    choices = data.get("choices", [])
    if not choices:
        return ""

    choice = choices[0] or {}
    message = choice.get("message", {}) or {}

    for key in ("content", "output_text", "text"):
        value = message.get(key) if key != "text" else choice.get(key)
        if isinstance(value, str) and value.strip():
            raw_text = value.strip()
            # Strip reasoning/thought tags that some open source models output in content
            cleaned = re.sub(r"<(?:think|thought)>.*?</(?:think|thought)>", "", raw_text, flags=re.DOTALL | re.IGNORECASE).strip()
            return cleaned if cleaned else raw_text

    return ""


def openrouter_request(
    model,
    messages,
    max_tokens=700,
    temperature=0.2,
    response_format=None,
    extra_payload=None,
):
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured."
        )

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    if response_format is not None:
        payload["response_format"] = response_format

    if extra_payload:
        payload.update(extra_payload)

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers=api_headers(),
            json=payload,
            timeout=OPENROUTER_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Network error while contacting OpenRouter: {exc}"
        )

    if response.status_code != 200:
        try:
            body = response.json()
            error_obj = body.get("error", {})
            message = error_obj.get("message") or response.text
        except Exception:
            message = response.text

        raise OpenRouterError(response.status_code, message)

    try:
        data = response.json()
    except Exception as exc:
        raise RuntimeError(
            f"OpenRouter returned invalid JSON: {exc}"
        )

    content = extract_response_content(data)
    if not content:
        choice = data.get("choices", [{}])[0] or {}
        message = choice.get("message", {}) or {}
        raise RuntimeError(
            "OpenRouter returned an empty answer. "
            f"finish_reason={choice.get('finish_reason')}, "
            f"reasoning_present={bool(message.get('reasoning'))}"
        )

    return {
        "content": content,
        "raw": data,
    }


# ============================================================
# LIVE FREE-MODEL DISCOVERY
# ============================================================
# Hardcoded ":free" slugs rot — OpenRouter periodically retires them and
# returns a 404 telling you to use the paid slug instead. Pulling the
# current free catalog live means a dead model just falls out of rotation
# instead of taking down every answer attempt.


DISALLOWED_FREE_MODEL_SUBSTRINGS = (
    "safety", "guard", "moderation", "embed", "vision", "note-preview",
    "clip", "tts", "ranker", "reward", "code", "image", "inkling",
)


def fetch_free_model_ids(limit=20):
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers=api_headers() if OPENROUTER_API_KEY else {},
            timeout=SEARCH_TIMEOUT,
        )
        if response.status_code != 200:
            return []
        data = response.json().get("data", [])
    except Exception:
        return []

    free_ids = []
    for model in data:
        model_id = model.get("id", "")
        if not model_id.endswith(":free"):
            continue
        model_id_lower = model_id.lower()
        if any(bad in model_id_lower for bad in DISALLOWED_FREE_MODEL_SUBSTRINGS):
            continue
        context_length = model.get("context_length") or 0
        free_ids.append((context_length, model_id))

    # Larger context first: more room for evidence + reasoning + answer.
    free_ids.sort(reverse=True)
    return [model_id for _, model_id in free_ids[:limit]]


def get_model_pool():
    now = time.time()
    cached = st.session_state.get("_model_pool_cache")
    if cached and now - cached["fetched_at"] < MODEL_LIST_TTL_SECONDS:
        return cached["models"]

    live = fetch_free_model_ids()

    if live:
        # Known-good models first if still live, then the rest of the pool.
        ordered = [m for m in FALLBACK_ANSWER_MODELS if m in live]
        ordered += [m for m in live if m not in ordered]
        models = ordered
    else:
        models = list(FALLBACK_ANSWER_MODELS)

    # BUGFIX: previously nothing detected the live free-model pool changing
    # between refreshes (models retired/added), so answer_model_index could
    # keep pointing at a model that's no longer in the same position — or
    # even a completely different model than what the sidebar last showed.
    # Reset the rotation index whenever the pool's actual contents change.
    pool_signature = tuple(models)
    if st.session_state.get("_model_pool_signature") != pool_signature:
        st.session_state["_model_pool_signature"] = pool_signature
        st.session_state["answer_model_index"] = 0

    st.session_state["_model_pool_cache"] = {"fetched_at": now, "models": models}
    return models


def get_answer_models():
    pool = get_model_pool()
    return pool if pool else list(FALLBACK_ANSWER_MODELS)


def get_verifier_models():
    pool = get_model_pool()
    if not pool:
        return list(FALLBACK_VERIFIER_MODELS)
    # The dynamic router stays first choice when it's present.
    ordered = [m for m in pool if m == "openrouter/free"]
    ordered += [m for m in pool if m != "openrouter/free"]
    return ordered


# ============================================================
# CASUAL QUESTIONS (LLM-classified, no hardcoded phrase list)
# ============================================================
# Instead of matching a fixed dictionary of exact phrases, ask a free model
# to decide whether the message is small talk (greeting, "how are you",
# thanks, goodbye...) or a real question that needs web-grounded research.
# This costs one extra free-model call per message (including plain "hi"),
# but scales to any phrasing without hand-listing variants.
#
# Fails OPEN: if classification errors out or is inconclusive, treat the
# message as a real question and let it fall through to the full
# search + grounded-answer + verification pipeline, rather than blocking.

# ============================================================
# CASUAL QUESTIONS (hybrid: instant quick-match, LLM for the rest)
# ============================================================
# Two layers:
#   1. quick_casual_reply() — a tiny regex pre-filter that answers the most
#      common greetings/thanks/etc. INSTANTLY, with zero API calls. This
#      exists purely for latency: these are extremely common messages and
#      there's no reason to pay a model round-trip for "hi".
#   2. classify_casual() — for anything the quick filter doesn't recognize,
#      ask a free model to decide casual-vs-real-question. This is what
#      lets phrasing the quick filter never anticipated ("how ya doing",
#      "sup", "what's good") still get caught without hand-listing every
#      variant. Only called for SHORT messages (<= 8 words) — a long,
#      clearly substantive question skips the classifier call entirely and
#      goes straight to the research pipeline, since there's no ambiguity
#      to resolve and no reason to spend a model call on it.
#
# classify_casual fails OPEN: any error, timeout, or inconclusive reply
# just returns None, and the message proceeds through the normal
# search + grounded-answer + verification pipeline rather than blocking.

_CASUAL_QUICK_PATTERNS = [
    (re.compile(r"^(hi|hello|hey|yo)( bro)?$"), "Hey! 👋"),
    (re.compile(r"^(bye|goodbye|see ya|see you|cya)$"), "Take care! 👋"),
    (re.compile(r"^(thanks?( you)?|ty|thx)$"), "You're welcome! 😎"),
    (re.compile(r"^(ok|okay|k)$"), "👍"),
    (
        re.compile(r"^(what'?s up|wyd|what are (you|u) doing)$"),
        "Not much — ready to fact-check whenever you are. 🛡️",
    ),
    (
        re.compile(
            r"^how'?s? (it going|(are|r) (you|u)( doing)?)$"
        ),
        "I'm an AI, so no feelings to report, but I'm running fine and ready to help! 🛡️",
    ),
    (
        re.compile(r"^who (are|r) (you|u)$"),
        "I'm your Hallucination Detector — I search for evidence, generate an answer, and independently verify it. 🛡️",
    ),
]

_CASUAL_GOOD_TIME_PATTERN = re.compile(r"^good (morning|night|afternoon|evening)$")
_CASUAL_GOOD_TIME_EMOJI = {
    "morning": "☀️", "night": "🌙", "afternoon": "🌤️", "evening": "🌆",
}


def _normalize_quick_casual(text):
    text = text.lower().strip()
    text = re.sub(r"[!?.,]+$", "", text)
    return re.sub(r"\s+", " ", text)


def quick_casual_reply(question):
    """Zero-API-call match for the handful of extremely common casual
    phrasings. Returns a reply string, or None if nothing matched (in
    which case the caller falls back to classify_casual)."""
    q = _normalize_quick_casual(question)

    time_match = _CASUAL_GOOD_TIME_PATTERN.match(q)
    if time_match:
        word = time_match.group(1)
        return f"Good {word}! {_CASUAL_GOOD_TIME_EMOJI[word]}"

    for pattern, reply in _CASUAL_QUICK_PATTERNS:
        if pattern.match(q):
            return reply

    return None


CASUAL_CLASSIFIER_SYSTEM_PROMPT = """
You are a small-talk gate in front of a fact-checking assistant.

Decide whether the LATEST USER MESSAGE is casual conversation (a greeting,
"how are you", thanks, goodbye, small talk with no factual claim to check)
or a genuine question/request that needs to be researched and grounded in
web evidence.

If it is casual small talk: reply with a short, friendly, natural response,
prefixed EXACTLY with "CASUAL:" and nothing before it. If the message asks
about your own state/feelings, say plainly that you're an AI with no
feelings but are working fine — do not invent any other fact about yourself.

If it is a real question/request that needs facts, reply with EXACTLY the
single word NEEDS_SEARCH and nothing else.

If you are unsure which it is, output NEEDS_SEARCH — never guess a
"casual" reply for something that might need real facts.
"""

# Only messages this short are even eligible for the LLM classifier call —
# anything longer is assumed to be a real question, skipping the extra
# round-trip entirely.
CASUAL_CLASSIFIER_MAX_WORDS = 8


def classify_casual(question):
    """Returns a reply string if `question` is casual small talk, or None
    if it needs the real research pipeline (including on failure — this
    fails open, it never blocks a real question)."""
    messages = [
        {"role": "system", "content": CASUAL_CLASSIFIER_SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    dead_models = st.session_state.setdefault("_dead_models", set())
    models = [m for m in get_answer_models() if m not in dead_models]
    if not models:
        models = get_answer_models()

    # Only 2 attempts: this gate must stay cheap and fast, and failing
    # open (falling through to search) is always safe here.
    for model in models[:2]:
        try:
            result = openrouter_request(
                model=model,
                messages=messages,
                max_tokens=120,
                temperature=0.0,
                extra_payload={"reasoning": {"effort": "none", "exclude": True}},
            )
            content = result["content"].strip()
        except Exception:
            continue

        upper = content.upper()

        if upper.startswith("NEEDS_SEARCH"):
            return None

        if upper.startswith("CASUAL:"):
            reply = content.split(":", 1)[1].strip()
            return reply or None

        # Model didn't follow the exact format. Treat a short, plainly
        # non-factual-looking reply as casual; anything else falls
        # through to search rather than risk swallowing a real question.
        if content and len(content) < 200:
            return content

    return None


def casual_response(question):
    """Hybrid entry point: instant regex match first (no API call), then
    the LLM classifier — but only for short messages, since a long message
    is assumed to be a real question and skips the extra round-trip."""
    quick = quick_casual_reply(question)
    if quick:
        return quick

    if len(question.split()) <= CASUAL_CLASSIFIER_MAX_WORDS:
        return classify_casual(question)

    return None


# ============================================================
# FREE WEB SEARCH
# ============================================================


def clean_text(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def clean_search_url(url):
    if not url:
        return ""

    url = html.unescape(url)

    # DuckDuckGo redirect URLs often look like /l/?uddg=<encoded-url>.
    parsed = urlparse(url)
    if parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        if target:
            url = unquote(target)

    if url.startswith("//"):
        url = "https:" + url

    if not url.startswith(("http://", "https://")):
        return ""

    return url


def fetch_url_text(url, timeout=SEARCH_TIMEOUT):
    """Fetch a readable text page without requiring a paid search API."""
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/142 Safari/537.36"
                )
            },
            timeout=timeout,
        )
        if response.status_code != 200:
            return ""

        content_type = response.headers.get("content-type", "").lower()
        if "text" not in content_type and "html" not in content_type:
            return ""

        raw = response.text
        raw = re.sub(r"<script[\s\S]*?</script>", " ", raw, flags=re.I)
        raw = re.sub(r"<style[\s\S]*?</style>", " ", raw, flags=re.I)
        raw = re.sub(r"<noscript[\s\S]*?</noscript>", " ", raw, flags=re.I)
        raw = re.sub(r"<[^>]+>", " ", raw)
        text = clean_text(raw)
        return text[:MAX_SOURCE_CONTENT]
    except requests.RequestException:
        return ""


def wikipedia_search(query, limit=5):
    sources = []

    data = None
    for attempt in range(2):
        try:
            response = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": limit,
                    "format": "json",
                    "utf8": 1,
                },
                headers={"User-Agent": "HallucinationDetectorBot/2.0 (AI Research; mailto:contact@hallucinationdetector.local)"},
                timeout=SEARCH_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            break
        except Exception:
            if attempt == 0:
                time.sleep(0.4)
            else:
                return sources

    if not data:
        return sources

    search_items = data.get("query", {}).get("search", [])
    if not search_items:
        return sources

    # Fetch rich full extracts for top results concurrently for comprehensive grounding
    top_titles = [item.get("title", "") for item in search_items[:3] if item.get("title")]
    extracts = {}
    if top_titles:
        def _fetch_single_wiki_extract(t):
            try:
                r_ext = requests.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "prop": "extracts",
                        "explaintext": 1,
                        "exsectionformat": "plain",
                        "titles": t,
                        "format": "json",
                        "redirects": 1,
                    },
                    headers={"User-Agent": "HallucinationDetectorBot/2.0 (AI Research; mailto:contact@hallucinationdetector.local)"},
                    timeout=SEARCH_TIMEOUT,
                )
                if r_ext.status_code == 200:
                    pages = r_ext.json().get("query", {}).get("pages", {})
                    for page in pages.values():
                        txt = clean_text(page.get("extract", ""))
                        if txt:
                            return t, txt[:MAX_SOURCE_CONTENT]
            except Exception:
                pass
            return t, ""

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(top_titles), 3)) as executor:
            for t, txt in executor.map(_fetch_single_wiki_extract, top_titles):
                if txt:
                    extracts[t] = txt

    for item in search_items:
        title = clean_text(item.get("title", ""))
        if not title:
            continue

        url = "https://en.wikipedia.org/wiki/" + quote_plus(
            title.replace(" ", "_")
        )

        content = extracts.get(title, "")
        if not content:
            raw_snip = item.get("snippet", "")
            content = clean_text(re.sub(r"<[^>]+>", " ", raw_snip))

        if content:
            sources.append({
                "title": f"Wikipedia - {title}",
                "url": url,
                "content": content[:MAX_SOURCE_CONTENT],
            })

    return sources


def _generic_link_scrape(page, limit, skip_domains):
    """Last-resort extraction: grab any <a href> that isn't obviously site
    navigation/chrome. Used when a search engine's specific result markup
    (CSS classes etc.) doesn't match — which happens whenever the site
    tweaks its HTML — so a page fetch that succeeded doesn't silently turn
    into zero results just because the class-based regex missed."""
    sources = []
    seen = set()

    for href, text_html in re.findall(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        page, flags=re.I | re.S,
    ):
        url = clean_search_url(href)
        title = clean_text(re.sub(r"<[^>]+>", " ", text_html))
        if not url or not title or len(title) < 4:
            continue
        domain = urlparse(url).netloc.lower()
        if not domain or any(bad in domain for bad in skip_domains):
            continue
        if url in seen:
            continue
        seen.add(url)
        sources.append({"title": title, "url": url, "content": ""})
        if len(sources) >= limit:
            break

    return sources


def duckduckgo_search(query, limit=6):
    """Free DuckDuckGo HTML search with a lite-page fallback.

    Returns (sources, diagnostics_entry) instead of pushing diagnostics
    into st.session_state directly — this function now runs inside a
    ThreadPoolExecutor worker thread (see free_web_search), and Streamlit's
    session_state is only safe to touch from the main script thread. The
    caller merges diagnostics into session_state itself, back on the main
    thread."""
    sources = []
    diagnostics = {"attempts": [], "blocks_found": 0, "fallback_used": False}

    def diag_entry():
        return {"engine": "duckduckgo", "query": query, **diagnostics}

    urls = [
        "https://html.duckduckgo.com/html/?q=" + quote_plus(query),
        "https://lite.duckduckgo.com/lite/?q=" + quote_plus(query),
    ]

    page = ""
    for search_url in urls:
        try:
            response = requests.get(
                search_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 Chrome/142 Safari/537.36"
                    )
                },
                timeout=SEARCH_TIMEOUT,
            )
            diagnostics["attempts"].append(
                f"{search_url.split('?')[0]} -> HTTP {response.status_code}, "
                f"{len(response.text or '')} chars"
            )
            if response.status_code == 200 and response.text:
                page = response.text
                break
        except requests.RequestException as exc:
            diagnostics["attempts"].append(f"{search_url.split('?')[0]} -> {exc}")
            continue

    if not page:
        return sources, diag_entry()

    # Standard DDG HTML results.
    blocks = re.findall(
        r"<div[^>]*class=[\"'].*?result.*?[\"'][^>]*>(.*?)"
        r"(?=<div[^>]*class=[\"'].*?result.*?[\"']|$)",
        page,
        flags=re.I | re.S,
    )

    # DDG Lite uses table rows instead of result divs.
    if not blocks:
        lite_rows = re.findall(
            r'<tr[^>]*>(.*?)</tr>', page, flags=re.I | re.S
        )
        for row in lite_rows:
            link_match = re.search(
                r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
                row, flags=re.I | re.S
            )
            if not link_match:
                continue
            url = clean_search_url(link_match.group(1))
            title = clean_text(re.sub(r'<[^>]+>', ' ', link_match.group(2)))
            if not url or not title:
                continue
            text = clean_text(re.sub(r'<[^>]+>', ' ', row))
            text = re.sub(re.escape(title), '', text, count=1, flags=re.I).strip()
            sources.append({
                "title": title,
                "url": url,
                "content": text[:MAX_SOURCE_CONTENT],
            })
            if len(sources) >= limit:
                break

        diagnostics["blocks_found"] = len(lite_rows)
        if not sources:
            # Class-based lite-row parsing also missed — DDG's markup has
            # likely changed. Fall back to a generic link scrape rather
            # than giving up on a page we successfully fetched.
            diagnostics["fallback_used"] = True
            sources = _generic_link_scrape(
                page, limit, skip_domains=("duckduckgo.com",)
            )
            for source in sources[:3]:
                fetched = fetch_url_text(source["url"])
                if fetched:
                    source["content"] = fetched

        return sources, diag_entry()

    diagnostics["blocks_found"] = len(blocks)

    for block in blocks[:limit]:
        link_match = re.search(
            r"<a[^>]+class=[\"']([^\"']*result__a[^\"']*)[\"'][^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
            block, flags=re.I | re.S
        )
        if not link_match:
            # Attribute order can vary.
            link_match = re.search(
                r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*class=[\"'][^\"']*result__a[^\"']*[\"'][^>]*>(.*?)</a>",
                block, flags=re.I | re.S
            )
            if not link_match:
                continue
            url = clean_search_url(link_match.group(1))
            title_html = link_match.group(2)
        else:
            url = clean_search_url(link_match.group(2))
            title_html = link_match.group(3)

        title = clean_text(re.sub(r'<[^>]+>', ' ', title_html))
        if not url or not title:
            continue

        snippet_match = re.search(
            r"class=[\"'][^\"']*result__snippet[^\"']*[\"'][^>]*>(.*?)</(?:a|div)>",
            block, flags=re.I | re.S
        )
        snippet = clean_text(
            re.sub(r'<[^>]+>', ' ', snippet_match.group(1))
        ) if snippet_match else ""

        content = snippet
        if len(sources) < 3:
            fetched = fetch_url_text(url)
            if fetched:
                content = fetched

        if content:
            sources.append({
                "title": title,
                "url": url,
                "content": content[:MAX_SOURCE_CONTENT],
            })

    if not sources:
        # We found "result" divs but couldn't extract a link+title from
        # any of them — the inner markup changed. Fall back generically.
        diagnostics["fallback_used"] = True
        sources = _generic_link_scrape(
            page, limit, skip_domains=("duckduckgo.com",)
        )
        for source in sources[:3]:
            fetched = fetch_url_text(source["url"])
            if fetched:
                source["content"] = fetched

    return sources, diag_entry()


def bing_search(query, limit=6):
    """Second free scrape target, used when DuckDuckGo returns nothing.

    Returns (sources, diagnostics_entry) — see duckduckgo_search's
    docstring for why: this runs inside a worker thread now."""
    sources = []
    diagnostics = {"attempts": [], "blocks_found": 0, "fallback_used": False}

    def diag_entry():
        return {"engine": "bing", "query": query, **diagnostics}

    try:
        response = requests.get(
            "https://www.bing.com/search?q=" + quote_plus(query),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/142 Safari/537.36"
                )
            },
            timeout=SEARCH_TIMEOUT,
        )
        diagnostics["attempts"].append(
            f"bing.com/search -> HTTP {response.status_code}, "
            f"{len(response.text or '')} chars"
        )
        if response.status_code != 200:
            return sources, diag_entry()
        page = response.text
    except requests.RequestException as exc:
        diagnostics["attempts"].append(f"bing.com/search -> {exc}")
        return sources, diag_entry()

    blocks = re.findall(r'<li class="b_algo"[^>]*>(.*?)</li>', page, flags=re.I | re.S)
    diagnostics["blocks_found"] = len(blocks)

    for block in blocks[:limit]:
        link_match = re.search(
            r'<h2><a href="([^"]+)"[^>]*>(.*?)</a></h2>', block, flags=re.I | re.S
        )
        if not link_match:
            continue

        url = clean_search_url(link_match.group(1))
        title = clean_text(re.sub(r'<[^>]+>', ' ', link_match.group(2)))
        if not url or not title:
            continue

        snippet_match = re.search(
            r'<p>(.*?)</p>', block, flags=re.I | re.S
        )
        snippet = clean_text(
            re.sub(r'<[^>]+>', ' ', snippet_match.group(1))
        ) if snippet_match else ""

        content = snippet
        if len(sources) < 3:
            fetched = fetch_url_text(url)
            if fetched:
                content = fetched

        if content:
            sources.append({
                "title": title,
                "url": url,
                "content": content[:MAX_SOURCE_CONTENT],
            })

    if not sources:
        # Bing's markup changed / class-based parse missed — fall back to
        # a generic link scrape instead of quietly returning nothing from
        # a page we successfully fetched.
        diagnostics["fallback_used"] = True
        sources = _generic_link_scrape(
            page, limit, skip_domains=("bing.com", "microsoft.com")
        )
        for source in sources[:3]:
            fetched = fetch_url_text(source["url"])
            if fetched:
                source["content"] = fetched

    return sources, diag_entry()


def duckduckgo_instant_answer(query):
    """DuckDuckGo's Instant Answer JSON API — a real, documented, key-free
    API endpoint, NOT HTML scraping. html.duckduckgo.com / bing.com have
    been returning zero results from this host across multiple real
    queries (confirmed via the search diagnostics), which strongly
    suggests those specific scrape endpoints are being blocked at the
    network level for this deployment — a very common outcome for
    cloud-hosted IPs. api.duckduckgo.com is a different service and isn't
    subject to that block. It's weaker for broad web search, but its
    RelatedTopics field is built exactly for disambiguation — i.e. exactly
    what an acronym question like "CBE" needs."""
    sources = []
    diagnostics = {"attempts": [], "blocks_found": 0, "fallback_used": False}

    try:
        response = requests.get(
            "https://api.duckduckgo.com/",
            params={
                "q": query,
                "format": "json",
                "no_redirect": 1,
                "no_html": 1,
                "skip_disambig": 0,
            },
            headers={"User-Agent": "HallucinationDetector/1.0"},
            timeout=SEARCH_TIMEOUT,
        )
        diagnostics["attempts"].append(
            f"api.duckduckgo.com -> HTTP {response.status_code}, "
            f"{len(response.text or '')} chars"
        )
        if response.status_code != 200:
            st.session_state.setdefault("_search_diagnostics", []).append(
                {"engine": "ddg_instant_answer", "query": query, **diagnostics}
            )
            return sources
        data = response.json()
    except Exception as exc:
        diagnostics["attempts"].append(f"api.duckduckgo.com -> {exc}")
        st.session_state.setdefault("_search_diagnostics", []).append(
            {"engine": "ddg_instant_answer", "query": query, **diagnostics}
        )
        return sources

    def add(text, url):
        text = clean_text(text)
        url = clean_search_url(url) if url else ""
        if text and url:
            sources.append({
                "title": text[:120],
                "url": url,
                "content": text[:MAX_SOURCE_CONTENT],
            })

    if data.get("AbstractText"):
        add(data.get("AbstractText"), data.get("AbstractURL", ""))

    if data.get("Definition"):
        add(data.get("Definition"), data.get("DefinitionURL", ""))

    def walk_topics(topics):
        for item in topics:
            if "Topics" in item:
                walk_topics(item["Topics"])
            elif item.get("Text"):
                add(item.get("Text"), item.get("FirstURL", ""))

    walk_topics(data.get("RelatedTopics", []))

    diagnostics["blocks_found"] = len(sources)
    st.session_state.setdefault("_search_diagnostics", []).append(
        {"engine": "ddg_instant_answer", "query": query, **diagnostics}
    )
    return sources


ACRONYM_STOPWORDS = {
    "where", "what", "which", "who", "when", "how", "why", "is", "are",
    "was", "were", "the", "a", "an", "in", "on", "at", "of", "for", "to",
    "me", "my", "you", "your", "give", "tell", "does", "did", "has", "had",
    "not", "can", "and", "its", "his", "her", "located", "location",
    "place", "city", "full", "form", "name", "meaning", "stands", "about",
    # Common English question-word contractions.
    "whats", "hows", "wheres", "whens", "whys", "whos", "whichs",
    "isnt", "arent", "wasnt", "werent", "dont", "doesnt", "didnt",
    "cant", "wont", "couldnt", "wouldnt", "shouldnt", "hasnt", "hadnt",
    # Meta-verbs about an acronym/abbreviation question, not the acronym itself
    "stand", "mean", "means", "refer", "refers", "referred", "known",
    "call", "called", "short", "term", "word", "words",
    # Roman numerals (prevent World War II / King Henry VIII from triggering acronym queries)
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
    # Short words/particles that should not be queried as bare acronyms
    "ai", "as", "if", "or", "in", "on", "at", "by", "to", "do", "no", "so", "us", "uk", "it",
}


def extract_acronym_candidate(text):
    """Return an acronym candidate if present.
    Strictly prefers uppercase tokens (e.g. 'CM', 'CBE', 'NASA', 'AI', 'WHO').
    If no uppercase token exists, only allows lowercase candidates if the question
    explicitly asks for an abbreviation expansion (e.g. 'full form', 'stands for', 'meaning of').
    This prevents ordinary capitalized words (e.g. 'Chief', 'Story', 'Hotel') from being
    hijacked as acronym disambiguations."""
    tokens = re.findall(r"[A-Za-z0-9]+", text)
    upper_candidates = [
        t for t in tokens
        if t.isupper() and 2 <= len(t) <= 6 and t.lower() not in ACRONYM_STOPWORDS
    ]
    if upper_candidates:
        return upper_candidates[0]

    # Only fall back to case-insensitive candidate if the user query explicitly asks for an acronym definition
    text_lower = text.lower()
    is_acronym_query = any(phrase in text_lower for phrase in (
        "full form", "stands for", "stand for", "abbreviation", "short form",
        "meaning of", "acronym", "stands as"
    ))
    if is_acronym_query:
        candidates = [
            t for t in tokens
            if 2 <= len(t) <= 6 and t.lower() not in ACRONYM_STOPWORDS
        ]
        if candidates:
            return candidates[0]

    return None


CONTEXT_STOPWORDS = {
    "where", "what", "which", "who", "when", "how", "why", "is", "are",
    "was", "were", "the", "a", "an", "in", "on", "at", "of", "for", "to",
    "me", "my", "you", "your", "give", "tell", "does", "did", "has", "had",
    "not", "can", "and", "its", "his", "her", "about",
    "whats", "full", "form", "meaning", "stands", "abbreviation", "acronym",
}


def extract_context_words(question, acronym):
    """Words in the question (besides the acronym itself and generic
    filler) that hint at *which* meaning of the acronym is intended — e.g.
    "city" in "the city CBE". Deliberately uses a SEPARATE, smaller
    stopword list from ACRONYM_STOPWORDS: that list excludes words like
    "city"/"location"/"place" specifically so they're never mistaken for
    the acronym itself, but those are exactly the hint words this function
    needs to keep. Used to bias search queries and source ranking toward
    the sense actually being asked about, without hardcoding any specific
    acronym or meaning."""
    tokens = re.findall(r"[A-Za-z][A-Za-z]+", question.lower())
    acro_lower = (acronym or "").lower()
    return [
        t for t in tokens
        if t not in CONTEXT_STOPWORDS and t != acro_lower and len(t) > 2
    ]


def build_search_queries(question):
    """Create targeted free-search queries for factual questions."""
    q = re.sub(r"\s+", " ", question.strip())
    lower = q.lower()
    word_count = len(q.split())
    queries = []

    # For concise questions, keep full question as top query; for long complex questions,
    # put distilled focused queries first so search engines don't choke on 30-word sentences.
    if word_count <= 8:
        queries.append(q)

    location_words = (
        "where", "located", "location", "place", "city", "town",
        "district", "state", "country", "address", "situated", "based"
    )
    full_form_words = (
        "full form", "full name", "meaning", "stands for",
        "abbreviation", "acronym"
    )
    asks_location = any(word in lower for word in location_words)
    asks_full_form = any(word in lower for word in full_form_words)

    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]*", q)
    ignored = {
        "where", "what", "which", "who", "when", "how", "why",
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "in", "on", "at", "for", "to", "by", "from", "with", "of", "about",
        "give", "me", "tell", "does", "do", "did", "can", "please",
        "explain", "distinguish", "describe", "discuss", "using", "approximate",
        "actually", "terms", "typical", "major", "differences", "difference",
        "latest", "previous", "generation", "if", "as", "and", "or", "not"
    }
    entities = [
        token for token in tokens
        if token.lower() not in ignored and len(token) >= 2
    ]
    if not entities and tokens:
        entities = tokens

    # 1. Multi-entity comparison extraction (e.g. 'between X, Y, and Z')
    m_between = re.search(r"\bbetween\s+([^?]+?)(?:\s+in terms of|\s+regarding|\s+and how|\s*\?|$)", q, re.I)
    if m_between:
        clause = m_between.group(1).strip()
        sub_items = re.split(r",\s*|\s+and\s+|\s+or\s+", clause)
        for s_item in sub_items:
            s_clean = re.sub(r"^(?:the\s+)", "", s_item.strip(), flags=re.I).strip()
            w_list = [w for w in s_clean.split() if w.lower() not in ignored]
            if len(w_list) >= 1:
                queries.append(" ".join(w_list[:4]))

    # 2. Extract X of Y relational phrases (e.g. "geographic center of India", "discovery of penicillin")
    for m in re.finditer(r"\b([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+of\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\b", q, re.I):
        lw = [w for w in m.group(1).split() if w.lower() not in ignored]
        rw = [w for w in m.group(2).split() if w.lower() not in ignored]
        if lw and rw:
            queries.append(f"{' '.join(lw)} of {' '.join(rw)}")

    # 3. Capitalized proper nouns & named entities (e.g. "Alexander Fleming", "Antonio Meucci", "Alexander Graham Bell")
    prop_pattern = r"\b[A-Z][a-zA-Z0-9']*(?:\s+(?:van|von|de|da|del|of|the|for|and)\s+[A-Z][a-zA-Z0-9']+|\s+[A-Z][a-zA-Z0-9']+|\s+[0-9]{4})*\b"
    for cp in re.findall(prop_pattern, q):
        words = [w for w in cp.split() if w.lower() not in ignored]
        if words and len(words) >= 1:
            clean_cp = " ".join(words)
            if len(clean_cp) >= 3 and clean_cp.lower() not in ignored:
                queries.append(clean_cp)

    # 4. Add core entity / keyword phrase (up to 4-5 core tokens)
    if entities:
        if len(entities) <= 6:
            queries.append(" ".join(entities))
        else:
            queries.append(" ".join(entities[:5]))
            queries.append(" ".join(entities[5:10]))

    # Acronym handling — works regardless of case.
    acro = extract_acronym_candidate(q)
    if acro:
        context_words = extract_context_words(q, acro)
        if context_words:
            queries.append(f'"{acro}" {" ".join(context_words[:3])}')
        queries.extend([
            f'"{acro}" full form',
            f'"{acro}" abbreviation meaning',
            f'"{acro}" stands for',
            f'{acro} disambiguation',
        ])

    if asks_location and entities:
        entity = " ".join(entities[:4])
        queries.extend([
            f'"{entity}" location',
            f'where is {entity}',
            f'{entity} country',
        ])

    if asks_full_form and entities:
        entity = " ".join(entities[:4])
        queries.extend([
            f'"{entity}" full form',
            f'"{entity}" meaning abbreviation',
            f'"{entity}" stands for',
        ])

    clean_q = re.sub(r"[?!.,;]+", "", q).strip()
    if clean_q and word_count <= 14:
        queries.append(clean_q)

    # Deduplicate while preserving order
    result = []
    seen = set()
    for item in queries:
        item = item.strip()
        key = item.lower()
        if item and key not in seen and len(item) >= 2:
            seen.add(key)
            result.append(item)

    return result[:6]


def source_score(source, question):
    """Rank sources by exact entity/question relevance, not raw word overlap."""
    title = clean_text(source.get("title", "")).lower()
    content = clean_text(source.get("content", "")).lower()
    url = source.get("url", "").lower()
    q = clean_text(question).lower()

    tokens = [t for t in re.findall(r"[a-z0-9][a-z0-9._-]*", q) if len(t) >= 2]
    stop = {
        "where", "what", "which", "who", "when", "how", "why", "is", "are", "was", "were",
        "the", "a", "an", "in", "on", "at", "of", "for", "to", "by", "from", "with",
        "me", "give", "tell", "does", "do", "about", "can", "you", "please",
    }
    important = [t for t in tokens if t not in stop]
    if not important:
        important = tokens

    score = 0
    title_tokens = set(re.findall(r"[a-z0-9][a-z0-9._-]*", title))

    for token in important:
        if token in title_tokens:
            score += 14
        elif token in title:
            score += 7
        if token in content:
            score += 2

    # Exact multi-word entity/question matches are extremely strong evidence.
    # Fires for single-word entities too (e.g. bare acronyms like "CBE"),
    # not just phrases of 2+ words.
    entity_patterns = []
    if important:
        entity_patterns.append(" ".join(important[:4]))

    # BUGFIX: build phrases only from consecutive runs of non-stopword
    # tokens in the question, not raw n-grams over the whole question
    # (which let filler/leftover words like "located" become their own
    # substring-matched "entity" — see comment above and the changelog).
    raw_tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9.-]*", question)
    run = []
    for raw_tok in raw_tokens:
        if raw_tok.lower() in stop or len(raw_tok) < 2:
            if run:
                phrase = " ".join(run).lower()
                if phrase not in entity_patterns:
                    entity_patterns.append(phrase)
            run = []
        else:
            run.append(raw_tok)
    if run:
        phrase = " ".join(run).lower()
        if phrase not in entity_patterns:
            entity_patterns.append(phrase)

    # Raw acronym token straight from the original question (preserves case
    # signal even though matching itself is case-insensitive).
    for raw in re.findall(r"[A-Za-z0-9]+", question):
        if raw.isupper() and 2 <= len(raw) <= 6:
            cleaned = raw.lower()
            if cleaned not in entity_patterns:
                entity_patterns.append(cleaned)

    for phrase in entity_patterns:
        if not phrase:
            continue
        # Short acronyms get a smaller absolute bonus (less specific) but
        # still fire, instead of being skipped entirely.
        title_bonus = 30 if len(phrase) > 3 else 22
        content_bonus = 12 if len(phrase) > 3 else 9
        if phrase in title:
            score += title_bonus
        elif phrase in content:
            score += content_bonus

    # Context-sense bonus: when the acronym AND a question context word
    # (e.g. "city", "railway") both show up in the same source, that
    # source is describing the sense the user actually meant — push it
    # above sources that only match the bare acronym. This is what makes
    # "the city CBE" prefer a Coimbatore-railway/city page over an
    # unrelated "CBE" expansion that happens to rank well on its own.
    acro = extract_acronym_candidate(question)
    if acro:
        acro_lower = acro.lower()
        acro_present = acro_lower in title or acro_lower in content
        if acro_present:
            context_words = extract_context_words(question, acro)
            for cw in context_words[:5]:
                if cw in title:
                    score += 16
                elif cw in content:
                    score += 8

    if "wikipedia.org" in url:
        score += 4
    if any(tld in url for tld in (
        ".gov", ".nic.", ".edu", ".org", ".int"
    )):
        score += 8

    return score


def free_web_search(question):
    """Free evidence retrieval using Wikipedia and DuckDuckGo, with a Bing
    HTML fallback when DuckDuckGo returns nothing (it rate-limits/changes
    markup often and fails silently).

    Wikipedia + DuckDuckGo calls for all queries run CONCURRENTLY via a
    ThreadPoolExecutor instead of one after another — this is the single
    biggest latency win, since the old sequential version could mean
    dozens of blocking HTTP round-trips (5 queries x 2 engines, plus
    per-source page fetches inside each) stacked back to back. All
    st.session_state / diagnostics writes still happen on the main thread
    only, since Streamlit's session_state isn't safe to touch from worker
    threads directly (see duckduckgo_search/bing_search docstrings)."""
    st.session_state["_search_diagnostics"] = []
    all_sources = []
    seen_urls = set()
    ddg_hits = 0

    queries = build_search_queries(question)
    STRONG_SCORE = 30
    STRONG_SOURCE_TARGET = 4

    # Instant Answer API first: single fast call, not HTML-scraping, so it
    # isn't affected by whatever is blocking html.duckduckgo.com/bing.com
    # from this host (see duckduckgo_instant_answer's docstring). Query
    # with the bare acronym when there is one — that's what makes its
    # RelatedTopics disambiguation list actually fire. Kept synchronous:
    # it's a single quick call and the acronym follow-up work below reads
    # its result.
    acro_for_ia = extract_acronym_candidate(question)
    ia_queries = [acro_for_ia] if acro_for_ia else [question]
    ia_hits = 0
    for ia_query in ia_queries:
        for source in duckduckgo_instant_answer(ia_query):
            if ia_hits >= 3:
                break
            url = source.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_sources.append(source)
                ia_hits += 1

    def strong_hit_count():
        return sum(
            1 for s in all_sources if source_score(s, question) >= STRONG_SCORE
        )

    # PARALLEL FETCH: prioritize the top 4 targeted queries with concurrency
    # to avoid rate-limiting or IP blocks while ensuring multi-entity coverage.
    search_queries = queries[:4]
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(6, max(len(search_queries) * 2, 1))
    ) as executor:
        future_map = {}
        for query in search_queries:
            future_map[executor.submit(wikipedia_search, query, 6)] = ("wiki", None)
            future_map[executor.submit(duckduckgo_search, query, 5)] = ("ddg", None)

        pending = set(future_map)
        for future in concurrent.futures.as_completed(future_map):
            pending.discard(future)
            kind, _ = future_map[future]

            try:
                result = future.result()
            except Exception:
                result = [] if kind == "wiki" else ([], None)

            if kind == "ddg":
                results, diag_entry = result
                ddg_hits += len(results)
                if diag_entry:
                    st.session_state["_search_diagnostics"].append(diag_entry)
            else:
                results = result

            for source in results:
                url = source.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_sources.append(source)

            # Early stop only if we've already collected plenty of sources
            if len(all_sources) >= 20:
                for p in pending:
                    p.cancel()
                break

    already_strong = strong_hit_count() >= STRONG_SOURCE_TARGET

    # DuckDuckGo scraping is fragile (UA blocks / markup drift) and fails
    # silently. If it contributed nothing across all queries, fall back to
    # a Bing HTML scrape (also parallelized) so evidence quality doesn't
    # quietly collapse to Wikipedia-only.
    if ddg_hits == 0 and not already_strong:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(4, max(len(queries[:4]), 1))
        ) as executor:
            futures = [executor.submit(bing_search, q, 5) for q in queries[:4]]
            for future in concurrent.futures.as_completed(futures):
                try:
                    results, diag_entry = future.result()
                except Exception:
                    results, diag_entry = [], None
                if diag_entry:
                    st.session_state["_search_diagnostics"].append(diag_entry)
                for source in results:
                    url = source.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_sources.append(source)

    # Direct disambiguation pull for short acronym-like entities (e.g.
    # "cbe"/"CBE"). Wikipedia's own disambiguation pages resolve these
    # cleanly without hardcoding any specific answer. Case-insensitive,
    # since most users type acronyms lowercase. Skipped once we already
    # have strong evidence — this was previously unconditional and could
    # add a dozen+ more Wikipedia requests for no benefit. Also run in
    # parallel now.
    acro = extract_acronym_candidate(question)
    if acro and not already_strong:
        context_words = extract_context_words(question, acro)
        ctx_query = (
            f'"{acro}" {" ".join(context_words[:3])}' if context_words else None
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            tasks = [
                ("wiki", executor.submit(wikipedia_search, f"{acro} (disambiguation)", 6)),
                ("wiki", executor.submit(wikipedia_search, acro, 6)),
            ]
            if ctx_query:
                tasks.append(("wiki", executor.submit(wikipedia_search, ctx_query, 4)))
                tasks.append(("ddg", executor.submit(duckduckgo_search, ctx_query, 4)))

            for kind, future in tasks:
                try:
                    result = future.result()
                except Exception:
                    result = [] if kind == "wiki" else ([], None)

                if kind == "ddg":
                    results, diag_entry = result
                    if diag_entry:
                        st.session_state["_search_diagnostics"].append(diag_entry)
                else:
                    results = result

                for source in results:
                    url = source.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_sources.append(source)

    # One extra exact Wikipedia lookup for short named entities.
    # This is still generic and does not hardcode answers. Also skipped
    # once we already have strong evidence.
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9.-]*", question)
    if len(words) <= 6 and not already_strong:
        exact = " ".join(w for w in words if w.lower() not in {
            "where", "is", "the", "in", "what", "which", "who", "how",
            "for", "of", "a", "an", "to", "me", "tell", "give", "does", "do"
        })
        if exact:
            for source in wikipedia_search(exact, limit=6):
                url = source.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_sources.append(source)

    st.session_state["_last_source_count"] = len(all_sources)
    st.session_state["_last_ddg_hits"] = ddg_hits
    st.session_state["_last_ia_hits"] = ia_hits

    all_sources.sort(
        key=lambda source: source_score(source, question),
        reverse=True,
    )

    return all_sources[:MAX_SOURCES]


# ============================================================
# EVIDENCE HELPERS
# ============================================================


def has_reliable_evidence(sources, question=None, min_relevance_score=8):
    """A source counts as reliable evidence if it has real content and meets
    a reasonable relevance score to the query, or if multiple non-empty sources
    were fetched."""
    if not sources:
        return False

    for source in sources:
        content = str(source.get("content", "")).strip()
        if len(content) < 60:
            continue
        if question is None:
            return True
        if source_score(source, question) >= min_relevance_score:
            return True

    # Generic fallback: if search returned multiple sources with substantial text,
    # allow the grounded generator to inspect them instead of blocking immediately
    substantial = [s for s in sources if len(str(s.get("content", "")).strip()) >= 80]
    if len(substantial) >= 2:
        return True

    return False


def build_evidence_pack(sources):
    parts = []
    total = 0

    for index, source in enumerate(sources, start=1):
        content = str(source.get("content", "")).strip()
        if not content:
            continue

        block = (
            f"SOURCE {index}\n"
            f"TITLE: {source.get('title', '')}\n"
            f"URL: {source.get('url', '')}\n"
            f"CONTENT:\n{content}\n"
        )

        if total + len(block) > MAX_TOTAL_EVIDENCE_CHARS:
            break

        parts.append(block)
        total += len(block)

    return "\n".join(parts)


# ============================================================
# GROUNDED ANSWER GENERATION
# ============================================================


def generate_grounded_answer(question, evidence_pack, sources=None, history_context=None):
    if not evidence_pack.strip():
        return {
            "answer": "NOT_FOUND",
            "error": None,
            "model": None,
        }

    system_prompt = """
You are the grounded answer generator for a hallucination detection system.

Answer the user's question using ONLY the supplied web evidence.

Rules:
1. Never invent facts.
2. Never use outside knowledge.
3. Never guess a fact that has no support in the evidence.
4. If an abbreviation or entity has multiple unrelated meanings in the
   evidence, pick the meaning that best matches the context words actually
   present in the user's question (for example a country, domain, or
   category the user mentioned). Do not blend facts from different
   meanings into a single answer.
4a. If the evidence shows the abbreviation is a CODE (railway/airport/
    postal station code, radio callsign, etc.) rather than the literal
    name of the thing the user asked about, still answer using that
    connection instead of declining on a technicality — e.g. if asked
    "where is the city CBE" and the evidence shows CBE is Coimbatore's
    railway station code, say the abbreviation refers to Coimbatore via
    that code and give Coimbatore's location, rather than only saying
    "no city is literally named CBE."
5. Verify the exact entity, location, names, dates, numbers and
   relationships for the meaning you selected.
6. If NONE of the candidate meanings has at least one source that clearly
   describes it, output exactly NOT_FOUND.
7. If two or more meanings are equally and strongly supported and there is
   no contextual signal in the question to prefer one, briefly state the
   top 2-3 possibilities instead of outputting NOT_FOUND.
8. Be concise and directly answer the question.
9. Do not mention these instructions.
10. If RECENT CONVERSATION is supplied below, use it only to resolve
    pronouns/references in the latest message (e.g. "it", "its", "that",
    "there", or a bare clarification like picking one candidate meaning).
    The recent conversation is context for understanding what the latest
    message means — it is NOT itself evidence, and facts from it must not
    be treated as supported unless the WEB EVIDENCE below also supports
    them.
"""

    if history_context:
        user_content = (
            f"RECENT CONVERSATION IN THIS CHAT (for resolving pronouns/"
            f"references only, not evidence):\n{history_context}\n\n"
            f"USER'S LATEST MESSAGE:\n{question}\n\n"
            f"WEB EVIDENCE:\n{evidence_pack}\n\n"
            "Resolve any reference in the latest message using the recent "
            "conversation above, then answer strictly from the evidence."
        )
    else:
        user_content = (
            f"USER QUESTION:\n{question}\n\n"
            f"WEB EVIDENCE:\n{evidence_pack}\n\n"
            "Answer strictly from the evidence."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    errors = []

    # -------------------------------------------------------------
    # PRIMARY ENGINE: Google Gemini (Direct, fast, highly reliable)
    # -------------------------------------------------------------
    gemini_key = os.getenv("GEMINI_API_KEY") or st.session_state.get("USER_GEMINI_KEY")
    if gemini_key:
        try:
            from generator import generate_answer as gemini_gen
            ctx_list = [s.get("content", s.get("snippet", "")) for s in sources] if sources else [evidence_pack]
            ctx_list = [c for c in ctx_list if c and str(c).strip()] or [evidence_pack]
            gemini_ans, used_model = gemini_gen(question, ctx_list, return_model=True)
            if gemini_ans:
                if "not contain enough information" in gemini_ans.lower() and len(gemini_ans) < 160:
                    return {
                        "answer": "NOT_FOUND",
                        "error": None,
                        "model": f"Google Gemini ({used_model})",
                    }
                st.session_state.last_successful_model = "Google Gemini"
                return {
                    "answer": gemini_ans,
                    "error": None,
                    "model": f"Google Gemini ({used_model})",
                }
        except Exception as g_exc:
            errors.append(f"Google Gemini: {g_exc}")

    # Fallback: OpenRouter community models
    dead_models = st.session_state.setdefault("_dead_models", set())
    models = [m for m in get_answer_models() if m not in dead_models]
    if not models:
        # Every known model is blacklisted (extremely unlikely) — fall
        # back to the unfiltered pool rather than failing outright.
        models = get_answer_models()
    start_index = st.session_state.get("answer_model_index", 0) % max(len(models), 1)

    # Remember the first model that explicitly said NOT_FOUND. That's only
    # returned as a last resort if every model either says NOT_FOUND or
    # fails outright — a NOT_FOUND from one model should not stop us from
    # trying the next one, since a different free model can (and often
    # does) find the answer in the same evidence.
    not_found_model = None

    # Cap attempts instead of looping through the entire live pool (which
    # can hold ~20 free models). Each attempt can also retry once with a
    # bigger token budget on an empty response, so trying every model in
    # sequence was the single biggest source of multi-minute latency.
    # 4 attempts is already generous fallback coverage.
    max_attempts = min(len(models), 4)

    for offset in range(max_attempts):
        index = (start_index + offset) % len(models)
        model = models[index]

        try:
            try:
                result = openrouter_request(
                    model=model,
                    messages=messages,
                    max_tokens=1200,
                    temperature=0.0,
                    extra_payload={"reasoning": {"effort": "none", "exclude": True}},
                )
            except RuntimeError as empty_exc:
                # Some models still burn the whole token budget on hidden
                # reasoning even with effort=none. Retry once with a bigger
                # budget and reasoning fully disabled before giving up.
                if "empty answer" not in str(empty_exc).lower():
                    raise
                result = openrouter_request(
                    model=model,
                    messages=messages,
                    max_tokens=1800,
                    temperature=0.0,
                    extra_payload={"reasoning": {"enabled": False}},
                )

            answer = result["content"].strip()

            # Models don't always follow "output exactly NOT_FOUND" to the
            # letter — some explain first, then append NOT_FOUND. An exact
            # equality check missed that case entirely, which let a
            # "couldn't find it" explanation slip through as a real answer
            # (and on to verification, where it just failed for unrelated
            # reasons instead of showing a clean NOT_FOUND). Treat any
            # short-ish response containing the sentinel as NOT_FOUND.
            if "NOT_FOUND" in answer.upper() and len(answer) < 400:
                # BUGFIX: this used to `return` immediately here, which
                # meant a single model saying NOT_FOUND killed the whole
                # request even though other free models hadn't been tried
                # yet. Now we just remember it and keep going.
                if not_found_model is None:
                    not_found_model = model
                errors.append(f"{model}: returned NOT_FOUND")
                continue

            st.session_state.last_successful_model = model
            st.session_state.answer_model_index = index

            return {
                "answer": answer,
                "error": None,
                "model": model,
            }

        except OpenRouterError as exc:
            errors.append(f"{model}: {exc}")
            if exc.status_code == 403 and "agentic harness" in str(exc.message).lower():
                # Permanent capability mismatch, not a transient failure —
                # this model will 403 the exact same way every time.
                dead_models.add(model)
            continue
        except Exception as exc:
            errors.append(f"{model}: {exc}")
            # A provider 429/404/5xx should immediately fall through to the
            # next free model rather than showing a generic pipeline failure.
            continue


    if not_found_model is not None:
        return {
            "answer": "NOT_FOUND",
            "error": None,
            "model": not_found_model,
        }

    return {
        "answer": None,
        "error": "All free answer models failed:\n" + "\n".join(errors),
        "model": None,
    }


# ============================================================
# VERIFIER JSON PARSING / VALIDATION
# ============================================================


def extract_json_object(content):
    if not isinstance(content, str):
        raise ValueError("Verifier output is not text.")

    content = content.strip()
    if not content:
        raise ValueError("Verifier returned empty output.")

    content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.I)
    content = re.sub(r"\s*```$", "", content, flags=re.I).strip()

    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
        raise ValueError("JSON root is not an object.")
    except json.JSONDecodeError:
        pass

    start = content.find("{")
    if start < 0:
        raise ValueError("No JSON object found in verifier output.")

    depth = 0
    in_string = False
    escape = False

    for i in range(start, len(content)):
        char = content[i]

        if escape:
            escape = False
            continue

        if char == "\\" and in_string:
            escape = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = content[start:i + 1]
                parsed = json.loads(candidate)
                if not isinstance(parsed, dict):
                    raise ValueError("JSON root is not an object.")
                return parsed

    raise ValueError("Could not find a complete JSON object.")


def validate_verifier_result(data):
    if not isinstance(data, dict):
        return {"valid": False, "result": None, "error": "Verifier JSON must be an object."}

    required = [
        "supported",
        "confidence",
        "claims_total",
        "claims_supported",
        "claims_unsupported",
        "reason",
        "unsupported_claims",
    ]

    missing = [key for key in required if key not in data]
    if missing:
        return {
            "valid": False,
            "result": None,
            "error": "Missing required field(s): " + ", ".join(missing),
        }

    supported = data["supported"]
    if not isinstance(supported, bool):
        return {"valid": False, "result": None, "error": "'supported' must be a boolean."}

    confidence = data["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return {"valid": False, "result": None, "error": "'confidence' must be a number."}
    confidence = float(confidence)
    if not 0.0 <= confidence <= 1.0:
        return {"valid": False, "result": None, "error": "'confidence' must be between 0 and 1."}

    counts = {}
    for key in ("claims_total", "claims_supported", "claims_unsupported"):
        value = data[key]
        if isinstance(value, bool) or not isinstance(value, int):
            return {"valid": False, "result": None, "error": f"'{key}' must be an integer."}
        if value < 0:
            return {"valid": False, "result": None, "error": f"'{key}' cannot be negative."}
        counts[key] = value

    if counts["claims_supported"] > counts["claims_total"]:
        return {"valid": False, "result": None, "error": "claims_supported cannot exceed claims_total."}

    if counts["claims_unsupported"] > counts["claims_total"]:
        return {"valid": False, "result": None, "error": "claims_unsupported cannot exceed claims_total."}

    if counts["claims_supported"] + counts["claims_unsupported"] > counts["claims_total"]:
        return {"valid": False, "result": None, "error": "Supported + unsupported claims cannot exceed total claims."}

    reason = data["reason"]
    if not isinstance(reason, str) or not reason.strip():
        return {"valid": False, "result": None, "error": "'reason' must be a non-empty string."}
    reason = reason.strip()[:2000]

    unsupported_claims = data["unsupported_claims"]
    if not isinstance(unsupported_claims, list):
        return {"valid": False, "result": None, "error": "'unsupported_claims' must be a list."}

    cleaned_claims = []
    for index, claim in enumerate(unsupported_claims):
        if not isinstance(claim, str):
            return {
                "valid": False,
                "result": None,
                "error": f"unsupported_claims item {index + 1} must be a string.",
            }
        claim = claim.strip()
        if claim:
            cleaned_claims.append(claim[:1000])

    if counts["claims_unsupported"] != len(cleaned_claims):
        return {
            "valid": False,
            "result": None,
            "error": "claims_unsupported does not match unsupported_claims length.",
        }

    if supported:
        if counts["claims_unsupported"] != 0:
            return {"valid": False, "result": None, "error": "supported cannot be true with unsupported claims."}
        if counts["claims_total"] > 0 and counts["claims_supported"] != counts["claims_total"]:
            return {"valid": False, "result": None, "error": "supported=true requires all claims to be supported."}
    elif counts["claims_total"] > 0 and counts["claims_unsupported"] == 0:
        return {"valid": False, "result": None, "error": "supported=false requires an unsupported claim."}

    result = {
        "supported": supported,
        "confidence": confidence,
        "claims_total": counts["claims_total"],
        "claims_supported": counts["claims_supported"],
        "claims_unsupported": counts["claims_unsupported"],
        "reason": reason,
        "unsupported_claims": cleaned_claims,
    }

    return {"valid": True, "result": result, "error": None}


def parse_and_validate_verifier(content):
    try:
        data = extract_json_object(content)
    except Exception as exc:
        return {
            "valid": False,
            "result": None,
            "error": f"Invalid verifier JSON: {exc}",
        }

    return validate_verifier_result(data)


# ============================================================
# INDEPENDENT VERIFICATION
# ============================================================


def build_verifier_messages(question, answer, sources):
    evidence = build_evidence_pack(sources)

    system_prompt = """
You are an independent hallucination verifier.

Determine whether the generated answer is fully supported by the supplied evidence.
Do NOT use outside knowledge.

If the question involves an abbreviation or entity with multiple unrelated
meanings, judge support against the meaning the answer actually selected —
do not mark a claim unsupported merely because the evidence also contains
other, unrelated meanings of the same term.

Return ONLY one JSON object with EXACTLY these fields:
{
  "supported": true,
  "confidence": 0.95,
  "claims_total": 1,
  "claims_supported": 1,
  "claims_unsupported": 0,
  "reason": "The answer is directly supported by the evidence.",
  "unsupported_claims": []
}

Rules:
- supported is a JSON boolean.
- confidence is a number from 0 to 1.
- claims_total, claims_supported and claims_unsupported are integers >= 0.
- supported claims + unsupported claims must not exceed total claims.
- claims_unsupported must equal the length of unsupported_claims.
- If supported is true, every claim must be supported.
- If supported is false and claims_total > 0, at least one claim must be unsupported.
- reason must be non-empty.
- Do not output markdown or commentary.
"""

    user_prompt = (
        f"QUESTION:\n{question}\n\n"
        f"GENERATED ANSWER:\n{answer}\n\n"
        f"EVIDENCE:\n{evidence}\n\n"
        "Verify strictly against the evidence."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def verify_answer(question, answer, sources):
    errors = []

    # -------------------------------------------------------------
    # PRIMARY VERIFIER: Google Gemini (Fast, structured, reliable)
    # -------------------------------------------------------------
    gemini_key = os.getenv("GEMINI_API_KEY") or st.session_state.get("USER_GEMINI_KEY")
    if gemini_key:
        try:
            from generator import get_client
            gem_client = get_client()
            evidence_str = "\n\n".join(
                f"Source {i+1} ({s.get('title', 'Web')}):\n{s.get('content', s.get('snippet', ''))}"
                for i, s in enumerate(sources)
            )
            g_prompt = (
                "You are an independent hallucination verifier.\n\n"
                "Determine whether the generated answer is fully supported by the supplied evidence.\n"
                "Do NOT use outside knowledge.\n\n"
                "Return ONLY one JSON object with EXACTLY these fields:\n"
                "{\n"
                '  "supported": true,\n'
                '  "confidence": 0.95,\n'
                '  "claims_total": 1,\n'
                '  "claims_supported": 1,\n'
                '  "claims_unsupported": 0,\n'
                '  "reason": "The answer is directly supported by the evidence.",\n'
                '  "unsupported_claims": []\n'
                "}\n\n"
                f"QUESTION:\n{question}\n\n"
                f"GENERATED ANSWER:\n{answer}\n\n"
                f"EVIDENCE:\n{evidence_str}\n\n"
                "Verify strictly against the evidence."
            )
            for cand in ["gemini-3.5-flash-lite", "gemini-3.8-flash"]:
                for v_attempt in range(2):
                    try:
                        resp = gem_client.models.generate_content(
                            model=cand,
                            contents=g_prompt,
                            config={"response_mime_type": "application/json"}
                        )
                        if resp.text:
                            parsed = parse_and_validate_verifier(resp.text)
                            if parsed["valid"]:
                                return {
                                    **parsed["result"],
                                    "available": True,
                                    "model": f"Google Gemini ({cand})",
                                    "error": None,
                                }
                    except Exception as cand_exc:
                        errors.append(f"{cand}: {cand_exc}")
                        err_str = str(cand_exc).lower()
                        if ("503" in err_str or "unavailable" in err_str or "429" in err_str or "quota" in err_str) and v_attempt == 0:
                            time.sleep(1.0)
                            continue
                        break
        except Exception as g_exc:
            errors.append(f"Gemini verifier: {g_exc}")

    # Fallback: OpenRouter verifier pool
    dead_models = st.session_state.setdefault("_dead_models", set())
    verifier_models = [m for m in get_verifier_models() if m not in dead_models]
    if not verifier_models:
        verifier_models = get_verifier_models()

    preferred = []
    answer_model = st.session_state.get("last_successful_model")
    for model in verifier_models:
        if model != answer_model:
            preferred.append(model)
    if not preferred:
        preferred = list(verifier_models)

    # Cap instead of trying the whole pool — up to ~19 models × 2 modes
    # (JSON + plain fallback) each was another major source of multi-
    # minute latency when several free models were slow or rate-limited.
    preferred = preferred[:2]

    for verifier_model in preferred:
        # Prefer a different free model from the answer generator so the
        # verification is genuinely independent when possible.
        # A 429 is not retried immediately because that only burns quota.
        try:
            response = openrouter_request(
                model=verifier_model,
                messages=messages,
                max_tokens=900,
                temperature=0.0,
                response_format={"type": "json_object"},
                extra_payload={"reasoning": {"effort": "none"}},
            )
            parsed = parse_and_validate_verifier(response["content"])

            if parsed["valid"]:
                result = parsed["result"]
                return {
                    **result,
                    "available": True,
                    "model": verifier_model,
                    "error": None,
                }

            errors.append(
                f"{verifier_model} (JSON mode): {parsed['error']}"
            )

        except OpenRouterError as exc:
            errors.append(str(exc))
            if exc.status_code == 403 and "agentic harness" in str(exc.message).lower():
                dead_models.add(verifier_model)
                continue
            # Do not burn another request on a rate-limit response.
            if exc.status_code == 429:
                continue
        except Exception as exc:
            errors.append(f"{verifier_model} (JSON mode): {exc}")

        # Plain-mode fallback is only used after a non-rate-limit failure,
        # such as a provider rejecting response_format.
        try:
            response = openrouter_request(
                model=verifier_model,
                messages=messages,
                max_tokens=900,
                temperature=0.0,
                response_format=None,
                extra_payload={"reasoning": {"effort": "none"}},
            )
            parsed = parse_and_validate_verifier(response["content"])

            if parsed["valid"]:
                result = parsed["result"]
                return {
                    **result,
                    "available": True,
                    "model": verifier_model,
                    "error": None,
                }

            errors.append(
                f"{verifier_model} (plain mode): {parsed['error']}"
            )

        except OpenRouterError as exc:
            errors.append(str(exc))
        except Exception as exc:
            errors.append(f"{verifier_model} (plain mode): {exc}")


    # Automatic fallback 2: if all LLM verifiers failed/rate-limited,
    # use local DeBERTa NLI + XGBoost V2 so the user is never left without verification.
    try:
        raw_ctx = [
            s.get("content", s.get("snippet", ""))
            for s in sources
            if s.get("content") or s.get("snippet")
        ]
        if raw_ctx:
            local_v = verify_answer_local_ml(question, answer, raw_ctx)
            if local_v.get("available"):
                local_v["reason"] += " (OpenRouter was busy/rate-limited; verified via local DeBERTa+XGBoost)."
                return local_v
    except Exception:
        pass

    return {
        "supported": False,
        "confidence": 0.0,
        "claims_total": 0,
        "claims_supported": 0,
        "claims_unsupported": 0,
        "reason": "All verifier attempts failed.",
        "unsupported_claims": [],
        "available": False,
        "model": None,
        "error": "\n".join(errors),
    }


# ============================================================
# LOCAL ML VERIFICATION (DeBERTa NLI + XGBoost V2)
# ============================================================

@st.cache_resource(show_spinner="Loading SQuAD knowledge base & embeddings...")
def get_cached_squad_retriever():
    try:
        from retrieve import retrieve
        return retrieve
    except Exception:
        return lambda q, top_k=3: []


@st.cache_resource(show_spinner="Loading local NLI CrossEncoder & XGBoost detector...")
def get_cached_local_ml():
    import joblib
    from sentence_transformers import SentenceTransformer
    detector_path = os.path.join(BASE_DIR, "hallucination_model_v2.pkl")
    xgb_detector = joblib.load(detector_path)
    mini_encoder = SentenceTransformer("all-MiniLM-L6-v2")
    return xgb_detector, mini_encoder


def verify_answer_local_ml(question, answer, contexts):
    try:
        from pipeline import verify_with_local_ml
        xgb_detector, mini_encoder = get_cached_local_ml()

        knowledge = "\n\n".join(contexts) if isinstance(contexts, list) else str(contexts)
        ctx_list = contexts if isinstance(contexts, list) else [knowledge]

        result = verify_with_local_ml(
            knowledge=knowledge,
            question=question,
            answer=answer,
            contexts=ctx_list,
            custom_detector=xgb_detector,
            custom_encoder=mini_encoder,
        )

        is_verified = bool(result["verified"])
        return {
            "verifier_type": "local_ml",
            "available": True,
            "supported": is_verified,
            "confidence": float(result["confidence"]) / 100.0,
            "entailment": float(result["entailment"]),
            "contradiction": float(result["contradiction"]),
            "neutral": float(result["neutral"]),
            "xgb_verified": bool(result["xgb_verified"]),
            "xgb_confidence": float(result["xgb_confidence"]),
            "claims_total": 1,
            "claims_supported": 1 if is_verified else 0,
            "claims_unsupported": 0 if is_verified else 1,
            "reason": (
                f"Local ML ensemble verdict: {'VERIFIED' if is_verified else 'HALLUCINATION DETECTED'}. "
                f"DeBERTa Entailment: {result['entailment']:.1f}%, XGBoost V2 Faithfulness: {result['xgb_confidence']:.1f}%."
            ),
            "unsupported_claims": (
                [] if is_verified
                else ["Claim is not sufficiently entailed by evidence according to DeBERTa NLI and XGBoost V2."]
            ),
            "model": "DeBERTa-v3-NLI + XGBoost-V2 Ensemble",
            "error": None,
        }
    except Exception as exc:
        return {
            "verifier_type": "local_ml",
            "available": False,
            "supported": False,
            "confidence": 0.0,
            "claims_total": 0,
            "claims_supported": 0,
            "claims_unsupported": 0,
            "reason": f"Local ML verification error: {exc}",
            "unsupported_claims": [],
            "model": "DeBERTa-v3-NLI + XGBoost-V2",
            "error": str(exc),
        }


# ============================================================
# MODEL ROTATION
# ============================================================


def current_model():
    models = get_answer_models()
    index = st.session_state.get("answer_model_index", 0)
    if not 0 <= index < len(models):
        index = 0
        st.session_state.answer_model_index = 0
    return models[index]


def rotate_model():
    models = get_answer_models()
    st.session_state.answer_model_index = (
        st.session_state.get("answer_model_index", 0) + 1
    ) % max(len(models), 1)


# ============================================================
# FOLLOW-UP DETECTION
# ============================================================
# Each question is otherwise processed with zero conversation context, so a
# low-content clarification like "uhm im telling a city" free-searches on
# filler words and pulls back unrelated evidence. If a message carries
# almost no searchable content of its own, treat it as clarifying the
# previous question instead of a new standalone one.

FOLLOWUP_STOPWORDS = {
    "i", "im", "i'm", "am", "is", "are", "the", "a", "an", "to", "it",
    "that", "this", "one", "uhm", "um", "uh", "telling", "mean", "meant",
    "meaning", "said", "say", "about", "you", "your", "tell", "please",
    "no", "yes", "like", "just", "actually", "well", "so",
}
GENERIC_CATEGORY_WORDS = {
    "city", "place", "country", "state", "location", "district",
    "name", "word", "number", "date", "year", "town",
}


def is_low_info_followup(question):
    tokens = re.findall(r"[a-z0-9']+", question.lower())
    important = [
        t for t in tokens
        if t not in FOLLOWUP_STOPWORDS and len(t) > 2
    ]
    meaningful = [t for t in important if t not in GENERIC_CATEGORY_WORDS]
    has_proper_noun = bool(re.search(r"\b[A-Z][a-z0-9]{2,}\b", question))
    return not meaningful and not has_proper_noun


# CHAT MEMORY: the app previously had none — each question was processed
# with zero awareness of earlier turns in the same chat, so "what's its
# population?" after "where is Coimbatore?" had no way to resolve "its".
# The only prior mechanism (FOLLOWUP_STOPWORDS/is_low_info_followup above)
# only caught near-empty clarifications, not ordinary pronoun references.
PRONOUN_PATTERN = re.compile(
    r"\b(it|its|it's|that|this|they|their|them|those|these|there|"
    r"he|she|him|her|his|hers)\b",
    re.I,
)

MAX_CONTEXT_EXCHANGES = 3


def needs_conversation_context(question):
    """True when the question likely depends on earlier turns — either a
    pronoun/reference ("its", "that", "there"...) or the existing
    near-empty-clarification heuristic."""
    return bool(PRONOUN_PATTERN.search(question)) or is_low_info_followup(question)


def get_recent_exchanges(conversation, limit=MAX_CONTEXT_EXCHANGES):
    """Pull the last few real Q&A pairs from this conversation, oldest
    first, to use as short-term memory. Casual replies ("hey! 👋") and
    errored/empty turns are skipped since they add no useful context and
    would just waste tokens in the prompt."""
    exchanges = []
    pending_question = None

    for msg in conversation.get("messages", []):
        role = msg.get("role")
        if role == "user":
            pending_question = msg.get("content", "")
        elif role == "assistant" and pending_question is not None:
            status = msg.get("status")
            answer_text = msg.get("content", "")
            if status not in ("casual", "error") and answer_text:
                exchanges.append({
                    "question": pending_question,
                    "answer": answer_text,
                })
            pending_question = None

    return exchanges[-limit:]


# ============================================================
# MAIN PIPELINE
# ============================================================


def process_question(
    question,
    history=None,
    pipeline_mode="Web Search + OpenRouter LLM Verifier",
    progress_callback=None,
):
    history = history or []

    def notify(step):
        if progress_callback:
            try:
                progress_callback(step)
            except Exception:
                pass

    # Casual messages skip the full search+verify pipeline.
    casual = casual_response(question)
    if casual:
        notify("✨ Responding...")
        return {
            "answer": casual,
            "status": "casual",
            "sources": [],
            "verification": None,
            "error": None,
            "answer_model": None,
        }

    # ========================================================
    # MODE 2: LOCAL SQUAD KNOWLEDGE BASE + DeBERTa NLI + XGBoost V2
    # ========================================================
    if pipeline_mode == "Local SQuAD + DeBERTa NLI + XGBoost V2":
        notify("📚 Retrieving knowledge from SQuAD dataset...")
        try:
            squad_retrieve = get_cached_squad_retriever()
            retrieved = squad_retrieve(question, top_k=3)
        except Exception as exc:
            return {
                "answer": None,
                "status": "error",
                "sources": [],
                "verification": None,
                "error": f"Local SQuAD retrieval failed: {exc}",
                "answer_model": "Local SQuAD Retriever",
            }

        if not retrieved:
            notify("? No matching SQuAD records found")
            return {
                "answer": "NOT_FOUND",
                "status": "not_found",
                "sources": [],
                "verification": None,
                "error": None,
                "answer_model": "Local SQuAD Retriever",
            }

        notify(f"📚 Found {len(retrieved)} SQuAD evidence contexts")
        contexts = [r["context"] for r in retrieved]
        sources = [
            {
                "title": r.get("title", "SQuAD Document"),
                "context": r.get("context", ""),
                "similarity": r.get("similarity", 0.0),
                "score": r.get("score", 0.0),
                "url": "",
                "snippet": r.get("context", "")[:250],
            }
            for r in retrieved
        ]

        # Generate answer: try Gemini first if key available, else OpenRouter
        notify("✨ Generating grounded answer...")
        answer = None
        answer_model = None
        if os.getenv("GEMINI_API_KEY"):
            try:
                from generator import generate_answer
                answer = generate_answer(question, contexts)
                answer_model = "Google Gemini"
            except Exception:
                answer = None

        if not answer:
            evidence_pack = "\n\n".join(
                f"Source {i+1} ({r.get('title', 'Evidence')}):\n{r.get('context', '')}"
                for i, r in enumerate(retrieved)
            )
            generated = generate_grounded_answer(
                question,
                evidence_pack,
                sources,
            )
            if generated.get("error"):
                return {
                    "answer": None,
                    "status": "error",
                    "sources": sources,
                    "verification": None,
                    "error": generated["error"],
                    "answer_model": None,
                }
            answer = generated["answer"]
            answer_model = generated.get("model")

        if answer == "NOT_FOUND":
            return {
                "answer": "NOT_FOUND",
                "status": "not_found",
                "sources": sources,
                "verification": None,
                "error": None,
                "answer_model": answer_model,
            }

        notify("🛡️ Verifying answer with DeBERTa NLI & XGBoost...")
        verification = verify_answer_local_ml(question, answer, contexts)
        status = "verified" if verification.get("supported") else "not_verified"
        if not verification.get("available"):
            status = "verification_unavailable"

        notify("✓ Complete" if status == "verified" else "✓ Verification complete")
        return {
            "answer": answer,
            "status": status,
            "sources": sources,
            "verification": verification,
            "error": None,
            "answer_model": answer_model,
        }

    # ========================================================
    # MODE 1 & 3: WEB SEARCH RETRIEVAL (Web LLM or Hybrid ML)
    # ========================================================
    history_context = None
    search_question = question

    if history and needs_conversation_context(question):
        last = history[-1]
        prev_answer_snippet = str(last.get("answer", ""))[:200]
        prev_question = last.get("question", "")
        search_question = f"{prev_answer_snippet} {prev_question} {question}"

        lines = []
        for exchange in history[-MAX_CONTEXT_EXCHANGES:]:
            lines.append(f"Q: {exchange.get('question', '')}")
            lines.append(f"A: {str(exchange.get('answer', ''))[:300]}")
        history_context = "\n".join(lines)

    # --------------------------------------------------------
    # FREE WEB GROUNDING
    # --------------------------------------------------------
    notify("🔎 Searching web sources...")
    try:
        sources = free_web_search(search_question)
    except Exception as exc:
        return {
            "answer": None,
            "status": "error",
            "sources": [],
            "verification": None,
            "error": f"Free web search failed: {exc}",
            "answer_model": None,
        }

    if not has_reliable_evidence(sources, search_question):
        notify("? Insufficient reliable evidence found")
        return {
            "answer": "NOT_FOUND",
            "status": "not_found",
            "sources": sources,
            "verification": None,
            "error": None,
            "answer_model": None,
        }

    notify(f"📚 Evidence found ({len(sources)} sources)")
    evidence_pack = build_evidence_pack(sources)

    # --------------------------------------------------------
    # GROUNDED ANSWER + FREE MODEL FALLBACK
    # --------------------------------------------------------
    notify("✨ Generating answer...")
    generated = generate_grounded_answer(
        question,
        evidence_pack,
        sources,
        history_context=history_context,
    )

    if generated["error"]:
        return {
            "answer": None,
            "status": "error",
            "sources": sources,
            "verification": None,
            "error": generated["error"],
            "answer_model": None,
        }

    answer = generated["answer"]
    answer_model = generated.get("model")

    if answer == "NOT_FOUND":
        return {
            "answer": "NOT_FOUND",
            "status": "not_found",
            "sources": sources,
            "verification": None,
            "error": None,
            "answer_model": answer_model,
        }

    # --------------------------------------------------------
    # VERIFICATION: Local ML (Hybrid) or OpenRouter LLM
    # --------------------------------------------------------
    notify("🛡️ Verifying answer against evidence...")
    if pipeline_mode == "Hybrid (Web Search + Local ML Verifier)":
        web_contexts = [
            s.get("content", s.get("snippet", ""))
            for s in sources
            if s.get("content") or s.get("snippet")
        ]
        verification = verify_answer_local_ml(question, answer, web_contexts)
    else:
        verification = verify_answer(
            question,
            answer,
            sources,
        )

    if not verification["available"]:
        notify("✓ Complete (Verifier offline)")
        return {
            "answer": answer,
            "status": "verification_unavailable",
            "sources": sources,
            "verification": verification,
            "error": None,
            "answer_model": answer_model,
        }

    if verification["supported"]:
        status = "verified"
        notify("✓ Verified")
    else:
        status = "not_verified"
        notify("⚠ Verification complete")

    return {
        "answer": answer,
        "status": status,
        "sources": sources,
        "verification": verification,
        "error": None,
        "answer_model": answer_model,
    }



# ============================================================
# DISPLAY HELPERS & VERIFICATION CARDS
# ============================================================


def render_user_message(content):
    escaped = html.escape(str(content)).replace("\n", "<br>")
    st.markdown(
        f'''<div class="user-msg-row">
            <div class="user-msg-bubble">
                {escaped}
            </div>
        </div>''',
        unsafe_allow_html=True,
    )


def render_verification_card(status, verification=None):
    if not status or status == "casual":
        return

    if status == "verified":
        conf_html = ""
        if verification and verification.get("confidence") is not None:
            conf_val = verification.get("confidence", 0)
            conf_html = f'<span class="verif-tag">{conf_val:.0%} verified</span>'

        card_html = f'''
        <div class="verif-card verif-card-verified">
            <div class="verif-card-header">
                <span class="verif-card-icon">🛡️</span>
                <div class="verif-card-title-group">
                    <span class="verif-card-title">Verified</span>
                    <span class="verif-card-desc">Supported by available evidence</span>
                </div>
                {conf_html}
            </div>
        </div>
        '''
        st.markdown(card_html, unsafe_allow_html=True)

    elif status == "not_verified":
        supp_c = verification.get("claims_supported", 0) if verification else 0
        total_c = verification.get("claims_total", 0) if verification else 0

        if supp_c > 0:
            tag_html = f'<span class="verif-tag">{supp_c}/{total_c} claims verified</span>' if total_c else ""
            card_html = f'''
            <div class="verif-card verif-card-partial">
                <div class="verif-card-header">
                    <span class="verif-card-icon">⚠️</span>
                    <div class="verif-card-title-group">
                        <span class="verif-card-title">Partially Supported</span>
                        <span class="verif-card-desc">Some claims could not be independently verified</span>
                    </div>
                    {tag_html}
                </div>
            </div>
            '''
            st.markdown(card_html, unsafe_allow_html=True)
        else:
            card_html = '''
            <div class="verif-card verif-card-unsupported">
                <div class="verif-card-header">
                    <span class="verif-card-icon">✕</span>
                    <div class="verif-card-title-group">
                        <span class="verif-card-title">Not Supported</span>
                        <span class="verif-card-desc">Available evidence contradicts or does not support the answer</span>
                    </div>
                </div>
            </div>
            '''
            st.markdown(card_html, unsafe_allow_html=True)

    elif status == "not_found":
        card_html = '''
        <div class="verif-card verif-card-unable">
            <div class="verif-card-header">
                <span class="verif-card-icon">🔍</span>
                <div class="verif-card-title-group">
                    <span class="verif-card-title">Unable to Verify</span>
                    <span class="verif-card-desc">Insufficient evidence found</span>
                </div>
            </div>
        </div>
        '''
        st.markdown(card_html, unsafe_allow_html=True)

    elif status == "verification_unavailable":
        card_html = '''
        <div class="verif-card verif-card-unable">
            <div class="verif-card-header">
                <span class="verif-card-icon">🔧</span>
                <div class="verif-card-title-group">
                    <span class="verif-card-title">Unable to Verify</span>
                    <span class="verif-card-desc">Verification service temporarily offline</span>
                </div>
            </div>
        </div>
        '''
        st.markdown(card_html, unsafe_allow_html=True)


def render_status(status, verification=None):
    render_verification_card(status, verification)


def render_verification_details(verification):
    if not verification:
        return

    if verification.get("available"):
        with st.expander("🔬 Verification Analysis & Diagnostics"):
            model_name = verification.get("model") or "Independent Verifier"
            conf = verification.get("confidence", 0)

            st.markdown(
                f'<div style="font-size: 0.85rem; color: #8B949E; margin-bottom: 0.6rem;">'
                f'Evaluated by <b style="color: #F0F6FC;">{html.escape(str(model_name))}</b>'
                f'</div>',
                unsafe_allow_html=True,
            )

            if verification.get("verifier_type") == "local_ml":
                ent = verification.get("entailment", 0)
                contra = verification.get("contradiction", 0)
                neu = verification.get("neutral", 0)
                xgb = verification.get("xgb_confidence", 0)

                metrics_html = f'''
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="metric-card-label">DeBERTa Entailment</div>
                        <div class="metric-card-val" style="color: #34D399;">{ent:.1f}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-card-label">Contradiction</div>
                        <div class="metric-card-val" style="color: #F87171;">{contra:.1f}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-card-label">XGBoost Faithfulness</div>
                        <div class="metric-card-val" style="color: #58A6FF;">{xgb:.1f}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-card-label">Neutral / Ambiguous</div>
                        <div class="metric-card-val" style="color: #8B949E;">{neu:.1f}%</div>
                    </div>
                </div>
                '''
                st.markdown(metrics_html, unsafe_allow_html=True)
            else:
                total_c = verification.get("claims_total", 0)
                supp_c = verification.get("claims_supported", 0)
                unsupp_c = verification.get("claims_unsupported", 0)

                metrics_html = f'''
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="metric-card-label">Confidence</div>
                        <div class="metric-card-val" style="color: #34D399;">{conf:.0%}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-card-label">Total Claims</div>
                        <div class="metric-card-val" style="color: #C9D1D9;">{total_c}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-card-label">Supported</div>
                        <div class="metric-card-val" style="color: #34D399;">{supp_c}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-card-label">Unsupported</div>
                        <div class="metric-card-val" style="color: #F87171;">{unsupp_c}</div>
                    </div>
                </div>
                '''
                st.markdown(metrics_html, unsafe_allow_html=True)

            reason = verification.get("reason", "")
            if reason:
                st.markdown(
                    f'<div style="background: rgba(22, 27, 34, 0.8); border-left: 3px solid #58A6FF; padding: 0.65rem 0.95rem; border-radius: 8px; font-size: 0.86rem; color: #C9D1D9; margin-top: 0.6rem;">'
                    f'<b>Verification Verdict:</b> {html.escape(reason)}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            unsupported = verification.get("unsupported_claims", [])
            if unsupported:
                st.markdown('<div style="color: #F87171; font-weight: 600; margin-top: 0.6rem; font-size: 0.86rem;">Flagged Unsupported Claims:</div>', unsafe_allow_html=True)
                for claim in unsupported:
                    st.markdown(f'<div style="padding-left: 1rem; color: #FCA5A5; font-size: 0.84rem;">• {html.escape(claim)}</div>', unsafe_allow_html=True)
    else:
        error = verification.get("error")
        if error:
            with st.expander("🔧 Verifier Diagnostics"):
                st.code(error, language="text")


def render_verification(verification):
    render_verification_details(verification)


def render_sources(sources):
    if not sources:
        return

    with st.expander(f"🌐 Sources & Evidence ({len(sources)})"):
        for index, source in enumerate(sources, start=1):
            raw_title = str(source.get("title", source.get("url", f"Source {index}")))
            title = html.escape(raw_title)
            url = source.get("url", "")
            context = source.get("context") or source.get("content") or source.get("snippet", "")
            similarity = source.get("similarity")

            domain = ""
            if url:
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc.replace("www.", "")
                except Exception:
                    domain = ""
            badge_text = domain if domain else f"Source {index}"

            card_html = f'''
            <div class="citation-card">
                <div class="citation-header">
                    <span class="citation-badge">{html.escape(badge_text[:28])}</span>
                    <span class="citation-title" title="{title}">{title}</span>
            '''
            if url:
                safe_url = html.escape(url, quote=True)
                card_html += f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer" class="citation-link">Open Source ↗</a>'
            card_html += '</div>'

            if similarity is not None:
                card_html += f'<div style="font-size: 0.74rem; color: #6E7681; margin-bottom: 0.25rem;">Relevance Score: {similarity:.4f}</div>'

            if context:
                snippet = html.escape(context[:280] + ("..." if len(context) > 280 else ""))
                card_html += f'<div class="citation-snippet">"{snippet}"</div>'

            card_html += '</div>'
            st.markdown(card_html, unsafe_allow_html=True)


def render_assistant_content(content, status):
    if status == "not_found" or (isinstance(content, str) and (content.strip().startswith("❌ **NOT FOUND**") or content.strip() == "NOT_FOUND")):
        st.markdown(
            '''<div class="insufficient-evidence-card">
                <div class="insufficient-evidence-icon">🔍</div>
                <div>
                    <div class="insufficient-evidence-title">Insufficient Reliable Evidence</div>
                    <p class="insufficient-evidence-desc">
                        The system searched for evidence but could not find enough reliable sources to confirm or refute this answer. To prevent misinformation, no unverified claims are presented as fact.
                    </p>
                </div>
            </div>''',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(content)


def render_message_details(message):
    status = message.get("status")
    verification = message.get("verification")
    render_verification_card(status, verification)
    render_verification_details(verification)
    render_sources(message.get("sources", []))


def format_user_friendly_error(err_msg):
    if not err_msg:
        return "An unexpected error occurred while verifying evidence. Please try again."
    err_str = str(err_msg).lower()
    if "429" in err_str or "rate limit" in err_str:
        return "Rate limit reached. Automatically switching to fallback provider..."
    if "all free answer models failed" in err_str or "all providers" in err_str:
        return "All AI providers are currently busy. Please wait a moment and try again."
    if "no reliable web sources" in err_str or "search failed" in err_str:
        return "No reliable web sources found for this query. Try rephrasing or asking a more specific question."
    clean_err = re.sub(r'File ".*?", line \d+.*', '', str(err_msg), flags=re.S).strip()
    return clean_err[:220] if clean_err else "An error occurred during evidence retrieval. Please try again."


# ============================================================
# PIPELINE CONFIG & EXPORT HELPERS
# ============================================================

PIPELINE_MODE_MAP = {
    "🌐 Real-Time Web Grounding (Live Fact-Checking)": "Web Search + OpenRouter LLM Verifier",
    "🔬 Hybrid Verification (Dual-Layer NLI + XGBoost)": "Hybrid (Web Search + Local ML Verifier)",
    "📚 Academic Knowledge Base (Pre-trained ML)": "Local SQuAD + DeBERTa NLI + XGBoost V2",
}


def generate_chat_export(conv):
    title = conv.get("title", "Hallucination Detector Report")
    lines = [
        f"# {title}",
        f"*Exported from Hallucination Detector on {now_iso()}*",
        "",
        "---",
        "",
    ]
    for m in conv.get("messages", []):
        role = m.get("role")
        content = m.get("content", "")
        if role == "user":
            lines.append(f"### 👤 Question\n{content}\n")
        elif role == "assistant":
            status = m.get("status", "unknown")
            badge = "✅ Verified" if status == "verified" else ("⚠️ Partially Supported" if status == "not_verified" else "🔍 Unable to Verify")
            lines.append(f"### 🛡️ Answer ({badge})\n")
            if status == "not_found":
                lines.append("> *The system searched for evidence but could not find enough reliable sources to confirm or refute this answer.*\n")
            else:
                lines.append(f"{content}\n")
            ver = m.get("verification")
            if ver and ver.get("available"):
                conf = ver.get("confidence", 0)
                reason = ver.get("reason", "")
                lines.append(f"- **Verification Confidence:** {conf:.0%}")
                if reason:
                    lines.append(f"- **Analysis:** {reason}")
                lines.append("")
            sources = m.get("sources", [])
            if sources:
                lines.append("#### Sources & Evidence:")
                for i, s in enumerate(sources, 1):
                    t = s.get("title", f"Source {i}")
                    u = s.get("url", "")
                    if u:
                        lines.append(f"{i}. [{t}]({u})")
                    else:
                        lines.append(f"{i}. {t}")
                lines.append("")
            lines.append("---\n")
    return "\n".join(lines)


# ============================================================
# AUTHENTICATION & ACCESS CONTROL GATE
# ============================================================

def render_auth_screen():
    st.markdown(
        '''<div class="claude-hero-container" style="margin-top: 1.8rem; margin-bottom: 1.4rem;">
            <div class="claude-hero-icon">🛡️</div>
            <h1 class="claude-hero-title">Hallucination Detector</h1>
            <p class="claude-hero-subtitle">
                Sign in with your User ID to resume saved research sessions, verify claims against live web sources, and prevent AI hallucinations.
            </p>
        </div>''',
        unsafe_allow_html=True,
    )

    if st.session_state.get("auth_block_message"):
        st.error(st.session_state.pop("auth_block_message"))

    _, col_auth, _ = st.columns([1, 2.2, 1])
    with col_auth:
        tab_login, tab_register = st.tabs(["🔐 Sign In", "✨ Create Account"])

        with tab_login:
            with st.form("form_login", clear_on_submit=False):
                st.markdown("#### Welcome Back")
                l_user = st.text_input("User ID / Username", placeholder="e.g. admin or your username", key="login_username_field")
                l_pass = st.text_input("Password", type="password", placeholder="••••••••", key="login_password_field")
                btn_login = st.form_submit_button("Sign In ➔", type="primary", use_container_width=True)

                if btn_login:
                    ok, msg, user_dict = authenticate_user(l_user, l_pass)
                    if ok:
                        st.session_state.authenticated_user = user_dict
                        user_id = user_dict["id"]
                        saved = load_user_saved_conversations(user_id)
                        if not saved and user_dict.get("is_admin") and os.path.exists(CHAT_HISTORY_FILE):
                            try:
                                old_raw = load_json(CHAT_HISTORY_FILE, [])
                                if old_raw and isinstance(old_raw, list):
                                    for item in old_raw:
                                        norm = normalize_conversation(item)
                                        save_user_conversation(user_id, norm)
                                    saved = load_user_saved_conversations(user_id)
                            except Exception:
                                pass
                        if not saved:
                            new_c = create_conversation()
                            save_user_conversation(user_id, new_c)
                            saved = [new_c]
                        st.session_state.conversations = saved
                        st.session_state.current_conversation_id = saved[0]["id"]
                        st.success(f"Welcome back, {user_dict['username']}!")
                        time.sleep(0.3)
                        st.rerun()
                    else:
                        st.error(msg)

            st.markdown(
                '''<div style="margin-top: 1rem; padding: 0.75rem 0.9rem; background: rgba(255,255,255,0.03); border-radius: 8px; border: 1px solid rgba(255,255,255,0.06); font-size: 0.78rem; color: #8B949E; line-height: 1.5;">
                    🔑 <b>Default Administrator Account:</b><br/>
                    User ID: <code style="color: #DA7756; font-size: 0.82rem;">admin</code> &nbsp;•&nbsp; Password: <code style="color: #DA7756; font-size: 0.82rem;">admin123</code><br/>
                    <span style="font-size: 0.72rem; color: #6E7681;">Administrators can monitor all user accounts and block or unblock users.</span>
                </div>''',
                unsafe_allow_html=True,
            )

        with tab_register:
            with st.form("form_register", clear_on_submit=False):
                st.markdown("#### Create New Account")
                st.caption("Sign up for free to save your chat sessions and verified claims.")
                r_user = st.text_input("Choose User ID", placeholder="Letters, numbers, hyphens, underscores (3-30 chars)", key="reg_username_field")
                r_pass = st.text_input("Create Password", type="password", placeholder="At least 4 characters", key="reg_password_field")
                r_pass_conf = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="reg_password_conf_field")
                btn_reg = st.form_submit_button("Create Account & Sign In ➔", type="primary", use_container_width=True)

                if btn_reg:
                    if not r_user.strip() or not r_pass.strip():
                        st.error("Please fill in all fields.")
                    elif r_pass != r_pass_conf:
                        st.error("Passwords do not match. Please verify your password.")
                    else:
                        ok, msg = register_user(r_user, r_pass)
                        if ok:
                            ok_l, msg_l, user_dict = authenticate_user(r_user, r_pass)
                            if ok_l:
                                st.session_state.authenticated_user = user_dict
                                new_c = create_conversation()
                                save_user_conversation(user_dict["id"], new_c)
                                st.session_state.conversations = [new_c]
                                st.session_state.current_conversation_id = new_c["id"]
                                st.success(f"Welcome, {r_user}! Your account has been created.")
                                time.sleep(0.3)
                                st.rerun()
                            else:
                                st.success("Account created successfully! Please sign in with your credentials.")
                        else:
                            st.error(msg)


if st.session_state.get("authenticated_user") is None:
    with st.sidebar:
        st.markdown(
            '''<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.8rem;">
                <div style="font-weight: 800; font-size: 1.15rem; color: #F0F6FC; display: flex; align-items: center; gap: 0.5rem;">
                    <span>🛡️ Hallucination Detector</span>
                </div>
                <span style="font-size: 0.7rem; font-weight: 700; color: #34D399; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); padding: 0.15rem 0.5rem; border-radius: 9999px;">v3.0</span>
            </div>
            <div style="font-size: 0.78rem; color: #8B949E; margin-top: -0.5rem; margin-bottom: 1.1rem;">
                Free web-grounded AI with verification
            </div>''',
            unsafe_allow_html=True,
        )
        st.markdown(
            '''<div style="background: rgba(255, 255, 255, 0.03); border: 1px dashed rgba(255, 255, 255, 0.12); border-radius: 12px; padding: 1.1rem 0.9rem; text-align: center; margin-bottom: 1.2rem;">
                <div style="font-size: 1.6rem; margin-bottom: 0.35rem;">🔐</div>
                <div style="font-size: 0.88rem; font-weight: 700; color: #FAF9F5; margin-bottom: 0.25rem;">Sign In Required</div>
                <div style="font-size: 0.75rem; color: #8B949E; line-height: 1.45;">
                    Sign in or create an account to start chat sessions, restore saved conversations, and use web-grounded verification.
                </div>
            </div>''',
            unsafe_allow_html=True,
        )
        with st.expander("ℹ️ About Hallucination Detector"):
            st.markdown(
                """
                1. **Live Autonomous Retrieval**: Fetches authoritative web sources (Wikipedia, government records, news, scholarly content).
                2. **Atomic Claim Extraction**: Deconstructs answers into individual verifiable factual assertions.
                3. **Cross-Examination**: Evaluates natural language entailment (NLI) & XGBoost confidence against evidence.
                4. **Zero-Hallucination Gate**: If sources lack conclusive evidence, the engine declines to guess to prevent misinformation.
                """
            )

    render_auth_screen()
    st.stop()


# ------------------------------------------------------------
# LIVE BLOCK VALIDATION (For logged-in users)
# ------------------------------------------------------------
current_user = st.session_state.get("authenticated_user")
if current_user:
    conn = get_db_connection()
    try:
        cur = conn.execute("SELECT is_blocked FROM users WHERE id = ?;", (current_user["id"],))
        row = cur.fetchone()
        if not row or row["is_blocked"]:
            st.session_state.authenticated_user = None
            st.session_state.conversations = []
            st.session_state.current_conversation_id = None
            st.session_state.auth_block_message = "🚫 Your account has been suspended by the administrator."
            st.rerun()
    finally:
        conn.close()

    # Ensure user's conversations are loaded into session
    if not st.session_state.get("conversations"):
        u_id = current_user["id"]
        saved_convs = load_user_saved_conversations(u_id)
        if not saved_convs and current_user.get("is_admin") and os.path.exists(CHAT_HISTORY_FILE):
            try:
                old_raw = load_json(CHAT_HISTORY_FILE, [])
                if old_raw and isinstance(old_raw, list):
                    for item in old_raw:
                        norm = normalize_conversation(item)
                        save_user_conversation(u_id, norm)
                    saved_convs = load_user_saved_conversations(u_id)
            except Exception:
                pass
        if not saved_convs:
            new_c = create_conversation()
            save_user_conversation(u_id, new_c)
            saved_convs = [new_c]
        st.session_state.conversations = saved_convs
        st.session_state.current_conversation_id = saved_convs[0]["id"]


# ============================================================
# SIDEBAR (For Logged-in Users)
# ============================================================

with st.sidebar:
    st.markdown(
        '''<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.8rem;">
            <div style="font-weight: 800; font-size: 1.15rem; color: #F0F6FC; display: flex; align-items: center; gap: 0.5rem;">
                <span>🛡️ Hallucination Detector</span>
            </div>
            <span style="font-size: 0.7rem; font-weight: 700; color: #34D399; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); padding: 0.15rem 0.5rem; border-radius: 9999px;">v3.0</span>
        </div>
        <div style="font-size: 0.78rem; color: #8B949E; margin-top: -0.5rem; margin-bottom: 0.8rem;">
            Free web-grounded AI with verification
        </div>''',
        unsafe_allow_html=True,
    )

    # User Profile / Identity Card
    user_info = st.session_state.get("authenticated_user") or {}
    u_admin = user_info.get("is_admin", False)
    u_name = user_info.get("username", "User")

    badge_html = (
        '<span style="color: #DA7756; font-weight: 700; background: rgba(218, 119, 86, 0.15); border: 1px solid rgba(218, 119, 86, 0.35); padding: 0.12rem 0.45rem; border-radius: 9999px; font-size: 0.68rem;">🛡️ Admin</span>'
        if u_admin
        else '<span style="color: #34D399; font-weight: 600; background: rgba(52, 211, 153, 0.12); border: 1px solid rgba(52, 211, 153, 0.25); padding: 0.12rem 0.45rem; border-radius: 9999px; font-size: 0.68rem;">👤 Member</span>'
    )

    st.markdown(
        f'''<div style="background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 0.75rem 0.9rem; margin-bottom: 0.6rem;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 0.5rem; overflow: hidden;">
                    <span style="font-size: 1.15rem;">{"🛡️" if u_admin else "👤"}</span>
                    <div style="overflow: hidden;">
                        <div style="font-weight: 700; font-size: 0.95rem; color: #FAF9F5; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                            {html.escape(u_name)}
                        </div>
                    </div>
                </div>
                {badge_html}
            </div>
        </div>''',
        unsafe_allow_html=True,
    )

    col_btn_logout, col_btn_new = st.columns([1, 1.4])
    with col_btn_logout:
        if st.button("🚪 Log Out", use_container_width=True, key="btn_logout"):
            st.session_state.authenticated_user = None
            st.session_state.conversations = []
            st.session_state.current_conversation_id = None
            st.rerun()
    with col_btn_new:
        if st.button("＋ New Chat", use_container_width=True, type="primary"):
            start_new_chat()
            st.rerun()

    # Admin Control Panel (Only for Administrator)
    if u_admin:
        with st.expander("🛡️ Admin: User Management & Moderation", expanded=False):
            all_users = get_all_users_for_admin()
            st.markdown(f"**Total Registered Users:** `{len(all_users)}`")

            active_cnt = sum(1 for u in all_users if not u["is_blocked"])
            blocked_cnt = sum(1 for u in all_users if u["is_blocked"])

            col_u1, col_u2 = st.columns(2)
            with col_u1:
                st.markdown(f"<span style='color: #34D399; font-size: 0.8rem; font-weight: 600;'>🟢 Active: {active_cnt}</span>", unsafe_allow_html=True)
            with col_u2:
                st.markdown(f"<span style='color: #F87171; font-size: 0.8rem; font-weight: 600;'>🔴 Blocked: {blocked_cnt}</span>", unsafe_allow_html=True)

            st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)

            other_users = [u for u in all_users if u["id"] != user_info.get("id")]
            if other_users:
                user_options = {
                    f"{u['username']} ({'🔴 Blocked' if u['is_blocked'] else '🟢 Active'}) — {u['conversation_count']} chats": u
                    for u in other_users
                }
                sel_label = st.selectbox(
                    "Select User to Moderate",
                    options=list(user_options.keys()),
                    key="admin_user_select",
                )
                sel_u = user_options[sel_label]

                st.markdown(
                    f'''<div style="background: rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 0.6rem 0.8rem; margin: 0.4rem 0 0.8rem 0; font-size: 0.78rem; line-height: 1.5;">
                        <b>User:</b> {html.escape(sel_u['username'])}<br/>
                        <b>Role:</b> {'Administrator' if sel_u['is_admin'] else 'Member'}<br/>
                        <b>Status:</b> {'🔴 Blocked' if sel_u['is_blocked'] else '🟢 Active'}<br/>
                        <b>Saved Chats:</b> {sel_u['conversation_count']}<br/>
                        <b>Last Active:</b> {sel_u['last_login']}<br/>
                        <b>Joined:</b> {sel_u['created_at'][:10]}
                    </div>''',
                    unsafe_allow_html=True,
                )

                if sel_u["is_admin"]:
                    st.caption("Cannot block administrator accounts.")
                else:
                    if sel_u["is_blocked"]:
                        if st.button(f"✅ Unblock '{sel_u['username']}'", type="primary", use_container_width=True, key=f"unblock_btn_{sel_u['id']}"):
                            ok, msg = toggle_user_block(user_info["id"], sel_u["id"], block=False)
                            if ok:
                                st.success(msg)
                                time.sleep(0.3)
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        if st.button(f"🚫 Block '{sel_u['username']}'", use_container_width=True, key=f"block_btn_{sel_u['id']}"):
                            ok, msg = toggle_user_block(user_info["id"], sel_u["id"], block=True)
                            if ok:
                                st.warning(msg)
                                time.sleep(0.3)
                                st.rerun()
                            else:
                                st.error(msg)
            else:
                st.caption("No other users registered yet.")

            st.markdown("---")
            with st.expander("📋 All Users Directory", expanded=False):
                for u in all_users:
                    s_label = "🔴 Blocked" if u["is_blocked"] else "🟢 Active"
                    r_label = "Admin" if u["is_admin"] else "User"
                    st.markdown(
                        f'''<div style="display:flex; justify-content:space-between; align-items:center; padding: 0.35rem 0.2rem; border-bottom: 1px solid rgba(255,255,255,0.04); font-size: 0.75rem;">
                            <div>
                                <b>{html.escape(u["username"])}</b> <span style="color:#8B949E;">({r_label})</span><br/>
                                <span style="color:#6E7681;">Chats: {u["conversation_count"]} • Last: {u["last_login"][:10] if u["last_login"] != "Never" else "Never"}</span>
                            </div>
                            <div>
                                <span style="font-weight:600; color:{'#F87171' if u['is_blocked'] else '#34D399'};">{s_label}</span>
                            </div>
                        </div>''',
                        unsafe_allow_html=True,
                    )

    st.markdown("### 💬 Conversations")

    search_conv = st.text_input(
        "Search conversations",
        placeholder="🔍 Search chats...",
        label_visibility="collapsed",
        key="sidebar_search_conv",
    )

    conversations_sorted = sorted(
        st.session_state.conversations,
        key=lambda c: c.get("updated_at", ""),
        reverse=True,
    )

    if search_conv.strip():
        q_lower = search_conv.strip().lower()
        conversations_display = [
            c for c in conversations_sorted
            if q_lower in c.get("title", "").lower() or any(q_lower in m.get("content", "").lower() for m in c.get("messages", []))
        ]
    else:
        conversations_display = conversations_sorted

    current_id = st.session_state.current_conversation_id

    for conversation_item in conversations_display:
        conversation_id = conversation_item.get("id")
        title = conversation_item.get("title", "New Chat")
        is_current = conversation_id == current_id
        label = ("● " if is_current else "○ ") + title

        if st.button(
            label,
            key=f"chat_{conversation_id}",
            use_container_width=True,
        ):
            st.session_state.current_conversation_id = conversation_id
            st.rerun()

    current_conv = get_current_conversation()
    with st.expander("✏️ Rename Active Chat"):
        new_title_val = st.text_input(
            "Chat title",
            value=current_conv.get("title", "New Chat") if current_conv else "",
            key="rename_title_input",
        )
        if st.button("Save Title", use_container_width=True, key="save_rename_btn"):
            if new_title_val.strip():
                rename_current_chat(new_title_val.strip())
                st.rerun()

    st.markdown("---")

    # Multi-Provider Settings Panel (Requirement 3)
    with st.expander("⚙️ Settings & AI Providers"):
        st.markdown(
            '''<div style="font-size: 0.8rem; color: #8B949E; margin-bottom: 0.6rem;">
                Supported AI providers and verification engines:
            </div>''',
            unsafe_allow_html=True,
        )

        has_gemini = bool(os.getenv("GEMINI_API_KEY") or st.session_state.get("USER_GEMINI_KEY"))
        has_openai = bool(os.getenv("OPENAI_API_KEY") or st.session_state.get("USER_OPENAI_KEY"))
        has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY") or st.session_state.get("USER_ANTHROPIC_KEY"))
        has_groq = bool(os.getenv("GROQ_API_KEY") or st.session_state.get("USER_GROQ_KEY"))
        has_openrouter = bool(OPENROUTER_API_KEY or st.session_state.get("USER_OPENROUTER_KEY"))

        providers = [
            ("Google Gemini", "Default / Grounded", has_gemini),
            ("OpenRouter", "Multi-Model Fallback", has_openrouter),
            ("OpenAI", "GPT-4o / GPT-4o-mini", has_openai),
            ("Anthropic", "Claude 3.5 Sonnet", has_anthropic),
            ("Groq", "Llama 3 / Mixtral", has_groq),
        ]

        for p_name, p_desc, p_ok in providers:
            badge = '<span class="status-badge-ok">● Configured</span>' if p_ok else '<span class="status-badge-missing">○ Not configured</span>'
            row_html = f'''
            <div class="provider-row">
                <div>
                    <div style="font-weight: 600; color: #F0F6FC;">{p_name}</div>
                    <div style="font-size: 0.72rem; color: #6E7681;">{p_desc}</div>
                </div>
                {badge}
            </div>
            '''
            st.markdown(row_html, unsafe_allow_html=True)

        st.markdown(
            '''<div style="font-size: 0.76rem; color: #34D399; font-weight: 600; margin: 0.5rem 0;">
                ● Auto-fallback enabled across active models
            </div>''',
            unsafe_allow_html=True,
        )

        st.markdown("##### Custom API Key")
        selected_provider = st.selectbox(
            "Select Provider",
            ["Google Gemini", "OpenAI", "Anthropic Claude", "Groq", "OpenRouter"],
            key="custom_prov_select",
        )
        custom_key_val = st.text_input(
            f"Enter {selected_provider} API Key",
            type="password",
            placeholder="sk-...",
            key="custom_key_input",
            help="Stored in session memory only. Never written to disk.",
        )
        if st.button("Save Key to Session", use_container_width=True, key="save_custom_key_btn"):
            if custom_key_val.strip():
                if "gemini" in selected_provider.lower():
                    st.session_state["USER_GEMINI_KEY"] = custom_key_val.strip()
                    os.environ["GEMINI_API_KEY"] = custom_key_val.strip()
                elif "openai" in selected_provider.lower():
                    st.session_state["USER_OPENAI_KEY"] = custom_key_val.strip()
                    os.environ["OPENAI_API_KEY"] = custom_key_val.strip()
                elif "anthropic" in selected_provider.lower():
                    st.session_state["USER_ANTHROPIC_KEY"] = custom_key_val.strip()
                    os.environ["ANTHROPIC_API_KEY"] = custom_key_val.strip()
                elif "groq" in selected_provider.lower():
                    st.session_state["USER_GROQ_KEY"] = custom_key_val.strip()
                    os.environ["GROQ_API_KEY"] = custom_key_val.strip()
                elif "openrouter" in selected_provider.lower():
                    st.session_state["USER_OPENROUTER_KEY"] = custom_key_val.strip()
                    os.environ["OPENROUTER_API_KEY"] = custom_key_val.strip()
                st.success("API key active for current session!")
                st.rerun()

        st.markdown(
            '''<div style="font-size: 0.72rem; color: #8B949E; line-height: 1.4; margin-top: 0.4rem;">
                🔒 <i>API keys are never stored on disk. Free tier uses shared community endpoints with auto-fallback.</i>
            </div>
            <div style="font-size: 0.74rem; color: #58A6FF; margin-top: 0.6rem; padding-top: 0.5rem; border-top: 1px solid rgba(255, 255, 255, 0.08);">
                🌐 <b>Domain Status:</b> Ready for hallucinationdetector.com
            </div>''',
            unsafe_allow_html=True,
        )

    st.markdown("### 🔬 Engine Mode")
    selected_mode_label = st.selectbox(
        "Verification Mode",
        options=list(PIPELINE_MODE_MAP.keys()),
        index=0,
        help="Select how facts and evidence are retrieved and verified.",
        label_visibility="collapsed",
    )
    active_mode = PIPELINE_MODE_MAP[selected_mode_label]
    st.session_state["pipeline_mode"] = active_mode

    st.markdown("---")

    if current_conv and current_conv.get("messages"):
        export_text = generate_chat_export(current_conv)
        st.download_button(
            "📥 Export Chat (.md)",
            data=export_text,
            file_name=f"hallucination_report_{int(time.time())}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with st.expander("ℹ️ About Hallucination Detector"):
        st.markdown(
            """
            1. **Live Autonomous Retrieval**: Fetches authoritative web sources (Wikipedia, government records, news, scholarly content).
            2. **Atomic Claim Extraction**: Deconstructs answers into individual verifiable factual assertions.
            3. **Cross-Examination**: Evaluates natural language entailment (NLI) & XGBoost confidence against evidence.
            4. **Zero-Hallucination Gate**: If sources lack conclusive evidence, the engine declines to guess to prevent misinformation.
            """
        )

    if st.button("🗑️ Delete Chat", use_container_width=True):
        delete_current_chat()
        st.rerun()

    if st.button("🧹 Clear All Conversations", use_container_width=True):
        clear_all_chats()
        st.rerun()


# ============================================================
# MAIN UI
# ============================================================

conversation = get_current_conversation()

# Empty State / Landing (Claude Style)
if len(conversation["messages"]) == 0:
    st.markdown(
        '''<div class="claude-hero-container">
            <div class="claude-hero-icon">✦</div>
            <h1 class="claude-hero-title">What would you like to verify?</h1>
            <p class="claude-hero-subtitle">
                Ask any question — answers are retrieved from live web sources and independently verified claim-by-claim.
            </p>
            <div>
                <span class="claude-hero-pill">
                    <span class="claude-pulse"></span>
                    Live Web Grounding Active
                </span>
            </div>
        </div>''',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '''<div style="display: flex; align-items: center; justify-content: space-between; padding: 0.6rem 0.5rem 1rem 0.5rem; border-bottom: 1px solid rgba(255, 255, 255, 0.06); margin-bottom: 1rem; max-width: 820px; margin-left: auto; margin-right: auto;">
            <div style="display: flex; align-items: center; gap: 0.5rem; font-weight: 700; font-size: 1.05rem; color: #FAF9F5;">
                <span style="color: #DA7756; font-size: 1.2rem;">✦</span> Hallucination Detector
            </div>
            <span class="claude-hero-pill" style="margin-top: 0; font-size: 0.68rem; padding: 0.15rem 0.6rem;">
                <span class="claude-pulse"></span>
                Live Web Grounding
            </span>
        </div>''',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "🏛️ Current Events\n\nWho is the current Chief Minister of Tamil Nadu?",
            use_container_width=True,
            key="starter_cm",
        ):
            st.session_state["pending_starter"] = "who is the current chief minister of tamil nadu?"
            st.rerun()

        if st.button(
            "🔭 Science\n\nWhat did the James Webb Space Telescope recently discover?",
            use_container_width=True,
            key="starter_jwst",
        ):
            st.session_state["pending_starter"] = "What did the James Webb Space Telescope recently discover?"
            st.rerun()

    with col2:
        if st.button(
            "🤖 AI Concepts\n\nWhat is an AI hallucination and why do LLMs hallucinate?",
            use_container_width=True,
            key="starter_hd",
        ):
            st.session_state["pending_starter"] = "what is an AI hallucination and why do LLMs hallucinate?"
            st.rerun()

        if st.button(
            "💻 Technology\n\nWhat are the latest developments in quantum computing?",
            use_container_width=True,
            key="starter_quantum",
        ):
            st.session_state["pending_starter"] = "What are the latest developments in quantum computing?"
            st.rerun()


# ============================================================
# DISPLAY CURRENT CONVERSATION
# ============================================================

for message in conversation["messages"]:
    role = message.get("role")
    content = message.get("content", "")

    if role == "user":
        render_user_message(content)

    elif role == "assistant":
        with st.chat_message("assistant", avatar="🛡️"):
            status = message.get("status")
            verification = message.get("verification")
            sources = message.get("sources", [])

            # 1. Verification status card (Requirement 5)
            render_verification_card(status, verification)

            # 2. Answer content (Requirement 1)
            render_assistant_content(content, status)

            # 3. Sources & Evidence (Requirement 4)
            render_sources(sources)

            # 4. Detailed verification metrics (Requirement 5)
            render_verification_details(verification)

            # 5. Model badge & auto-fallback indicator
            if message.get("answer_model"):
                st.caption(f"Answer model: {message['answer_model']} • Auto-fallback enabled")


# ============================================================
# CHAT INPUT & EXECUTION
# ============================================================

pending_starter_query = st.session_state.pop("pending_starter", None)
user_chat_input = st.chat_input("Ask anything — answers are web-grounded and independently verified...")
st.markdown(
    '<div class="chat-disclaimer">Hallucination Detector searches the web and independently verifies claims before answering. Always verify critical facts.</div>',
    unsafe_allow_html=True,
)

user_question = pending_starter_query or user_chat_input

if user_question:
    user_question = user_question.strip()

    if user_question:
        # Check active status of authenticated user
        current_user = st.session_state.get("authenticated_user")
        if not current_user:
            st.error("Please sign in to send messages.")
            st.stop()

        # Real-time DB check if user has been blocked
        conn = get_db_connection()
        try:
            cur = conn.execute("SELECT is_blocked FROM users WHERE id = ?;", (current_user["id"],))
            row = cur.fetchone()
            if not row or row["is_blocked"]:
                st.session_state.authenticated_user = None
                st.session_state.conversations = []
                st.session_state.current_conversation_id = None
                st.session_state.auth_block_message = "🚫 Your account has been suspended by the administrator."
                st.rerun()
        finally:
            conn.close()

        # Save user message first so it survives
        conversation["messages"].append({
            "role": "user",
            "content": user_question,
            "timestamp": now_iso(),
        })

        if conversation["title"] == "New Chat":
            conversation["title"] = make_title(user_question)

        conversation["updated_at"] = now_iso()
        save_conversations()

        render_user_message(user_question)

        with st.chat_message("assistant", avatar="🛡️"):
            # Dynamic Stepper (Requirement 2)
            with st.status("🔎 Searching web sources...", expanded=True) as status_box:
                def on_progress(step_text):
                    status_box.update(label=step_text, state="running")

                active_mode = st.session_state.get(
                    "pipeline_mode",
                    "Web Search + OpenRouter LLM Verifier",
                )
                try:
                    result = process_question(
                        user_question,
                        history=get_recent_exchanges(conversation),
                        pipeline_mode=active_mode,
                        progress_callback=on_progress,
                    )
                except Exception as ex:
                    result = {
                        "answer": None,
                        "status": "error",
                        "sources": [],
                        "verification": None,
                        "error": format_user_friendly_error(ex),
                        "answer_model": None,
                    }

                status_res = result.get("status")
                if status_res == "verified":
                    status_box.update(label="✓ Verified: Grounded in live web evidence", state="complete", expanded=False)
                elif status_res == "not_verified":
                    status_box.update(label="⚠️ Verification complete: Some claims unverified", state="complete", expanded=False)
                elif status_res == "not_found":
                    status_box.update(label="🔍 Search complete: Insufficient reliable evidence", state="complete", expanded=False)
                elif status_res == "error":
                    status_box.update(label="✕ Processing encountered an issue", state="error", expanded=False)
                else:
                    status_box.update(label="✓ Complete", state="complete", expanded=False)

            answer = result.get("answer")
            status = result.get("status")
            sources = result.get("sources", [])
            verification = result.get("verification")
            error = result.get("error")
            answer_model = result.get("answer_model")

            if status == "error":
                friendly_error = format_user_friendly_error(error)
                answer_to_save = f"⚠️ {friendly_error}"
                st.error(friendly_error)
            elif status == "not_found":
                answer_to_save = "NOT_FOUND"
                render_verification_card(status, verification)
                render_assistant_content(answer_to_save, status)
                render_sources(sources)
            else:
                answer_to_save = answer or "NOT_FOUND"
                render_verification_card(status, verification)
                render_assistant_content(answer_to_save, status)
                render_sources(sources)
                render_verification_details(verification)

            if answer_model:
                st.caption(f"Answer model: {answer_model} • Auto-fallback enabled")

        assistant_message = {
            "role": "assistant",
            "content": answer_to_save,
            "status": status,
            "sources": sources,
            "verification": verification,
            "answer_model": answer_model,
            "error": error,
            "timestamp": now_iso(),
        }

        conversation["messages"].append(assistant_message)

        if len(conversation["messages"]) > MAX_HISTORY_MESSAGES:
            conversation["messages"] = conversation["messages"][-MAX_HISTORY_MESSAGES:]

        conversation["updated_at"] = now_iso()
        save_conversations()

        if status in {"verified", "not_verified", "verification_unavailable", "not_found"}:
            rotate_model()
            save_conversations()

        st.rerun()