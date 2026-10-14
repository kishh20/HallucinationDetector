"""ChatGPT-style theme for Streamlit.

Usage in app.py (right after st.set_page_config):

    from ui_theme import apply_theme
    apply_theme(st.session_state.get("theme", "System"))   # "Light" | "Dark" | "System"
"""
import streamlit as st

LIGHT = """
--bg:#ffffff; --sidebar:#f9f9f9; --surface:#f4f4f4; --surface-2:#ececec;
--text:#0d0d0d; --muted:#6b6b6b; --border:#e5e5e5; --accent:#0d0d0d; --accent-text:#ffffff;
--user-bubble:#f4f4f4; --input-bg:#f4f4f4; --shadow:0 2px 12px rgba(0,0,0,.06);
--text-primary:#0d0d0d; --text-muted:#6b6b6b; --text-subtle:#6b6b6b;
--btn-disabled-bg:#e5e5e5; --btn-disabled-color:#ffffff;
color-scheme: light;
"""
DARK = """
--bg:#212121; --sidebar:#171717; --surface:#2f2f2f; --surface-2:#3a3a3a;
--text:#ececec; --muted:#9b9b9b; --border:#3a3a3a; --accent:#ececec; --accent-text:#0d0d0d;
--user-bubble:#303030; --input-bg:#2f2f2f; --shadow:0 2px 12px rgba(0,0,0,.35);
--text-primary:#ececec; --text-muted:#9b9b9b; --text-subtle:#9b9b9b;
--btn-disabled-bg:#383838; --btn-disabled-color:#676767;
color-scheme: dark;
"""

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"], .stApp, button, input, textarea {
  font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif !important;
}
.stApp, [data-testid="stAppViewContainer"] { background: var(--bg) !important; color: var(--text) !important; }
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], footer { display:none !important; }
[data-testid="stMainBlockContainer"], .block-container { max-width: 768px !important; padding: 2rem 1.25rem 9rem !important; }
h1,h2,h3,h4 { color: var(--text) !important; font-weight: 600 !important; letter-spacing: -0.01em; }
p, li, label, span, div { color: inherit; }
small, .stCaption, [data-testid="stCaptionContainer"] { color: var(--muted) !important; }
hr { border-color: var(--border) !important; }

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] { background: var(--sidebar) !important; border-right: 1px solid var(--border); }
[data-testid="stSidebar"] * { color: var(--text); }
[data-testid="stSidebarContent"] { padding: .75rem .5rem; }

/* ---------- Buttons ---------- */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
  background: transparent; color: var(--text); border: 1px solid var(--border);
  border-radius: 10px; padding: .5rem .85rem; font-weight: 500; font-size: .9rem;
  box-shadow: none; transition: background .15s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover { background: var(--surface); border-color: var(--border); color: var(--text); }
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button {
  background: var(--accent); color: var(--accent-text); border: none; border-radius: 999px;
  padding: .6rem 1.2rem;
}
.stButton > button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] > button:hover { opacity: .88; background: var(--accent); color: var(--accent-text); }
/* sidebar chat list = flat, left-aligned rows */
[data-testid="stSidebar"] .stButton > button { width:100%; justify-content:flex-start; text-align:left; border:none; border-radius: 8px; padding:.55rem .7rem; background: transparent; color: var(--text); }
[data-testid="stSidebar"] .stButton > button:hover { background: var(--surface-2); }
/* New verification button in sidebar (outlined card button) */
[data-testid="stSidebar"] [class*="st-key-btn_new_chat"] .stButton > button {
  border: 1px solid var(--border) !important; border-radius: 10px !important;
  background: transparent !important; color: var(--text) !important; padding: .55rem .85rem !important;
}
[data-testid="stSidebar"] [class*="st-key-btn_new_chat"] .stButton > button:hover {
  background: var(--surface) !important;
}
/* Active conversation highlight in sidebar */
[data-testid="stSidebar"] [class*="st-key-chat_active_"] .stButton > button {
  background: var(--surface-2) !important; font-weight: 500 !important;
}
/* Segmented theme switcher in sidebar */
[data-testid="stSidebar"] [class*="st-key-theme_active_"] .stButton > button {
  background: var(--bg) !important; color: var(--text) !important;
  border: 1px solid var(--border) !important; border-radius: 8px !important;
  justify-content: center !important; text-align: center !important;
  padding: .35rem .5rem !important; font-size: .82rem !important; font-weight: 500 !important;
}
[data-testid="stSidebar"] [class*="st-key-theme_opt_"] .stButton > button {
  background: transparent !important; color: var(--muted) !important;
  border: 1px solid transparent !important; border-radius: 8px !important;
  justify-content: center !important; text-align: center !important;
  padding: .35rem .5rem !important; font-size: .82rem !important;
}
[data-testid="stSidebar"] [class*="st-key-theme_opt_"] .stButton > button:hover {
  color: var(--text) !important; background: var(--surface) !important;
}

