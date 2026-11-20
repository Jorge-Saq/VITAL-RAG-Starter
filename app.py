"""Working baseline chatbot with an optional RAG toggle."""
import streamlit as st
from llm import ask_llm
from rag import retrieve, build_context

st.title("Project VITAL — LLM + RAG Lab")
use_rag = st.sidebar.toggle("Enable RAG", value=False)
if "messages" not in st.session_state:
    st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("sources"):
            st.caption(msg["sources"])
question = st.chat_input("Ask a question")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)
    sources = "RAG off"
    try:
        if use_rag:
            hits = retrieve(question)
            context = build_context(hits)  # "" when nothing matched; never None
            names = ", ".join(name for name, _, _ in hits)
            sources = f"Sources: {names}" if names else "Sources: none retrieved"
            answer = ask_llm(question, context)
        else:
            answer = ask_llm(question)
    except Exception as exc:
        answer = f"Ollama unavailable: {exc}"
    with st.chat_message("assistant"):
        st.write(answer)
        st.caption(sources)
    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sources": sources}
    )
