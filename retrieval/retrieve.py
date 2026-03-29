# retrieval/retrieve.py
# retrieval/retrieve.py

import os
from pathlib import Path
from dotenv import load_dotenv
import chromadb
import google.generativeai as genai

# ── Load environment variables ──────────────────────────────
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# ── Connect to existing ChromaDB ─────────────────────────────
chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_or_create_collection(name="legal_docs")

# ── Embed the user's question ────────────────────────────────
def embed_query(text: str) -> list:
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        task_type="retrieval_query"
    )
    return result["embedding"]

# ── Search ChromaDB for relevant chunks ─────────────────────
def search_chunks(query: str, top_k: int = 3) -> list:
    query_embedding = embed_query(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    chunks = []
    for i in range(len(results["documents"][0])):
        chunks.append({
            "text":     results["documents"][0][i],
            "source":   results["metadatas"][0][i]["source"],
            "chunk_id": results["metadatas"][0][i]["chunk_index"]
        })
    return chunks

# ── Build prompt with retrieved context ─────────────────────
def build_prompt(question: str, chunks: list) -> str:
    context = ""
    for i, chunk in enumerate(chunks):
        context += f"\n--- Chunk {i+1} (from {chunk['source']}) ---\n"
        context += chunk["text"] + "\n"

    prompt = f"""You are a legal assistant helping users understand contracts and legal documents.
Answer the question based ONLY on the context provided below.
If the answer is not in the context, say "I could not find this information in the document."
Always mention which part of the document supports your answer.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""
    return prompt

# ── Ask Gemini with the context ──────────────────────────────
def ask_llm(prompt: str) -> str:
    from groq import Groq
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ── Main RAG function ────────────────────────────────────────
def ask_question(question: str) -> dict:
    print(f"\n🔍 Question: {question}")

    # Step 1: Retrieve relevant chunks
    chunks = search_chunks(question)
    print(f"📚 Retrieved {len(chunks)} relevant chunks")

    # Step 2: Build prompt
    prompt = build_prompt(question, chunks)

    # Step 3: Get answer from Gemini
    answer = ask_llm(prompt)
    print(f"\n💬 Answer:\n{answer}")

    return {
        "question": question,
        "answer":   answer,
        "sources":  chunks
    }

# ── Test it out ──────────────────────────────────────────────
if __name__ == "__main__":
    result = ask_question("What is the confidentiality period in this agreement?")
    print("\n" + "="*60)