/* ---------- Inputs ---------- */
.stTextInput input, .stTextArea textarea, .stSelectbox > div > div, [data-baseweb="input"], [data-baseweb="select"] > div {
  background: var(--input-bg) !important; color: var(--text) !important;
  border: 1px solid var(--border) !important; border-radius: 12px !important; box-shadow:none !important;
}
.stTextInput input:focus, .stTextArea textarea:focus { border-color: var(--muted) !important; }
.stTextInput label, .stTextArea label { color: var(--muted) !important; font-size:.85rem; font-weight:500; }

/* ---------- Tabs (sign in / create account) ---------- */
.stTabs [data-baseweb="tab-list"] { gap: .25rem; border-bottom: 1px solid var(--border); }
.stTabs [data-baseweb="tab"] { color: var(--muted); font-weight:500; background:transparent; }
.stTabs [aria-selected="true"] { color: var(--text) !important; }
.stTabs [data-baseweb="tab-highlight"] { background: var(--text) !important; }

/* ---------- Forms / expanders / cards ---------- */
[data-testid="stForm"], [data-testid="stExpander"] {
  background: transparent; border: 1px solid var(--border) !important; border-radius: 14px !important; box-shadow:none;
}
[data-testid="stExpander"] summary:hover { background: var(--surface); }
[data-testid="stAlert"] { background: var(--surface); border:1px solid var(--border); border-radius:12px; color: var(--text); }

/* ---------- Chat messages ---------- */
[data-testid="stChatMessage"] { background: transparent !important; padding: 1rem 0 !important; gap: .9rem; align-items:flex-start; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  flex-direction: row-reverse; background: transparent !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {
  background: var(--user-bubble); border-radius: 22px; padding: .7rem 1.1rem; max-width: 80%; margin-left:auto;
}
[data-testid="stChatMessageAvatarUser"] { display:none; }
[data-testid="stChatMessageAvatarAssistant"] {
  background: var(--surface) !important; color: var(--text) !important; border: 1px solid var(--border); border-radius: 50%;
}
[data-testid="stChatMessageContent"] { line-height: 1.7; font-size: .98rem; }
[data-testid="stChatMessageContent"] code { background: var(--surface); border-radius: 6px; padding: .1rem .35rem; }
[data-testid="stChatMessageContent"] pre { background: var(--sidebar) !important; border:1px solid var(--border); border-radius: 12px; }
[data-testid="stChatMessageContent"] a { color: var(--text); text-decoration: underline; text-underline-offset: 3px; }

/* User message custom bubble helper */
.user-msg-row { display: flex; justify-content: flex-end; margin: 1rem 0; }
.user-msg-bubble {
  background: var(--user-bubble); color: var(--text);
  border-radius: 22px; padding: .7rem 1.1rem; max-width: 80%;
  line-height: 1.6; font-size: .98rem; word-break: break-word;
}

/* ---------- Verification Pill & Source Pills (ChatGPT Mockup Style) ---------- */
.hd-verif-pill {
  display: inline-flex; align-items: center; gap: .4rem;
  background: var(--surface); color: var(--text);
  border-radius: 999px; padding: .3rem .85rem;
  font-size: .82rem; font-weight: 500; margin-bottom: .65rem;
}
.hd-verif-pill svg { flex-shrink: 0; color: var(--muted); }
.hd-sources {
  display: flex; flex-wrap: wrap; gap: .45rem; margin-top: .75rem; margin-bottom: .35rem;
}
a.hd-source-pill, .hd-source-pill {
  display: inline-flex; align-items: center; gap: .35rem;
  border: 1px solid var(--border); border-radius: 999px;
  padding: .28rem .8rem; font-size: .8rem; font-weight: 400;
  color: var(--muted) !important; text-decoration: none !important;
  background: transparent; transition: background .15s ease, color .15s ease, border-color .15s ease;
}
a.hd-source-pill:hover {
  background: var(--surface); color: var(--text) !important; border-color: var(--muted);
}

/* ---------- Sidebar Brand, History Headers & Account Footer ---------- */
.brand {
  display: flex; align-items: center; gap: .55rem;
  padding: .35rem .5rem .85rem; font-weight: 500; font-size: .98rem; color: var(--text);
}
.brand-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border: 1px solid var(--border); border-radius: 5px;
  color: var(--muted); font-size: .75rem;
}
.brand-name { font-weight: 500; font-size: .96rem; color: var(--text); }
.brand-sub { display: none; }
.conv-group-header {
  font-size: .76rem; font-weight: 500; color: var(--muted) !important;
  padding: .65rem .65rem .2rem;
}
.conv-empty-hint {
  font-size: .82rem; color: var(--muted) !important; padding: .5rem .65rem;
}
.theme-switcher-label { display: none; }
.account {
  display: flex; align-items: center; gap: .65rem;
  padding: .55rem .4rem; margin-top: .25rem;
}
.account-avatar {
  width: 30px; height: 30px; border-radius: 50%;
  background: var(--surface); border: 1px solid var(--border);
  display: flex; align-items: center; justify-content: center;
  font-size: .75rem; font-weight: 600; color: var(--text); flex-shrink: 0;
}
.account-name { font-size: .88rem; font-weight: 500; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.account-role, .user-badge-admin, .user-badge-member { display: none; }

/* ---------- Topbar ---------- */
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 0 1.25rem; margin-bottom: .5rem;
}
.topbar .model { font-size: 1.02rem; font-weight: 500; color: var(--text); }
.topbar .model-dot, .topbar .top-badge { display: none; }

