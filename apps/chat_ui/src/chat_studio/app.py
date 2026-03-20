import streamlit as st
import requests
from chat_ui.core.config import config

st.set_page_config(
    page_title="LLM Chat Studio",
    page_icon="💬",
    layout="wide",
)

st.markdown("""
    <style>
        /* Main background */
        .stApp {
            background-color: #0f1117;
            color: #e0e0e0;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #1a1d27;
            border-right: 1px solid #2e3250;
        }

        section[data-testid="stSidebar"] * {
            color: #c9cfe8 !important;
        }

        /* Sidebar title */
        .sidebar-title {
            font-size: 1.3rem;
            font-weight: 700;
            color: #7c9ef8 !important;
            margin-bottom: 1rem;
            letter-spacing: 0.04em;
        }

        /* Chat input box */
        .stChatInput textarea {
            background-color: #1e2130 !important;
            color: #e0e0e0 !important;
            border: 1px solid #3a3f5c !important;
            border-radius: 10px !important;
        }

        /* Chat messages */
        .stChatMessage {
            background-color: #1e2130 !important;
            border-radius: 10px !important;
            border: 1px solid #2a2f4a !important;
        }

        /* Selectbox */
        .stSelectbox div[data-baseweb="select"] {
            background-color: #1e2130 !important;
            border-color: #3a3f5c !important;
        }

        /* App header */
        .app-header {
            text-align: center;
            padding: 0.5rem 0 1.5rem 0;
        }
        .app-header h1 {
            font-size: 2rem;
            font-weight: 700;
            color: #7c9ef8;
            letter-spacing: 0.03em;
        }
        .app-header p {
            color: #7a82a8;
            font-size: 0.9rem;
        }

        /* Hide default Streamlit footer */
        footer { visibility: hidden; }
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
    st.markdown('<div class="sidebar-title">⚙️ Configuration</div>', unsafe_allow_html=True)
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
    st.markdown(f"<small style='color:#4a5080;'>Active: **{provider}** / {model_name}</small>", unsafe_allow_html=True)


st.markdown("""
    <div class="app-header">
        <h1>💬 LLM Chat Studio</h1>
        <p>Chat with leading AI models — OpenAI, Groq & Google</p>
    </div>
""", unsafe_allow_html=True)


if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I assist you today?"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Type your message here..."):
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
