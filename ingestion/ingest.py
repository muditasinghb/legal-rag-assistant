# ingestion/ingest.py

import os
from pathlib import Path
from dotenv import load_dotenv
from pypdf import PdfReader
import chromadb
import google.generativeai as genai

# ── Load environment variables ──────────────────────────────
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# ── Setup ChromaDB ───────────────────────────────────────────
chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_or_create_collection(name="legal_docs")

# ── Embed text ───────────────────────────────────────────────
def embed_text(text: str) -> list:
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        task_type="retrieval_document"
    )
    return result["embedding"]

# ── Extract text page by page ────────────────────────────────
def extract_pages(pdf_path: str) -> list:
    print(f"📄 Reading PDF: {pdf_path}")
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            pages.append({"text": text, "page": i + 1})
    print(f"📖 Extracted {len(pages)} pages")
    return pages

# ── Chunk each page separately ───────────────────────────────
def chunk_pages(pages: list, chunk_size: int = 500, overlap: int = 50) -> list:
    chunks = []
    for page_data in pages:
        words    = page_data["text"].split()
        page_num = page_data["page"]
        start    = 0
        chunk_num = 0
        while start < len(words):
            chunk_text = " ".join(words[start:start + chunk_size])
            chunks.append({
                "text":      chunk_text,
                "page":      page_num,
                "chunk_num": chunk_num
            })
            start += chunk_size - overlap
            chunk_num += 1
    print(f"✂️  Created {len(chunks)} chunks")
    return chunks

# ── Store chunks with page metadata ─────────────────────────
def store_chunks(chunks: list, filename: str):
    print(f"💾 Embedding and storing chunks...")

    # Clear old chunks for this file
    try:
        existing = collection.get(where={"source": filename})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
            print(f"🗑️  Cleared old chunks for '{filename}'")
    except:
        pass

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
    print(f"✅ Stored {len(chunks)} chunks from '{filename}' into ChromaDB!")

# ── Main pipeline ────────────────────────────────────────────
def ingest_pdf(pdf_path: str):
    filename = Path(pdf_path).name
    pages    = extract_pages(pdf_path)
    chunks   = chunk_pages(pages)
    store_chunks(chunks, filename)

if __name__ == "__main__":
    ingest_pdf(r"E:\practice\legal-rag\data\sample_nda.pdf")