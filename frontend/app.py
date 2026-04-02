# frontend/app.py

import uuid
import streamlit as st
import requests

# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Legal RAG Assistant",
    page_icon="⚖️",
    layout="wide"
)

# ── API URL ───────────────────────────────────────────────────
API_URL = "http://127.0.0.1:8000"

# ── Session identity ──────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

session_id = st.session_state.session_id

# ── Header ───────────────────────────────────────────────────
st.title("⚖️ Legal Document Assistant")
st.markdown("Upload one or more legal documents and ask questions across all of them.")
st.divider()

# ── Two columns layout ───────────────────────────────────────
col1, col2 = st.columns([1, 2])

# ════════════════════════════════════════════════
# LEFT COLUMN — Upload + Documents
# ════════════════════════════════════════════════
with col1:
    st.subheader("📄 Upload Documents")

    uploaded_files = st.file_uploader(
        "Upload PDF contracts or legal documents",
        type=["pdf"],
        accept_multiple_files=True
    )

    if uploaded_files:
        if st.button("📥 Ingest All Documents", use_container_width=True):
            for uploaded_file in uploaded_files:
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    response = requests.post(
                        f"{API_URL}/ingest",
                        params={"session_id": session_id},
                        files={"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        st.success(f"✅ {data['message']} — {data['chunks']} chunks")
                    else:
                        st.error(f"❌ Failed to ingest {uploaded_file.name}")

    st.divider()

    # ── List ingested documents ───────────────────────────────
    st.subheader("📚 Ingested Documents")
    if st.button("🔄 Refresh List", use_container_width=True):
        response = requests.get(f"{API_URL}/documents", params={"session_id": session_id})
        if response.status_code == 200:
            docs = response.json()["documents"]
            if docs:
                for doc in docs:
                    st.markdown(f"- 📄 `{doc}`")
            else:
                st.info("No documents ingested yet")

    st.divider()

    # ── Clear session ─────────────────────────────────────────
    if st.button("🗑️ Clear Session & Documents", use_container_width=True):
        requests.delete(f"{API_URL}/session/{session_id}")
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

# ════════════════════════════════════════════════
# RIGHT COLUMN — Chat Interface
# ════════════════════════════════════════════════
with col2:
    st.subheader("💬 Ask Questions")

    # ── Initialize chat history ───────────────────────────────
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # ── Clear chat button ─────────────────────────────────────
    if st.session_state.messages:
        if st.button("🗑️ Clear Chat", use_container_width=False):
            st.session_state.messages = []
            st.rerun()

    # ── Display chat history ──────────────────────────────────
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "sources" in msg:
                with st.expander("📎 View Sources"):
                    for s in msg["sources"]:
                        st.markdown(f"**📄 {s['source']}** — Page {s['page']}")
                        st.markdown(
                            f"> {s['excerpt']}",
                            help="Exact text retrieved from the document"
                        )
                        st.divider()

    # ── Chat input ────────────────────────────────────────────
    question = st.chat_input("Ask anything about your document...")

    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Searching documents..."):
                response = requests.post(
                    f"{API_URL}/ask",
                    json={"question": question, "session_id": session_id}
                )
                if response.status_code == 200:
                    data    = response.json()
                    answer  = data["answer"]
                    sources = data["sources"]

                    st.markdown(answer)
                    with st.expander("📎 View Sources"):
                        for s in sources:
                            st.markdown(f"**📄 {s['source']}** — Page {s['page']}")
                            st.markdown(f"> {s['excerpt']}")
                            st.divider()

                    st.session_state.messages.append({
                        "role":    "assistant",
                        "content": answer,
                        "sources": sources
                    })
                else:
                    st.error("❌ Failed to get answer. Is the API running?")

    # ── Suggested questions ───────────────────────────────────
    st.divider()
    st.markdown("**💡 Try asking:**")
    suggestions = [
        "What are the key obligations of each party?",
        "Which country's law governs this agreement?",
        "How can this agreement be terminated?",
        "What are the payment terms?",
        "What are the penalties for breach of contract?",
        "What is the duration of this agreement?"
    ]
    cols = st.columns(2)
    for i, s in enumerate(suggestions):
        if cols[i % 2].button(s, use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": s})
            response = requests.post(
                f"{API_URL}/ask",
                json={"question": s, "session_id": session_id}
            )
            if response.status_code == 200:
                data = response.json()
                st.session_state.messages.append({
                    "role":    "assistant",
                    "content": data["answer"],
                    "sources": data["sources"]
                })
            st.rerun()
