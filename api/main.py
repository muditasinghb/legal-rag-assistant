# api/main.py

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
import google.generativeai as genai
from groq import Groq
import shutil

# ── Load environment variables ──────────────────────────────
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# ── Setup FastAPI ────────────────────────────────────────────
app = FastAPI(title="Legal RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ── Setup ChromaDB ───────────────────────────────────────────
chroma_client = chromadb.PersistentClient(path="chroma_db")
collection     = chroma_client.get_or_create_collection(name="legal_docs")

# ── Request model ────────────────────────────────────────────
class QuestionRequest(BaseModel):
    question: str

# ── Helper: embed text ───────────────────────────────────────
def embed_text(text: str, task: str = "retrieval_query") -> list:
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        task_type=task
    )
    return result["embedding"]

# ── Helper: search ChromaDB ──────────────────────────────────
def search_chunks(query: str, top_k: int = 3) -> list:
    query_embedding = embed_text(query)
    results = collection.query(
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
async def ingest_pdf(file: UploadFile = File(...)):
    from pypdf import PdfReader

    # Save uploaded file
    save_path = Path("data") / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Extract text
    reader   = PdfReader(str(save_path))
    text     = ""
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + "\n"

    
    # Chunk with page tracking
    words    = text.split()
    chunks   = []
    start    = 0
    chunk_index = 0
    while start < len(words):
        chunk = " ".join(words[start:start+500])
        chunks.append(chunk)
        start += 450
        chunk_index += 1

    # Embed and store
    ids        = [f"{file.filename}_chunk_{i}" for i in range(len(chunks))]
    metadatas  = [{"source": file.filename, "chunk_index": i, "page": f"Section {i+1}"} for i in range(len(chunks))]
    embeddings = [embed_text(c, task="retrieval_document") for c in chunks]

    collection.add(
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

    return {
        "message":  f"Successfully ingested '{file.filename}'",
        "chunks":   len(chunks)
    }

# ── Ask a question ────────────────────────────────────────────
@app.post("/ask")
def ask(request: QuestionRequest):
    chunks  = search_chunks(request.question)
    prompt  = build_prompt(request.question, chunks)
    answer  = ask_llm(prompt)

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

# ── List all ingested documents ───────────────────────────────
@app.get("/documents")
def list_documents():
    results = collection.get()
    sources = list(set([m["source"] for m in results["metadatas"]]))
    return {"documents": sources, "total": len(sources)}