/* ---------- Inline Thinking Indicator ---------- */
.think-inline {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 4px; margin: 4px 0 8px;
}
.think-dots { position: relative; width: 22px; height: 22px; flex-shrink: 0; }
.think-dots i {
  position: absolute; top: 50%; left: 50%;
  width: 4px; height: 4px; margin: -2px 0 0 -2px;
  border-radius: 50%; background: var(--muted);
  animation: thinkOrbit 1.8s linear infinite;
}
.think-dots i:nth-child(2) { animation-delay: -0.6s; }
.think-dots i:nth-child(3) { animation-delay: -1.2s; }
@keyframes thinkOrbit {
  0%   { transform: rotate(0deg) translateX(7px) scale(0.8); opacity: 0.5; }
  50%  { transform: rotate(180deg) translateX(7px) scale(1.2); opacity: 1; }
  100% { transform: rotate(360deg) translateX(7px) scale(0.8); opacity: 0.5; }
}
.think-label {
  font-size: 14.5px; font-weight: 450;
  background: linear-gradient(90deg, var(--muted), var(--text), var(--muted));
  background-size: 200% 100%;
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: thinkShimmer 2.2s linear infinite;
}
@keyframes thinkShimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.think-verbs { position: relative; height: 1.4em; min-width: 110px; font-size: 12.5px; }
.think-verbs span {
  position: absolute; left: 0; opacity: 0; color: var(--muted) !important;
  animation: verbCycle 9s infinite;
}
.think-verbs span:nth-child(2) { animation-delay: 3s; }
.think-verbs span:nth-child(3) { animation-delay: 6s; }
@keyframes verbCycle { 0%,28% { opacity: 1; } 33%,100% { opacity: 0; } }
.think-done, .gpt-searched-pill, .model-meta-bar {
  font-size: 12.5px; color: var(--muted) !important; padding: 2px 0 6px;
}
.not-found-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 14px; padding: .9rem 1.1rem; margin: .4rem 0;
}
.not-found-title { font-weight: 600; font-size: .92rem; margin-bottom: .25rem; color: var(--text); }
.not-found-desc { font-size: .88rem; color: var(--muted) !important; line-height: 1.55; }
.metric-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: .5rem; margin: .5rem 0; }
.metric-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: .55rem .75rem; }
.metric-card-label { font-size: .74rem; color: var(--muted) !important; }
.metric-card-val { font-size: .98rem; font-weight: 600; color: var(--text); }
.eval-by-line, .verdict-box { font-size: .84rem; color: var(--muted) !important; margin: .35rem 0; }

/* ---------- Chat input (ChatGPT-style floating capsule) ---------- */
[data-testid="stBottom"] {
  background: linear-gradient(180deg, transparent 0%, var(--bg) 28%, var(--bg) 100%) !important;
  border-top: none !important;
}
[data-testid="stBottomBlockContainer"] {
  max-width: 768px !important;
  padding-left: 1rem !important;
  padding-right: 1rem !important;
  padding-top: 0.5rem !important;
  padding-bottom: 0.85rem !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: stretch !important;
}
[data-testid="stBottomBlockContainer"]::after {
  content: "Answers are checked against live sources before display.";
  display: block;
  text-align: center;
  font-size: 0.76rem;
  color: var(--muted);
  margin-top: 0.5rem;
  font-weight: 400;
  letter-spacing: -0.01em;
}

/* Outer Streamlit input container */
[data-testid="stChatInput"] {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
  width: 100% !important;
}

