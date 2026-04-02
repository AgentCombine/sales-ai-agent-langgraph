import json
import uuid

import streamlit as st

from virtual_sales_agent.runtime import AgentRuntime
from virtual_sales_agent import settings


def set_page_config() -> None:
    st.set_page_config(
        page_title="Virtual Sales Agent Chat",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def set_page_style() -> None:
    st.markdown(
        f"""
        <style>
        {open('assets/style.css').read()}
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_session_state() -> None:
    ss = st.session_state

    ss.customer_id = ss.get("customer_id") or settings.CUSTOMER_ID or str(uuid.uuid4())
    ss.thread_id = ss.get("thread_id") or settings.THREAD_ID or str(uuid.uuid4())
    ss.messages = ss.get("messages") or []
    ss.pending_tool = ss.get("pending_tool")

    runtime = ss.get("runtime")
    runtime_config = runtime.config if runtime else {"configurable": {}}
    runtime_customer_id = runtime_config["configurable"].get("customer_id")
    runtime_thread_id = runtime_config["configurable"].get("thread_id")
    if runtime is None or runtime_customer_id != ss.customer_id or runtime_thread_id != ss.thread_id:
        ss.runtime = AgentRuntime.get_or_create(ss.customer_id, ss.thread_id)


def setup_sidebar() -> None:
    ss = st.session_state

    with st.sidebar:
        st.markdown("## Virtual Sales Agent")
        st.markdown("- 🛒 Browse products")
        st.markdown("- 📦 Place orders")
        st.markdown("- 🚚 Track orders")
        st.markdown("- 🎯 Recommendations")
        st.markdown("---")
        if st.button("🔄 Start New Chat", use_container_width=True):
            ss.thread_id = str(uuid.uuid4())
            ss.messages = []
            ss.pending_tool = None
            ss.runtime = AgentRuntime.get_or_create(ss.customer_id, ss.thread_id)
            st.rerun()


def display_chat_history() -> None:
    ss = st.session_state

    if not ss.messages:
        st.markdown("### 👋 Welcome! How can I assist you today?")
    for message in ss.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])


def render_pending_approval(runtime: AgentRuntime) -> None:
    ss = st.session_state
    pending_tool = ss.pending_tool
    if pending_tool is None:
        return

    st.warning("The assistant wants to perform a sensitive action.")
    with st.expander("View function details", expanded=True):
        st.info(f"Function: **{pending_tool['name']}**")
        args_text = json.dumps(pending_tool.get("args", {}), indent=2)
        st.code(args_text, language="json")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Approve"):
            result = runtime.approve()
            assistant_message = result["assistant_message"]
            if assistant_message:
                ss.messages.append({"role": "assistant", "content": assistant_message})
            ss.pending_tool = None
            st.rerun()

    with col2:
        reason = st.text_input("Reason for denial")
        if st.button("❌ Deny"):
            deny_reason = reason or "No reason provided"
            result = runtime.deny(deny_reason)
            assistant_message = result["assistant_message"]
            if assistant_message:
                ss.messages.append({"role": "assistant", "content": assistant_message})
            ss.pending_tool = None
            st.rerun()


def run_ui() -> None:
    ss = st.session_state

    set_page_config()
    set_page_style()
    initialize_session_state()
    setup_sidebar()

    runtime = ss.runtime

    display_chat_history()
    render_pending_approval(runtime)

    prompt = st.chat_input("What would you like to order?")
    if prompt is None:
        return

    ss.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.spinner("Thinking..."):
        result = runtime.chat(prompt)

    assistant_message = result["assistant_message"]
    if assistant_message:
        ss.messages.append({"role": "assistant", "content": assistant_message})
        with st.chat_message("assistant"):
            st.write(assistant_message)

    if result["status"] == "needs_approval":
        ss.pending_tool = result["tool_call"]
        st.rerun()


run_ui()
