import streamlit as st
import requests
from chat_ui.core.config import config

st.set_page_config(
    page_title="Nuvex — AI Shopping Bot",
    page_icon="🛍️",
    layout="wide",
)

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=DM+Sans:wght@300;400;500&display=swap');

        *, *::before, *::after { box-sizing: border-box; }

        /* ── Base ── */
        .stApp {
            background-color: #faf7f4;
            color: #1a1208;
            font-family: 'DM Sans', sans-serif;
        }

        /* Subtle dot pattern background */
        .stApp::before {
            content: '';
            position: fixed;
            inset: 0;
            background-image: radial-gradient(circle, #d4b896 1px, transparent 1px);
            background-size: 28px 28px;
            pointer-events: none;
            opacity: 0.18;
            z-index: 0;
        }

        /* ── Sidebar ── */
        section[data-testid="stSidebar"] {
            background-color: #1a1208 !important;
            border-right: none !important;
        }

        section[data-testid="stSidebar"] * {
            color: #c9b49a !important;
            font-family: 'DM Sans', sans-serif !important;
        }

        /* Sidebar brand */
        .sidebar-brand {
            font-family: 'Playfair Display', serif !important;
            font-size: 1.6rem !important;
            font-weight: 900 !important;
            color: #f5e6d0 !important;
            letter-spacing: 0.04em;
            line-height: 1;
        }

        .sidebar-brand span {
            color: #e8a44a !important;
        }

        .sidebar-tagline {
            font-size: 0.65rem !important;
            color: #5a4530 !important;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            margin-top: 4px;
        }

        /* Sidebar labels */
        section[data-testid="stSidebar"] .stSelectbox label {
            font-size: 0.68rem !important;
            letter-spacing: 0.14em !important;
            text-transform: uppercase !important;
            color: #5a4530 !important;
            font-weight: 500 !important;
        }

        section[data-testid="stSidebar"] div[data-baseweb="select"] {
            background-color: #251a0e !important;
            border: 1px solid #3d2e1a !important;
            border-radius: 6px !important;
        }

        section[data-testid="stSidebar"] div[data-baseweb="select"] * {
            background-color: transparent !important;
            color: #c9b49a !important;
        }

        /* Active model pill in sidebar */
        .model-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: #251a0e;
            border: 1px solid #3d2e1a;
            border-radius: 20px;
            padding: 0.3rem 0.8rem;
            font-size: 0.67rem;
            letter-spacing: 0.08em;
            color: #e8a44a !important;
            text-transform: uppercase;
            margin-top: 0.2rem;
        }

        /* ── Main app header ── */
        .app-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1.8rem 0 1.6rem 0;
            border-bottom: 2px solid #1a1208;
            margin-bottom: 1.8rem;
        }

        .header-left h1 {
            font-family: 'Playfair Display', serif !important;
            font-size: 2.6rem !important;
            font-weight: 900 !important;
            color: #1a1208 !important;
            letter-spacing: 0.01em !important;
            margin: 0 !important;
            line-height: 1 !important;
        }

        .header-left h1 span {
            color: #c47f1a;
            font-style: italic;
        }

        .header-left p {
            font-size: 0.7rem !important;
            color: #9a7f5a !important;
            letter-spacing: 0.2em !important;
            text-transform: uppercase !important;
            margin-top: 0.4rem !important;
            font-weight: 400 !important;
        }

        .header-badge {
            background: #1a1208;
            color: #e8a44a;
            font-size: 0.65rem;
            font-family: 'DM Sans', sans-serif;
            font-weight: 500;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            padding: 0.5rem 1.1rem;
            border-radius: 20px;
        }

        /* ── Chat messages ── */
        .stChatMessage {
            background-color: transparent !important;
            border: none !important;
            padding: 0.5rem 0 !important;
        }

        /* User bubble */
        .stChatMessage[data-testid="chat-message-user"] {
            background-color: #1a1208 !important;
            border-radius: 16px 16px 4px 16px !important;
            padding: 1rem 1.4rem !important;
            margin-left: 4rem !important;
            margin-right: 0.5rem !important;
        }

        .stChatMessage[data-testid="chat-message-user"] p {
            color: #f5e6d0 !important;
        }

        /* Assistant bubble */
        .stChatMessage[data-testid="chat-message-assistant"] {
            background-color: #ffffff !important;
            border: 1.5px solid #e8ddd0 !important;
            border-radius: 16px 16px 16px 4px !important;
            padding: 1rem 1.4rem !important;
            margin-right: 4rem !important;
            margin-left: 0.5rem !important;
            box-shadow: 0 2px 12px rgba(26, 18, 8, 0.05);
        }

        .stChatMessage[data-testid="chat-message-assistant"] p {
            color: #2d1f0e !important;
        }

        /* Avatar */
        .stChatMessage .stAvatar {
            background-color: #e8a44a !important;
            border: none !important;
        }

        /* Message text */
        .stChatMessage p {
            font-family: 'DM Sans', sans-serif !important;
            font-size: 0.92rem !important;
            line-height: 1.75 !important;
        }

        /* ── Chat input ── */
        .stChatInput {
            background-color: transparent !important;
        }

        .stChatInput > div {
            background-color: #ffffff !important;
            border: 2px solid #1a1208 !important;
            border-radius: 12px !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }

        .stChatInput > div:focus-within {
            border-color: #c47f1a !important;
            box-shadow: 0 0 0 3px rgba(232, 164, 74, 0.15) !important;
        }

        .stChatInput textarea {
            background-color: transparent !important;
            color: #1a1208 !important;
            font-family: 'DM Sans', sans-serif !important;
            font-size: 0.92rem !important;
        }

        .stChatInput textarea::placeholder {
            color: #b8a08a !important;
        }

        /* ── Divider ── */
        hr {
            border-color: #3d2e1a !important;
            margin: 1rem 0 !important;
        }

        /* ── Scrollbar ── */
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #faf7f4; }
        ::-webkit-scrollbar-thumb { background: #d4b896; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #c47f1a; }

        footer { visibility: hidden; }
        #MainMenu { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)


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


with st.sidebar:
    st.markdown("""
        <div style="padding: 0.5rem 0 0.2rem 0;">
            <div class="sidebar-brand">Nu<span>vex</span></div>
            <div class="sidebar-tagline">🛍 AI Shopping Assistant</div>
        </div>
    """, unsafe_allow_html=True)
    st.divider()

    provider = st.selectbox("Provider", ["OpenAI", "Groq", "Google"])
    if provider == "OpenAI":
        model_name = st.selectbox("Model", ["gpt-5-nano", "gpt-5-mini"])
    elif provider == "Groq":
        model_name = st.selectbox("Model", ["llama-3.3-70b-versatile"])
    else:
        model_name = st.selectbox("Model", ["gemini-2.5-flash"])

    st.session_state.provider = provider
    st.session_state.model_name = model_name

    st.divider()
    st.markdown(
        f'<div class="model-pill">⚡ {provider} &nbsp;/&nbsp; {model_name}</div>',
        unsafe_allow_html=True
    )


st.markdown("""
    <div class="app-header">
        <div class="header-left">
            <h1>Nu<span>vex</span></h1>
            <p>Your AI-powered shopping companion</p>
        </div>
        <div class="header-badge">🛍 Shop Smarter</div>
    </div>
""", unsafe_allow_html=True)


if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hey there! 👋 I'm **Nuvex**, your personal AI shopping assistant. Tell me what you're looking for — deals, comparisons, recommendations — I've got you covered!"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask Nuvex anything — deals, products, comparisons..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        output = api_call(
            "post",
            f"{config.API_URL}/chat",
            json={
                "provider": st.session_state.provider,
                "models_name": st.session_state.model_name,
                "messages": st.session_state.messages,
            }
        )
        response_data = output[1]
        answer = response_data["message"]
        st.write(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})