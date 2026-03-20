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
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  STYLES
# ─────────────────────────────────────────────
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');

        *, *::before, *::after { box-sizing: border-box; }

        /* ── BASE ── */
        html, body, .stApp {
            background-color: #090c12 !important;
            color: #dde4f0 !important;
            font-family: 'DM Sans', sans-serif !important;
        }
        .block-container {
            padding-top: 0 !important;
            padding-bottom: 5rem !important;
        }

        /* ── SIDEBAR ── */
        section[data-testid="stSidebar"] {
            background-color: #0d1117 !important;
            border-right: 1px solid #1a2235 !important;
        }
        section[data-testid="stSidebar"] > div {
            padding: 1.2rem 1rem !important;
        }
        section[data-testid="stSidebar"] * {
            font-family: 'DM Sans', sans-serif !important;
        }
        section[data-testid="stSidebar"] .stCaption,
        section[data-testid="stSidebar"] .stCaption p {
            color: #8a9bb8 !important;
            font-size: 0.78rem !important;
        }
        section[data-testid="stSidebar"] hr {
            border: none !important;
            border-top: 1px solid #1a2235 !important;
            margin: 10px 0 !important;
        }
        section[data-testid="stSidebar"] img {
            border-radius: 8px !important;
            border: 1px solid #1e2d42 !important;
        }
        section[data-testid="stSidebar"] .stAlert {
            background: #111827 !important;
            border: 1px solid #1e2d42 !important;
            border-radius: 6px !important;
            font-size: 0.78rem !important;
        }
        section[data-testid="stSidebar"] .stAlert p {
            color: #4a5a7a !important;
        }

        /* Sidebar tabs */
        .stTabs [data-baseweb="tab-list"] {
            background: transparent !important;
            gap: 4px !important;
        }
        .stTabs [data-baseweb="tab"] {
            background: #111827 !important;
            border: 1px solid #1e2d42 !important;
            border-radius: 6px !important;
            color: #6b7fa3 !important;
            font-size: 0.74rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.05em !important;
            padding: 6px 12px !important;
        }
        .stTabs [aria-selected="true"] {
            background: #39ff8a18 !important;
            border-color: #39ff8a55 !important;
            color: #39ff8a !important;
        }
        .stTabs [data-baseweb="tab-panel"] {
            padding: 0.8rem 0 0 0 !important;
        }

        /* ── NAVBAR ── */
        .nuvex-navbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem 0 0.9rem 0;
            border-bottom: 1.5px solid #151f30;
            margin-bottom: 1.2rem;
        }
        .nuvex-logo {
            font-family: 'Bebas Neue', sans-serif;
            font-size: 2rem;
            color: #eef2ff;
            letter-spacing: 0.12em;
            line-height: 1;
        }
        .nuvex-logo em { color: #39ff8a; font-style: normal; }
        .nuvex-tagline {
            font-size: 0.6rem;
            font-weight: 600;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            color: #2a3a55;
            margin-top: 3px;
        }
        .nuvex-badge {
            background: #39ff8a;
            color: #090c12;
            font-size: 0.63rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            padding: 5px 13px;
            border-radius: 5px;
        }

        /* ── CHAT MESSAGES ── */
        .stChatMessage {
            background: transparent !important;
            border: none !important;
            padding: 3px 0 !important;
        }
        [data-testid="chat-message-user"] {
            background: #131929 !important;
            border: 1.5px solid #1e2d45 !important;
            border-radius: 14px 14px 4px 14px !important;
            padding: 13px 17px !important;
            margin-left: 3.5rem !important;
            margin-bottom: 8px !important;
        }
        [data-testid="chat-message-user"] p,
        [data-testid="chat-message-user"] span {
            color: #c8d4ee !important;
            font-size: 0.92rem !important;
            line-height: 1.7 !important;
        }
        [data-testid="chat-message-assistant"] {
            background: #0b1512 !important;
            border: 1.5px solid #1a3020 !important;
            border-left: 3px solid #39ff8a !important;
            border-radius: 4px 14px 14px 14px !important;
            padding: 13px 17px !important;
            margin-right: 3.5rem !important;
            margin-bottom: 8px !important;
        }
        [data-testid="chat-message-assistant"] p,
        [data-testid="chat-message-assistant"] span {
            color: #c8ecd6 !important;
            font-size: 0.92rem !important;
            line-height: 1.7 !important;
        }
        [data-testid="chat-message-user"] .stAvatar,
        [data-testid="chat-message-assistant"] .stAvatar {
            background: #131929 !important;
            border: 1.5px solid #1e2d45 !important;
        }

        /* ── FEEDBACK ── */
        .stFeedback { margin-top: 6px !important; }

        /* ── ALERTS ── */
        .stSuccess {
            background: #0d1f14 !important;
            border: 1px solid #39ff8a44 !important;
            color: #7dffb0 !important;
            border-radius: 8px !important;
            font-size: 0.82rem !important;
        }
        .stError {
            background: #1f0d0d !important;
            border: 1px solid #ff4a4a44 !important;
            color: #ff9a9a !important;
            border-radius: 8px !important;
            font-size: 0.82rem !important;
        }
        .stWarning {
            background: #1a1505 !important;
            border: 1px solid #f0b44444 !important;
            color: #f0c070 !important;
            border-radius: 8px !important;
            font-size: 0.82rem !important;
        }

        /* ── TEXT AREA ── */
        .stTextArea textarea {
            background: #0f1520 !important;
            border: 1.5px solid #1e2d42 !important;
            border-radius: 8px !important;
            color: #c8d4ee !important;
            font-family: 'DM Sans', sans-serif !important;
            font-size: 0.88rem !important;
        }
        .stTextArea textarea:focus {
            border-color: #39ff8a !important;
            box-shadow: 0 0 0 2px #39ff8a18 !important;
        }
        .stTextArea label {
            color: #4a5a7a !important;
            font-size: 0.72rem !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
        }

        /* ── BUTTONS ── */
        .stButton > button {
            background: transparent !important;
            border: 1.5px solid #1e2d42 !important;
            border-radius: 7px !important;
            color: #7a9abf !important;
            font-family: 'DM Sans', sans-serif !important;
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.06em !important;
            padding: 5px 14px !important;
            transition: all 0.15s !important;
        }
        .stButton > button:hover {
            border-color: #39ff8a !important;
            color: #39ff8a !important;
            background: #39ff8a0a !important;
        }

        /* ── CHAT INPUT ── */
        .stChatInput > div {
            background-color: #0f1520 !important;
            border: 2px solid #1e2d42 !important;
            border-radius: 12px !important;
            transition: border-color 0.2s, box-shadow 0.2s !important;
        }
        .stChatInput > div:focus-within {
            border-color: #39ff8a !important;
            box-shadow: 0 0 0 3px #39ff8a12 !important;
        }
        .stChatInput textarea {
            background: transparent !important;
            color: #dde4f0 !important;
            font-family: 'DM Sans', sans-serif !important;
            font-size: 0.92rem !important;
            caret-color: #39ff8a !important;
        }
        .stChatInput textarea::placeholder { color: #2a3a55 !important; }
        .stChatInput button {
            background: #39ff8a !important;
            border-radius: 8px !important;
            color: #090c12 !important;
        }

        /* ── SPINNER ── */
        .stSpinner > div { border-top-color: #39ff8a !important; }

        /* ── SCROLLBAR ── */
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #090c12; }
        ::-webkit-scrollbar-thumb { background: #1e2d42; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #39ff8a66; }

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
        st.session_state["error_popup"] = {
            "visible": True,
            "message": message,
        }

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
        _show_error_popup("Connection error. Please check your network connection.")
        return False, {"message": "Connection error"}
    except requests.exceptions.Timeout:
        _show_error_popup("The request timed out. Please try again later.")
        return False, {"message": "Request timeout"}
    except Exception as e:
        _show_error_popup(f"An unexpected error occurred: {str(e)}")
        return False, {"message": str(e)}


def api_call_stream(method, url, **kwargs):

    def _show_error_popup(message):
        st.session_state["error_popup"] = {
            "visible": True,
            "message": message,
        }

    try:
        response = getattr(requests, method)(url, **kwargs)
        return response.iter_lines()

    except requests.exceptions.ConnectionError:
        _show_error_popup("Connection error. Please check your network connection.")
        return False, {"message": "Connection error"}
    except requests.exceptions.Timeout:
        _show_error_popup("The request timed out. Please try again later.")
        return False, {"message": "Request timeout"}
    except Exception as e:
        _show_error_popup(f"An unexpected error occurred: {str(e)}")
        return False, {"message": str(e)}


def submit_feedback(feedback_type=None, feedback_text=""):
    """Submit feedback to the API endpoint"""

    def _feedback_score(feedback_type):
        if feedback_type == "positive":
            return 1
        elif feedback_type == "negative":
            return 0
        else:
            return None

    feedback_data = {
        "feedback_score": _feedback_score(feedback_type),
        "feedback_text": feedback_text,
        "trace_id": st.session_state.trace_id,
        "thread_id": session_id,
        "feedback_source_type": "api"
    }

    logger.info(f"Feedback data: {feedback_data}")

    status, response = api_call("post", f"{config.API_URL}/submit_feedback", json=feedback_data)
    return status, response


# ─────────────────────────────────────────────
#  SESSION STATE INIT
# ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I assist you today?"}]

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
    <div class="nuvex-navbar">
        <div>
            <div class="nuvex-logo">NU<em>VEX</em></div>
            <div class="nuvex-tagline">🛍 AI Shopping Bot</div>
        </div>
        <div class="nuvex-badge">Shop Smarter with AI</div>
    </div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    suggestions_tab, shopping_cart_tab = st.tabs(["🔍 Suggestions", "🛒 Shopping Cart"])

    with suggestions_tab:
        if st.session_state.used_context:
            for idx, item in enumerate(st.session_state.used_context):
                st.caption(item.get('description', 'No description'))
                if 'image_url' in item:
                    st.image(item["image_url"], width=250)
                st.caption(f"Price: {item['price']} USD")
                st.divider()
        else:
            st.info("No suggestions yet")

    with shopping_cart_tab:
        if st.session_state.shopping_cart:
            for idx, item in enumerate(st.session_state.shopping_cart):
                st.caption(item.get('description', 'No description'))
                if 'product_image_url' in item:
                    st.image(item["product_image_url"], width=250)
                st.caption(f"Price: {item['price']} {item['currency']}")
                st.caption(f"Quantity: {item['quantity']}")
                st.caption(f"Total price: {item['total_price']} {item['currency']}")
                st.divider()
        else:
            st.info("Your cart is empty")


# ─────────────────────────────────────────────
#  CHAT HISTORY
# ─────────────────────────────────────────────
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        is_latest_assistant = (
            message["role"] == "assistant" and
            idx == len(st.session_state.messages) - 1 and
            idx > 0
        )

        if is_latest_assistant:
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
                            st.error("Failed to submit feedback. Please try again.")
                    st.rerun()

            if st.session_state.latest_feedback and st.session_state.feedback_submission_status == "success":
                if st.session_state.latest_feedback == "positive":
                    st.success("✅ Thank you for your positive feedback!")
                elif st.session_state.latest_feedback == "negative" and not st.session_state.show_feedback_box:
                    st.success("✅ Thank you for your feedback!")
            elif st.session_state.feedback_submission_status == "error":
                st.error("❌ Failed to submit feedback. Please try again.")

            if st.session_state.show_feedback_box:
                st.markdown("**Want to tell us more? (Optional)**")
                st.caption("Your negative feedback has already been recorded. You can optionally provide additional details below.")

                feedback_text = st.text_area(
                    "Additional feedback (optional)",
                    key=f"feedback_text_{len(st.session_state.messages)}",
                    placeholder="Please describe what was wrong with this response...",
                    height=100
                )

                col_send, col_spacer, col_close = st.columns([3, 5, 2])
                with col_send:
                    if st.button("Send Additional Details", key=f"send_additional_{len(st.session_state.messages)}"):
                        if feedback_text.strip():
                            with st.spinner("Submitting additional feedback..."):
                                status, response = submit_feedback(feedback_text=feedback_text)
                                if status:
                                    st.success("✅ Thank you! Your additional feedback has been recorded.")
                                    st.session_state.show_feedback_box = False
                                else:
                                    st.error("❌ Failed to submit additional feedback. Please try again.")
                        else:
                            st.warning("Please enter some feedback text before submitting.")
                        st.rerun()

                with col_close:
                    if st.button("Close", key=f"close_feedback_{len(st.session_state.messages)}"):
                        st.session_state.show_feedback_box = False
                        st.rerun()


# ─────────────────────────────────────────────
#  CHAT INPUT
# ─────────────────────────────────────────────
if prompt := st.chat_input("Ask Nuvex about products, deals, comparisons..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):

        status_placeholder = st.empty()
        message_placeholder = st.empty()

        for line in api_call_stream(
            "post",
            f"{config.API_URL}/agent",
            json={"query": prompt, "thread_id": session_id},
            stream=True,
            headers={"Accept": "text/event-stream"}
        ):
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

                        status_placeholder.empty()
                        message_placeholder.markdown(answer)
                        break

                except json.JSONDecodeError:
                    status_placeholder.markdown(f"*{data}*")

    st.rerun()