---
title: Legal RAG Assistant
emoji: ⚖️
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# ⚖️ Legal RAG Assistant

> An end-to-end Retrieval Augmented Generation (RAG) pipeline that lets you upload any legal document and ask questions about it in plain English — with cited, accurate answers.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?style=flat-square&logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-1.40-red?style=flat-square&logo=streamlit)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-orange?style=flat-square)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-purple?style=flat-square)
![BGE](https://img.shields.io/badge/BGE-base--en--v1.5-blue?style=flat-square)

---

## 📌 What Problem Does This Solve?

Reading a legal contract is time-consuming, confusing, and expensive if you need a lawyer for every question.

This project turns any legal PDF into an intelligent assistant that:
- Answers specific questions about clauses instantly
- Cites the **exact page and section** it pulled the answer from
- Supports **multiple documents** — ask questions across all uploaded contracts at once
- Never hallucinates — it only answers from your document, not from general training data

---

## 🎬 Demo

| Upload Contracts | Ask a Question | Get a Cited Answer |
|---|---|---|
| Drag & drop one or more PDFs | Type in plain English | Answer + exact source excerpt with page number |

**Example:**
```
User   → "What is the termination notice period?"
System → "Either party may terminate this agreement with 30 days
          written notice. [sample_contract.pdf — Page 4]"
          
          > "...either party may terminate this Agreement upon
             thirty (30) days prior written notice to the other party..."
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        INGESTION PIPELINE                        │
│                                                                  │
│  PDF Upload → Extract Text (PyPDF) → Split into Chunks          │
│       → BGE Embeddings (local, no API) → Store in ChromaDB      │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                        RETRIEVAL PIPELINE                        │
│                                                                  │
│  User Question → BGE Embed Question → Cosine Similarity Search  │
│       → Top 3 Most Relevant Chunks Retrieved from ChromaDB      │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                       GENERATION PIPELINE                        │
│                                                                  │
│  Retrieved Chunks + Question → Prompt Engineering               │
│       → LLaMA 3.3 70B (via Groq) → Cited Answer                 │
└─────────────────────────────────────────────────────────────────┘
```

### Why RAG instead of just asking an LLM?

```
Plain LLM                        RAG (This Project)
─────────────────────            ──────────────────────────────
Question → LLM memory            Question → Search YOUR document
         → Answer from                     → Retrieve exact chunks
           general training                → LLM reads only those chunks
           (may hallucinate,               → Answer grounded in your
            no citations)                   document (cited, accurate)
```

---

## 🛠️ Tech Stack

| Layer | Technology | Why This Choice |
|---|---|---|
| **Embeddings** | `BAAI/bge-base-en-v1.5` | Top-ranked on MTEB benchmark, runs locally — no API calls, no rate limits |
| **Vector Database** | ChromaDB | Lightweight, persistent, runs in-process |
| **LLM** | LLaMA 3.3 70B via Groq | Free API, fast inference, strong reasoning |
| **Backend** | FastAPI + Uvicorn | Async REST API, auto-generated docs at `/docs` |
| **Frontend** | Streamlit | Rapid UI with built-in chat components |
| **PDF Parsing** | PyPDF | Extract text page-by-page with page number tracking |
| **Reverse Proxy** | nginx | Routes traffic between frontend and backend |
| **Containerization** | Docker | Consistent deployment environment |
| **CI/CD** | GitHub Actions → HuggingFace Spaces | Auto-deploy on every push to main |

---

## ✨ Features

- **Multi-document support** — upload multiple PDFs, ask questions across all of them
- **Chat history** — full conversation history within a session
- **Source highlighting** — see the exact paragraph from the document that supports each answer
- **Page-level citations** — every answer cites the page number it came from
- **No hallucination** — LLM is instructed to only answer from retrieved context
- **Batch embeddings** — all chunks embedded in one pass for fast ingestion

---

## 📁 Project Structure

```
legal-rag-assistant/
│
├── api/
│   └── main.py            # FastAPI backend — /ingest, /ask, /documents
│
├── frontend/
│   └── app.py             # Streamlit chat UI
│
├── ingestion/
│   └── ingest.py          # Standalone ingestion script
│
├── retrieval/
│   └── retrieve.py        # Standalone retrieval script
│
├── .streamlit/
│   └── config.toml        # Streamlit config (XSRF disabled for nginx proxy)
│
├── nginx.conf             # Reverse proxy config
├── Dockerfile             # Container definition
├── docker-compose.yml     # Local development setup
├── requirements.txt
└── .env                   # API keys (never committed)
```

---

## ⚙️ Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/muditasinghb/legal-rag-assistant.git
cd legal-rag-assistant
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Get API Key (Free)

| Key | Where to Get |
|---|---|
| `GROQ_API_KEY` | https://console.groq.com → API Keys |

> No Google API key needed — embeddings run locally using BGE.

### 4. Create `.env` File
```
GROQ_API_KEY=your_groq_key_here
```

### 5. Run with Docker (Recommended)
```bash
docker-compose up --build
```

### 6. Or Run Manually

```bash
# Terminal 1 — Backend
uvicorn api.main:app --reload --port 8000

# Terminal 2 — Frontend
streamlit run frontend/app.py --server.port 8501
```

### 7. Open in Browser
```
http://localhost:8501
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/ingest` | Upload & process a PDF |
| `POST` | `/ask` | Ask a question, get cited answer |
| `GET` | `/documents` | List all ingested documents |

Interactive API docs:
```
http://127.0.0.1:8000/docs
```

---

## 💬 Example Questions

Once you upload a contract, try:

- *"What are the key obligations of each party?"*
- *"Which country's law governs this agreement?"*
- *"How can this agreement be terminated?"*
- *"What are the payment terms?"*
- *"What are the penalties for breach of contract?"*
- *"What is the duration of this agreement?"*

---

## 🚀 Future Improvements

- [ ] Clause risk flagging (highlight potentially unfair terms)
- [ ] Support for DOCX and TXT files
- [ ] Fine-tuned embeddings on legal corpus (CUAD dataset)
- [ ] User authentication and persistent sessions

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 👤 Author

**Mudita Singh Bhardwaj**
- GitHub: [@muditasinghb](https://github.com/muditasinghb)
- HuggingFace Space: [muditaaaa/legal-rag-assistant](https://huggingface.co/spaces/muditaaaa/legal-rag-assistant)

---

> *Built as a portfolio project to demonstrate end-to-end RAG pipeline development for legal document intelligence.*