/* Inner interactive capsule container (matches ChatGPT pill) */
[data-testid="stChatInput"] > div {
  background-color: var(--input-bg) !important;
  border: 1px solid var(--border) !important;
  border-radius: 28px !important;
  box-shadow: var(--shadow) !important;
  padding: 8px 10px 8px 18px !important;
  min-height: 52px !important;
  display: flex !important;
  flex-direction: row !important;
  align-items: center !important;
  gap: 8px !important;
  box-sizing: border-box !important;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease !important;
}
[data-testid="stChatInput"] > div:focus-within {
  border-color: var(--muted) !important;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.08) !important;
}

/* Textarea wrapper & base input */
[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="input"],
[data-testid="stChatInput"] [data-baseweb="base-input"] {
  background: transparent !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
  flex: 1 !important;
}

/* Textarea */
[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] [data-testid="stChatInputTextArea"] {
  background: transparent !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  color: var(--text) !important;
  font-family: inherit !important;
  font-size: 0.98rem !important;
  line-height: 1.5 !important;
  padding: 6px 0 !important;
  margin: 0 !important;
  resize: none !important;
  caret-color: var(--text) !important;
  width: 100% !important;
}
[data-testid="stChatInput"] textarea:focus,
[data-testid="stChatInput"] [data-testid="stChatInputTextArea"]:focus {
  outline: none !important;
  border: none !important;
  box-shadow: none !important;
}
[data-testid="stChatInput"] textarea::placeholder,
[data-testid="stChatInput"] [data-testid="stChatInputTextArea"]::placeholder {
  color: var(--muted) !important;
  opacity: 0.8 !important;
  font-size: 0.95rem !important;
  font-weight: 400 !important;
}

/* Submit Button - Pure Circle matching ChatGPT */
[data-testid="stChatInputSubmitButton"],
[data-testid="stChatInput"] button {
  width: 32px !important;
  height: 32px !important;
  min-width: 32px !important;
  min-height: 32px !important;
  border-radius: 50% !important;
  border: none !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  background: var(--accent) !important;
  color: var(--accent-text) !important;
  cursor: pointer !important;
  padding: 0 !important;
  margin: 0 0 0 4px !important;
  flex-shrink: 0 !important;
  transition: opacity 0.15s ease, transform 0.1s ease, background 0.15s ease !important;
}
[data-testid="stChatInputSubmitButton"]:hover:not(:disabled),
[data-testid="stChatInput"] button:hover:not(:disabled) {
  opacity: 0.88 !important;
  transform: scale(1.04) !important;
}
[data-testid="stChatInputSubmitButton"]:disabled,
[data-testid="stChatInput"] button:disabled {
  background: var(--btn-disabled-bg) !important;
  color: var(--btn-disabled-color) !important;
  cursor: not-allowed !important;
  opacity: 1 !important;
  transform: none !important;
}
[data-testid="stChatInputSubmitButton"] svg,
[data-testid="stChatInput"] button svg {
  width: 17px !important;
  height: 17px !important;
  fill: currentColor !important;
  color: inherit !important;
}

/* Remove bulky helper labels inside the pill */
[data-testid="stChatInput"] .stChatInputInstructions,
[data-testid="stChatInput"] [id="stChatInputInstructions"] {
  display: none !important;
}

/* ---------- Misc ---------- */
.hd-hero { text-align:center; margin: 18vh 0 2rem; }
.hd-hero h1 { font-size: 2rem; margin-bottom:.4rem; }
.hd-hero p { color: var(--muted); }
.chat-disclaimer { text-align: center; font-size: .78rem; color: var(--muted) !important; margin-top: .5rem; }
::-webkit-scrollbar { width: 8px; } ::-webkit-scrollbar-thumb { background: var(--surface-2); border-radius: 8px; }

@media (max-width: 680px) { .think-verbs { display: none; } }
@media (prefers-reduced-motion: reduce) {
  .think-dots i, .think-label, .think-verbs span { animation: none !important; }
  .think-label { background: none !important; -webkit-text-fill-color: var(--muted) !important; color: var(--muted) !important; }
  .think-verbs span:not(:first-child) { display: none; }
}
"""


def apply_theme(mode: str = "System") -> None:
    mode = (mode or "System").lower()
    if mode == "dark":
        vars_css = f":root{{{DARK}}}"
    elif mode == "light":
        vars_css = f":root{{{LIGHT}}}"
    else:
        vars_css = f":root{{{LIGHT}}} @media (prefers-color-scheme: dark){{:root{{{DARK}}}}}"
    st.markdown(f"<style>{vars_css}\n{CSS}</style>", unsafe_allow_html=True)


def hero(title: str = "What can I verify for you?", sub: str = "") -> None:
    """Centered empty-state heading, like ChatGPT's home screen. Replaces the 3 feature cards + 4 prompt cards."""
    st.markdown(f"<div class='hd-hero'><h1>{title}</h1><p>{sub}</p></div>", unsafe_allow_html=True)
