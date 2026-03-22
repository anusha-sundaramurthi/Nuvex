import streamlit as st
import requests
from chat_ui.core.config import config
import uuid
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


st.set_page_config(
    page_title="Nuvex — AI Shopping Bot",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@700;800;900&display=swap');

        *, *::before, *::after { box-sizing: border-box; }

        /* ── BASE — cream white background ── */
        html, body, .stApp {
            background-color: #f7f5f2 !important;
            color: #1a1a2e !important;
            font-family: 'Inter', sans-serif !important;
        }

        .block-container {
            padding-top: 0 !important;
            padding-bottom: 6rem !important;
            max-width: 920px !important;
        }

        /* ── SIDEBAR — hidden ── */
        section[data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"] {
            background: #ffffff !important;
            border-right: 1.5px solid #e8e4df !important;
            box-shadow: 2px 0 10px rgba(0,0,0,0.06) !important;
        }
        section[data-testid="stSidebar"] > div { padding: 1.4rem 1rem !important; }
        section[data-testid="stSidebar"] * { font-family: 'Inter', sans-serif !important; }
        section[data-testid="stSidebar"] .stCaption,
        section[data-testid="stSidebar"] .stCaption p {
            color: #888 !important; font-size: 0.82rem !important;
        }
        section[data-testid="stSidebar"] hr {
            border: none !important; border-top: 1px solid #e8e4df !important; margin: 10px 0 !important;
        }
        section[data-testid="stSidebar"] img { border-radius: 10px !important; border: 1px solid #e8e4df !important; }

        .sidebar-brand-logo {
            font-family: 'Outfit', sans-serif;
            font-size: 1.8rem; font-weight: 900;
            background: linear-gradient(135deg, #7c3aed, #2563eb);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
            letter-spacing: 0.05em;
        }
        .sidebar-brand-tag {
            font-size: 0.6rem; font-weight: 600; letter-spacing: 0.2em;
            text-transform: uppercase; color: #aaa; margin-top: 2px;
        }

        .stTabs [data-baseweb="tab-list"] {
            background: #f0ede8 !important; border-radius: 10px !important;
            padding: 3px !important; border: 1px solid #e0dbd4 !important; gap: 2px !important;
        }
        .stTabs [data-baseweb="tab"] {
            background: transparent !important; border: none !important;
            border-radius: 7px !important; color: #888 !important;
            font-size: 0.75rem !important; font-weight: 600 !important;
        }
        .stTabs [aria-selected="true"] {
            background: #ffffff !important; color: #7c3aed !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.1) !important;
        }
        .stTabs [data-baseweb="tab-panel"] { padding: 0.8rem 0 0 0 !important; }

        /* ── NAVBAR — truly fixed using Streamlit header slot ── */
        /* Fix the Streamlit top header area */
        [data-testid="stHeader"] {
            background: #f7f5f2 !important;
            border-bottom: 2px solid #e8e4df !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
            height: 4rem !important;
            display: flex !important;
            align-items: center !important;
        }

        .nuvex-navbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.6rem 0;
            border-bottom: 2px solid #e8e4df;
            margin-bottom: 1.2rem;
            background: #f7f5f2;
        }

        /* Use Streamlit's own sticky header mechanism */
        .stApp > header {
            background: #f7f5f2 !important;
        }

        /* Make main content not overlap the header */
        .block-container {
            padding-top: 1rem !important;
        }

        /* The actual sticky navbar via Streamlit header injection */
        #nuvex-header {
            position: fixed;
            top: 0;
            right: 0;
            left: 0;
            height: 60px;
            background: #f7f5f2;
            border-bottom: 2px solid #e8e4df;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 2rem;
            z-index: 99999;
        }
        /* offset body so content doesn't hide under fixed bar */
        section.main > div:first-child {
            padding-top: 70px !important;
        }
        section[data-testid="stSidebarContent"] {
            padding-top: 70px !important;
        }
        .nuvex-logo {
            font-family: 'Outfit', sans-serif; font-size: 2rem; font-weight: 900;
            background: linear-gradient(135deg, #7c3aed, #2563eb);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
            letter-spacing: 0.06em; line-height: 1;
        }
        .nuvex-tagline {
            font-size: 0.6rem; font-weight: 600; letter-spacing: 0.2em;
            text-transform: uppercase; color: #bbb; margin-top: 3px;
        }
        .nuvex-badge {
            background: linear-gradient(135deg, #7c3aed, #2563eb);
            color: #fff; font-size: 0.65rem; font-weight: 700;
            letter-spacing: 0.1em; text-transform: uppercase;
            padding: 8px 18px; border-radius: 20px;
            box-shadow: 0 4px 14px rgba(124,58,237,0.3);
        }

        /* ── CHAT CONTAINER ── */
        .chat-container {
            display: flex;
            flex-direction: column;
            gap: 20px;
            padding: 16px 0 24px 0;
        }

        /* ── BOT MESSAGE (LEFT) ── */
        .msg-row-bot {
            display: flex;
            align-items: flex-end;
            gap: 14px;
            justify-content: flex-start;
            padding-right: 15%;
        }
        .msg-avatar-bot {
            width: 42px; height: 42px; min-width: 42px; border-radius: 50%;
            background: linear-gradient(135deg, #7c3aed, #2563eb);
            display: flex; align-items: center; justify-content: center;
            font-size: 1.2rem; flex-shrink: 0;
            box-shadow: 0 4px 12px rgba(124,58,237,0.35);
        }
        .msg-bubble-bot {
            background: #ffffff;
            border: 1.5px solid #e8e4df;
            border-radius: 4px 20px 20px 20px;
            padding: 14px 20px;
            color: #1a1a2e;
            font-size: 1.1rem;
            line-height: 1.9;
            font-weight: 400;
            box-shadow: 0 2px 10px rgba(0,0,0,0.07);
            word-break: break-word;
        }

        /* ── USER MESSAGE (RIGHT) ── */
        .msg-row-user {
            display: flex;
            align-items: flex-end;
            gap: 14px;
            justify-content: flex-end;
            padding-left: 15%;
        }
        .msg-bubble-user {
            background: linear-gradient(135deg, #7c3aed, #2563eb);
            border: none;
            border-radius: 20px 4px 20px 20px;
            padding: 14px 20px;
            color: #ffffff;
            font-size: 1.1rem;
            line-height: 1.9;
            font-weight: 500;
            box-shadow: 0 4px 16px rgba(124,58,237,0.3);
            word-break: break-word;
        }
        .msg-avatar-user {
            width: 42px; height: 42px; min-width: 42px; border-radius: 50%;
            background: linear-gradient(135deg, #4f46e5, #7c3aed);
            display: flex; align-items: center; justify-content: center;
            font-size: 1.2rem; flex-shrink: 0;
            box-shadow: 0 4px 12px rgba(79,70,229,0.3);
        }

        /* ── TYPING INDICATOR ── */
        .typing-row {
            display: flex; align-items: flex-end; gap: 14px;
            justify-content: flex-start; padding-right: 15%;
        }
        .typing-bubble {
            background: #ffffff;
            border: 1.5px solid #e8e4df;
            border-radius: 4px 20px 20px 20px;
            padding: 16px 22px;
            display: inline-flex; gap: 6px; align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.07);
        }
        .typing-dot {
            width: 9px; height: 9px; border-radius: 50%;
            background: linear-gradient(135deg, #7c3aed, #2563eb);
            animation: bounce 1.2s infinite;
        }
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce {
            0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
            40% { transform: translateY(-7px); opacity: 1; }
        }

        /* ── FEEDBACK ── */
        .feedback-wrapper { padding-left: 56px; margin-top: 2px; }

        /* ── ALERTS ── */
        .stSuccess { background: #f0fdf4 !important; border: 1px solid #86efac !important; color: #166534 !important; border-radius: 10px !important; font-size: 0.86rem !important; }
        .stError { background: #fef2f2 !important; border: 1px solid #fca5a5 !important; color: #991b1b !important; border-radius: 10px !important; font-size: 0.86rem !important; }
        .stWarning { background: #fffbeb !important; border: 1px solid #fcd34d !important; color: #92400e !important; border-radius: 10px !important; font-size: 0.86rem !important; }
        .stInfo { background: #eff6ff !important; border: 1px solid #bfdbfe !important; color: #1e40af !important; border-radius: 10px !important; font-size: 0.86rem !important; }

        /* ── TEXT AREA ── */
        .stTextArea textarea {
            background: #ffffff !important; border: 1.5px solid #e0dbd4 !important;
            border-radius: 10px !important; color: #1a1a2e !important;
            font-family: 'Inter', sans-serif !important; font-size: 0.95rem !important;
        }
        .stTextArea textarea:focus { border-color: #7c3aed !important; box-shadow: 0 0 0 3px rgba(124,58,237,0.1) !important; }
        .stTextArea label { color: #888 !important; font-size: 0.72rem !important; font-weight: 600 !important; letter-spacing: 0.08em !important; text-transform: uppercase !important; }

        /* ── BUTTONS ── */
        .stButton > button {
            background: #f0ede8 !important; border: 1.5px solid #e0dbd4 !important;
            border-radius: 8px !important; color: #7c3aed !important;
            font-family: 'Inter', sans-serif !important; font-size: 0.82rem !important;
            font-weight: 600 !important; padding: 6px 16px !important; transition: all 0.2s !important;
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #7c3aed, #2563eb) !important;
            border-color: transparent !important; color: #fff !important;
            box-shadow: 0 4px 12px rgba(124,58,237,0.3) !important;
        }

        /* ── CHAT INPUT BOTTOM BAR — nuke all dark backgrounds ── */
        .stBottom { background-color: #f7f5f2 !important; }
        .stBottom > div { background-color: #f7f5f2 !important; }
        .stBottom > div > div { background-color: #f7f5f2 !important; }
        [data-testid="stBottom"] { background-color: #f7f5f2 !important; border-top: 1.5px solid #e8e4df !important; }
        [data-testid="stBottom"] > div { background-color: #f7f5f2 !important; }
        [data-testid="stBottom"] > div > div { background-color: #f7f5f2 !important; }
        [data-testid="stBottom"] * { background-color: transparent; }

        /* ── CHAT INPUT ── */
        .stChatInput { background: transparent !important; }
        .stChatInput > div {
            background: #ffffff !important;
            border: 2px solid #ddd8d2 !important;
            border-radius: 14px !important;
            box-shadow: 0 2px 14px rgba(0,0,0,0.08) !important;
            transition: border-color 0.2s, box-shadow 0.2s !important;
        }
        .stChatInput > div:focus-within {
            border-color: #7c3aed !important;
            box-shadow: 0 0 0 3px rgba(124,58,237,0.12) !important;
        }
        .stChatInput textarea {
            background: #ffffff !important;
            color: #1a1a2e !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 1.08rem !important;
            caret-color: #7c3aed !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            resize: none !important;
        }
        .stChatInput textarea::placeholder { color: #bbb5af !important; }
        .stChatInput > div > div {
            border: none !important;
            box-shadow: none !important;
            background: #ffffff !important;
        }
        .stChatInput button {
            background: linear-gradient(135deg, #7c3aed, #2563eb) !important;
            border-radius: 10px !important; color: #fff !important;
            box-shadow: 0 4px 12px rgba(124,58,237,0.3) !important;
            border: none !important;
        }

        /* ── DIVIDER ── */
        hr { border: none !important; border-top: 1px solid #e8e4df !important; margin: 8px 0 !important; }

        /* ── SCROLLBAR ── */
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: #f7f5f2; }
        ::-webkit-scrollbar-thumb { background: #d4c8f0; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #7c3aed; }

        footer { visibility: hidden; }
        #MainMenu { visibility: hidden; }
        header { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  SESSION ID
# ─────────────────────────────────────────────
def get_session_id():
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    return st.session_state.session_id

session_id = get_session_id()


# ─────────────────────────────────────────────
#  API HELPERS
# ─────────────────────────────────────────────
def api_call(method, url, **kwargs):
    def _show_error_popup(message):
        st.session_state["error_popup"] = {"visible": True, "message": message}
    try:
        response = getattr(requests, method)(url, **kwargs)
        try:
            response_data = response.json()
        except requests.exceptions.JSONDecodeError:
            response_data = {"message": "Invalid response format from server"}
        if response.ok:
            return True, response_data
        return False, response_data
    except requests.exceptions.ConnectionError:
        _show_error_popup("Connection error.")
        return False, {"message": "Connection error"}
    except requests.exceptions.Timeout:
        _show_error_popup("Request timed out.")
        return False, {"message": "Request timeout"}
    except Exception as e:
        _show_error_popup(f"Error: {str(e)}")
        return False, {"message": str(e)}


def api_call_stream(method, url, **kwargs):
    def _show_error_popup(message):
        st.session_state["error_popup"] = {"visible": True, "message": message}
    try:
        response = getattr(requests, method)(url, **kwargs)
        return response.iter_lines()
    except requests.exceptions.ConnectionError:
        _show_error_popup("Connection error.")
        return None
    except requests.exceptions.Timeout:
        _show_error_popup("Request timed out.")
        return None
    except Exception as e:
        _show_error_popup(f"Error: {str(e)}")
        return None


def submit_feedback(feedback_type=None, feedback_text=""):
    def _feedback_score(t):
        return 1 if t == "positive" else (0 if t == "negative" else None)
    feedback_data = {
        "feedback_score": _feedback_score(feedback_type),
        "feedback_text": feedback_text,
        "trace_id": st.session_state.trace_id,
        "thread_id": session_id,
        "feedback_source_type": "api"
    }
    logger.info(f"Feedback data: {feedback_data}")
    return api_call("post", f"{config.API_URL}/submit_feedback", json=feedback_data)


def bot_bubble(text):
    return f"""
    <div class="msg-row-bot">
        <div class="msg-avatar-bot">🛍️</div>
        <div class="msg-bubble-bot">{text}</div>
    </div>"""

def user_bubble(text):
    return f"""
    <div class="msg-row-user">
        <div class="msg-bubble-user">{text}</div>
        <div class="msg-avatar-user">👤</div>
    </div>"""

def typing_indicator():
    return """
    <div class="typing-row">
        <div class="msg-avatar-bot">🛍️</div>
        <div class="typing-bubble">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    </div>"""


# ─────────────────────────────────────────────
#  SESSION STATE INIT
# ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hey there! 👋 I'm <b>Nuvex</b>, your AI-powered shopping assistant. Ask me about products, deals, or comparisons — I'll find the best options for you!"}]

if "used_context" not in st.session_state:
    st.session_state.used_context = []

if "shopping_cart" not in st.session_state:
    st.session_state.shopping_cart = []

if "latest_feedback" not in st.session_state:
    st.session_state.latest_feedback = None

if "show_feedback_box" not in st.session_state:
    st.session_state.show_feedback_box = False

if "feedback_submission_status" not in st.session_state:
    st.session_state.feedback_submission_status = None

if "trace_id" not in st.session_state:
    st.session_state.trace_id = None


# ─────────────────────────────────────────────
#  NAVBAR
# ─────────────────────────────────────────────
st.markdown("""
    <div id="nuvex-header">
        <div>
            <div class="nuvex-logo">NUVEX</div>
            <div class="nuvex-tagline">✦ AI-Powered Shopping Assistant</div>
        </div>
        <div class="nuvex-badge">✦ Powered by RAG + AI</div>
    </div>
""", unsafe_allow_html=True)





# ─────────────────────────────────────────────
#  CHAT HISTORY
# ─────────────────────────────────────────────
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

for idx, message in enumerate(st.session_state.messages):
    if message["role"] == "assistant":
        st.markdown(bot_bubble(message["content"]), unsafe_allow_html=True)
    else:
        st.markdown(user_bubble(message["content"]), unsafe_allow_html=True)

    is_latest_assistant = (
        message["role"] == "assistant" and
        idx == len(st.session_state.messages) - 1 and
        idx > 0
    )

    if is_latest_assistant:
        st.markdown('<div class="feedback-wrapper">', unsafe_allow_html=True)
        feedback_key = f"feedback_{len(st.session_state.messages)}"
        feedback_result = st.feedback("thumbs", key=feedback_key)

        if feedback_result is not None:
            feedback_type = "positive" if feedback_result == 1 else "negative"
            if st.session_state.latest_feedback != feedback_type:
                with st.spinner("Submitting feedback..."):
                    status, response = submit_feedback(feedback_type=feedback_type)
                    if status:
                        st.session_state.latest_feedback = feedback_type
                        st.session_state.feedback_submission_status = "success"
                        st.session_state.show_feedback_box = (feedback_type == "negative")
                    else:
                        st.session_state.feedback_submission_status = "error"
                        st.error("Failed to submit feedback.")
                st.rerun()

        if st.session_state.latest_feedback and st.session_state.feedback_submission_status == "success":
            if st.session_state.latest_feedback == "positive":
                st.success("✅ Thank you for your positive feedback!")
            elif st.session_state.latest_feedback == "negative" and not st.session_state.show_feedback_box:
                st.success("✅ Thank you for your feedback!")
        elif st.session_state.feedback_submission_status == "error":
            st.error("❌ Failed to submit feedback.")

        if st.session_state.show_feedback_box:
            st.markdown("**Want to tell us more? (Optional)**")
            feedback_text = st.text_area(
                "Additional feedback (optional)",
                key=f"feedback_text_{len(st.session_state.messages)}",
                placeholder="Please describe what was wrong...",
                height=100
            )
            col_send, col_spacer, col_close = st.columns([3, 5, 2])
            with col_send:
                if st.button("Send Details", key=f"send_additional_{len(st.session_state.messages)}"):
                    if feedback_text.strip():
                        with st.spinner("Submitting..."):
                            status, response = submit_feedback(feedback_text=feedback_text)
                            if status:
                                st.success("✅ Feedback recorded.")
                                st.session_state.show_feedback_box = False
                            else:
                                st.error("❌ Failed.")
                    else:
                        st.warning("Please enter some text.")
                    st.rerun()
            with col_close:
                if st.button("Close", key=f"close_feedback_{len(st.session_state.messages)}"):
                    st.session_state.show_feedback_box = False
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  CHAT INPUT
# ─────────────────────────────────────────────
if prompt := st.chat_input("Ask Nuvex about products, deals, comparisons..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(user_bubble(prompt), unsafe_allow_html=True)

    typing_placeholder = st.empty()
    typing_placeholder.markdown(typing_indicator(), unsafe_allow_html=True)

    stream = api_call_stream(
        "post",
        f"{config.API_URL}/agent",
        json={"query": prompt, "thread_id": session_id},
        stream=True,
        headers={"Accept": "text/event-stream"}
    )

    if not stream:
        typing_placeholder.empty()
        err_msg = "Sorry, I could not connect to the server."
        st.markdown(bot_bubble(err_msg), unsafe_allow_html=True)
        st.session_state.messages.append({"role": "assistant", "content": err_msg})
    else:
        answer = None
        for line in stream:
            if not isinstance(line, bytes):
                continue
            line_text = line.decode("utf-8")
            if line_text.startswith("data: "):
                data = line_text[6:]
                try:
                    output = json.loads(data)
                    if output["type"] == "final_result":
                        answer = output["data"]["answer"]
                        used_context = output["data"]["used_context"]
                        trace_id = output["data"]["trace_id"]
                        shopping_cart = output["data"]["shopping_cart"]

                        st.session_state.used_context = used_context
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                        st.session_state.trace_id = trace_id
                        st.session_state.shopping_cart = shopping_cart
                        st.session_state.latest_feedback = None
                        st.session_state.show_feedback_box = False
                        st.session_state.feedback_submission_status = None
                        break
                except json.JSONDecodeError:
                    pass

        typing_placeholder.empty()
        if answer:
            st.markdown(bot_bubble(answer), unsafe_allow_html=True)

    st.rerun()