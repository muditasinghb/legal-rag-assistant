
import os
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from pypdf import PdfReader
import chromadb
import google.generativeai as genai
from groq import Groq

# ── Load environment variables ──────────────────────────────
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")

if not GOOGLE_API_KEY:
    st.error("❌ GOOGLE_API_KEY not set. Add it in Space secrets.")
    st.stop()

if not GROQ_API_KEY:
    st.error("❌ GROQ_API_KEY not set. Add it in Space secrets.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# ── Setup ChromaDB ───────────────────────────────────────────
chroma_client = chromadb.PersistentClient(path="chroma_db")
collection     = chroma_client.get_or_create_collection(name="legal_docs")

# ── Core Functions ───────────────────────────────────────────
def embed_text(text: str, task: str = "retrieval_document") -> list:
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        task_type=task
    )
    return result["embedding"]

def extract_pages(pdf_file) -> list:
    reader = PdfReader(pdf_file)
    pages  = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            pages.append({"text": text, "page": i + 1})
    return pages

def chunk_pages(pages: list, chunk_size=500, overlap=50) -> list:
    chunks = []
    for page_data in pages:
        words     = page_data["text"].split()
        page_num  = page_data["page"]
        start     = 0
        chunk_num = 0
        while start < len(words):
            chunk_text = " ".join(words[start:start + chunk_size])
            chunks.append({
                "text":      chunk_text,
                "page":      page_num,
                "chunk_num": chunk_num
            })
            start     += chunk_size - overlap
            chunk_num += 1
    return chunks

def ingest_document(pdf_file, filename: str) -> int:
    try:
        existing = collection.get(where={"source": filename})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except:
        pass

    pages      = extract_pages(pdf_file)
    chunks     = chunk_pages(pages)
    ids        = [f"{filename}_p{c['page']}_c{c['chunk_num']}" for c in chunks]
    metadatas  = [{
        "source":    filename,
        "page":      c["page"],
        "chunk_num": c["chunk_num"],
        "citation":  f"Page {c['page']}"
    } for c in chunks]
    embeddings = [embed_text(c["text"]) for c in chunks]
    texts      = [c["text"] for c in chunks]

    collection.add(
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )
    return len(chunks)

def search_chunks(query: str, top_k: int = 3) -> list:
    query_embedding = embed_text(query, task="retrieval_query")
    results         = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    chunks = []
    for i in range(len(results["documents"][0])):
        chunks.append({
            "text":     results["documents"][0][i],
            "source":   results["metadatas"][0][i]["source"],
            "page":     results["metadatas"][0][i].get("page", "?"),
            "citation": results["metadatas"][0][i].get("citation", "")
        })
    return chunks

def ask_llm(question: str, chunks: list) -> str:
    context = ""
    for chunk in chunks:
        context += f"\n--- From {chunk['source']}, Page {chunk['page']} ---\n"
        context += chunk["text"] + "\n"

    prompt = f"""You are a legal assistant helping users understand contracts.
Answer based ONLY on the context below.
If the answer is not found, say "I could not find this in the document."
Always cite the page number that supports your answer.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""

    groq_client = Groq(api_key=GROQ_API_KEY)
    response    = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ════════════════════════════════════════════════════════════
# STREAMLIT UI
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Legal RAG Assistant",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ Legal Document Assistant")
st.markdown("Upload a legal document and ask questions about it in plain English.")
st.divider()

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📄 Upload Document")
    uploaded_file = st.file_uploader(
        "Upload a PDF contract or legal document",
        type=["pdf"]
    )

    if uploaded_file:
        if st.button("📥 Ingest Document", use_container_width=True):
            with st.spinner("Reading and embedding document..."):
                chunks = ingest_document(uploaded_file, uploaded_file.name)
                st.success(f"✅ Ingested '{uploaded_file.name}'")
                st.info(f"📦 Created {chunks} searchable chunks")

    st.divider()
    st.subheader("📚 Ingested Documents")
    if st.button("🔄 Refresh List", use_container_width=True):
        results = collection.get()
        if results["metadatas"]:
            sources = list(set([m["source"] for m in results["metadatas"]]))
            for doc in sources:
                st.markdown(f"- 📄 `{doc}`")
        else:
            st.info("No documents ingested yet")

with col2:
    st.subheader("💬 Ask Questions")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "sources" in msg:
                with st.expander("📎 Sources"):
                    for s in msg["sources"]:
                        st.markdown(f"**📄 {s['source']}** — {s['citation']}")
                        st.caption(f"*\"{s['excerpt']}\"*")

    question = st.chat_input("Ask anything about your document...")

    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Searching document..."):
                chunks  = search_chunks(question)
                answer  = ask_llm(question, chunks)
                sources = [{
                    "source":   c["source"],
                    "citation": c["citation"],
                    "excerpt":  c["text"][:150] + "..."
                } for c in chunks]

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
            st.session_state.messages.append({"role": "user", "content": s})
            chunks  = search_chunks(s)
            answer  = ask_llm(s, chunks)
            sources = [{
                "source":   c["source"],
                "citation": c["citation"],
                "excerpt":  c["text"][:150] + "..."
            } for c in chunks]
            st.session_state.messages.append({
                "role":    "assistant",
                "content": answer,
                "sources": sources
            })
            st.rerun()
