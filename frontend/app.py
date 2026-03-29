# frontend/app.py

import streamlit as st
import requests
from pathlib import Path

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Legal RAG Assistant",
    page_icon="⚖️",
    layout="wide"
)

# ── API URL ───────────────────────────────────────────────────
API_URL = "http://127.0.0.1:8000"

# ── Header ───────────────────────────────────────────────────
st.title("⚖️ Legal Document Assistant")
st.markdown("Upload a legal document and ask questions about it in plain English.")
st.divider()

# ── Two columns layout ───────────────────────────────────────
col1, col2 = st.columns([1, 2])

# ════════════════════════════════════════════════
# LEFT COLUMN — Upload + Documents
# ════════════════════════════════════════════════
with col1:
    st.subheader("📄 Upload Document")

    uploaded_file = st.file_uploader(
        "Upload a PDF contract or legal document",
        type=["pdf"]
    )

    if uploaded_file:
        if st.button("📥 Ingest Document", use_container_width=True):
            with st.spinner("Reading and embedding document..."):
                response = requests.post(
                    f"{API_URL}/ingest",
                    files={"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                )
                if response.status_code == 200:
                    data = response.json()
                    st.success(f"✅ {data['message']}")
                    st.info(f"📦 Created {data['chunks']} searchable chunks")
                else:
                    st.error("❌ Failed to ingest document")

    st.divider()

    # ── List ingested documents ───────────────────────────────
    st.subheader("📚 Ingested Documents")
    if st.button("🔄 Refresh List", use_container_width=True):
        response = requests.get(f"{API_URL}/documents")
        if response.status_code == 200:
            docs = response.json()["documents"]
            if docs:
                for doc in docs:
                    st.markdown(f"- 📄 `{doc}`")
            else:
                st.info("No documents ingested yet")

# ════════════════════════════════════════════════
# RIGHT COLUMN — Chat Interface
# ════════════════════════════════════════════════
with col2:
    st.subheader("💬 Ask Questions")

    # ── Initialize chat history ───────────────────────────────
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # ── Display chat history ──────────────────────────────────
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "sources" in msg:
                with st.expander("📎 Sources"):
                    for s in msg["sources"]:
                        st.markdown(f"**📄 {s['source']}** — {s['citation']}")
                        st.caption(f"*\"{s['excerpt']}\"*")
    # ── Chat input ────────────────────────────────────────────
    question = st.chat_input("Ask anything about your document...")

    if question:
        # Show user message
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Get answer from API
        with st.chat_message("assistant"):
            with st.spinner("Searching document..."):
                response = requests.post(
                    f"{API_URL}/ask",
                    json={"question": question}
                )
                if response.status_code == 200:
                    data     = response.json()
                    answer   = data["answer"]
                    sources  = data["sources"]

                    st.markdown(answer)
                    with st.expander("📎 Sources"):
                        for s in sources:
                            st.markdown(f"**📄 {s['source']}** — {s['citation']}")
                            st.caption(f"*\"{s['excerpt']}\"*")

                    st.session_state.messages.append({
                        "role":    "assistant",
                        "content": answer,
                        "sources": sources
                    })
                else:
                    st.error("❌ Failed to get answer. Is the API running?")

    # ── Suggested questions ───────────────────────────────────
# ── Suggested questions ───────────────────────────────────
    st.divider()
    st.markdown("**💡 Try asking:**")
    suggestions = [
        "What is the confidentiality period?",
        "Which country's law governs this agreement?",
        "How many days notice is required to terminate?",
        "Who owns the intellectual property?",
        "What are the exceptions to confidentiality?"
    ]
    cols = st.columns(2)
    for i, s in enumerate(suggestions):
        if cols[i % 2].button(s, use_container_width=True):
            # Show user message
            st.session_state.messages.append({"role": "user", "content": s})

            # Call API immediately
            response = requests.post(
                f"{API_URL}/ask",
                json={"question": s}
            )
            if response.status_code == 200:
                data = response.json()
                st.session_state.messages.append({
                    "role":    "assistant",
                    "content": data["answer"],
                    "sources": data["sources"]
                })
            st.rerun()