import uuid
import streamlit as st
from agent.agent_loop import run_turn

st.title("Wellness Assistant")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "chat" not in st.session_state:
    st.session_state.chat = []

variant = st.sidebar.radio("Model variant", ["frontier", "oss"])
if st.sidebar.button("Reset conversation"):
    st.session_state.chat = []
    st.session_state.session_id = str(uuid.uuid4())

for msg in st.session_state.chat:
    st.chat_message(msg["role"]).write(msg["content"])

user_msg = st.chat_input("Ask about diet, exercise, sleep...")
if user_msg:
    st.chat_message("user").write(user_msg)
    st.session_state.chat.append({"role": "user", "content": user_msg})

    result = run_turn(st.session_state.session_id, user_msg, variant)
    st.chat_message("assistant").write(result["reply"])
    st.session_state.chat.append({"role": "assistant", "content": result["reply"]})

    if result["tool_calls"]:
        with st.expander("tool calls"):
            st.json(result["tool_calls"])
