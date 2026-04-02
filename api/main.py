# api/main.py

import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from sentence_transformers import SentenceTransformer
from groq import Groq
import shutil

# ── Load environment variables ──────────────────────────────
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ── Load BGE embedding model once at startup ─────────────────
embedding_model = SentenceTransformer("BAAI/bge-base-en-v1.5")

# ── Setup FastAPI ────────────────────────────────────────────
app = FastAPI(title="Legal RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ── Setup ChromaDB — ephemeral, isolated per session ─────────
chroma_client = chromadb.EphemeralClient()
session_collections: dict = {}

def get_collection(session_id: str):
    if session_id not in session_collections:
        session_collections[session_id] = chroma_client.get_or_create_collection(
            name=f"legal_docs_{session_id}"
        )
    return session_collections[session_id]

# ── Request models ───────────────────────────────────────────
class QuestionRequest(BaseModel):
    question: str
    session_id: str

# ── Helper: embed text ───────────────────────────────────────
def embed_text(text: str) -> list:
    return embedding_model.encode(text, normalize_embeddings=True).tolist()

def embed_texts_batch(texts: list) -> list:
    return embedding_model.encode(texts, normalize_embeddings=True, batch_size=32).tolist()

# ── Helper: search ChromaDB ──────────────────────────────────
def search_chunks(query: str, session_id: str, top_k: int = 3) -> list:
    collection = get_collection(session_id)
    if collection.count() == 0:
        return []
    query_embedding = embed_text(f"Represent this sentence for searching relevant passages: {query}")
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count())
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

# ── Helper: ask LLM ──────────────────────────────────────────
def ask_llm(prompt: str) -> str:
    groq_client = Groq(api_key=GROQ_API_KEY)
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ── Helper: build prompt ─────────────────────────────────────
def build_prompt(question: str, chunks: list) -> str:
    context = ""
    for i, chunk in enumerate(chunks):
        context += f"\n--- From {chunk['source']}, Page {chunk['page']} ---\n"
        context += chunk["text"] + "\n"

    return f"""You are a legal assistant helping users understand contracts.
Answer based ONLY on the context below.
If answer not found, say "I could not find this in the document."
Always cite which part of the document supports your answer.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""

# ════════════════════════════════════════════════════════════
# ROUTES
# ════════════════════════════════════════════════════════════

# ── Health check ─────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "Legal RAG API is running!"}

# ── Upload + ingest a PDF ─────────────────────────────────────
@app.post("/ingest")
async def ingest_pdf(session_id: str, file: UploadFile = File(...)):
    from pypdf import PdfReader

    collection = get_collection(session_id)

    # Save uploaded file temporarily
    save_path = Path("data") / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Extract text
    reader = PdfReader(str(save_path))
    text   = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + "\n"

    # Chunk with page tracking
    words       = text.split()
    chunks      = []
    start       = 0
    chunk_index = 0
    while start < len(words):
        chunk = " ".join(words[start:start + 500])
        chunks.append(chunk)
        start += 450
        chunk_index += 1

    # Embed and store
    ids        = [f"{session_id}_{file.filename}_chunk_{i}" for i in range(len(chunks))]
    metadatas  = [{"source": file.filename, "chunk_index": i, "page": f"Section {i+1}"} for i in range(len(chunks))]
    embeddings = embed_texts_batch(chunks)

    collection.add(
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

    return {
        "message": f"Successfully ingested '{file.filename}'",
        "chunks":  len(chunks)
    }

# ── Ask a question ────────────────────────────────────────────
@app.post("/ask")
def ask(request: QuestionRequest):
    chunks = search_chunks(request.question, request.session_id)
    if not chunks:
        return {
            "question": request.question,
            "answer":   "No documents have been uploaded for this session yet.",
            "sources":  []
        }
    prompt = build_prompt(request.question, chunks)
    answer = ask_llm(prompt)

    return {
        "question": request.question,
        "answer":   answer,
        "sources": [{
            "source":   c["source"],
            "page":     c["page"],
            "citation": f"Page {c['page']}",
            "excerpt":  c["text"][:150] + "..."
        } for c in chunks]
    }

# ── List documents for a session ─────────────────────────────
@app.get("/documents")
def list_documents(session_id: str):
    collection = get_collection(session_id)
    results    = collection.get()
    if not results["metadatas"]:
        return {"documents": [], "total": 0}
    sources = list(set([m["source"] for m in results["metadatas"]]))
    return {"documents": sources, "total": len(sources)}

# ── Clear a session ───────────────────────────────────────────
@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    if session_id in session_collections:
        chroma_client.delete_collection(name=f"legal_docs_{session_id}")
        del session_collections[session_id]
    return {"message": f"Session {session_id} cleared"}
