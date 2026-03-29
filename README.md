# ⚖️ Legal RAG Assistant

> An end-to-end Retrieval Augmented Generation (RAG) pipeline that lets you upload any legal document and ask questions about it in plain English — with cited, accurate answers.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=flat-square&logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red?style=flat-square&logo=streamlit)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-orange?style=flat-square)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3-purple?style=flat-square)

---

## 📌 What Problem Does This Solve?

Reading a legal contract is time-consuming, confusing, and expensive if you need a lawyer for every question.

This project turns any legal PDF into an intelligent assistant that:
- Answers specific questions about clauses instantly
- Cites the exact page and section it pulled the answer from
- Explains complex legal language in plain English
- Never hallucinates — it only answers from your document

---

## 🎬 Demo

| Upload a Contract | Ask a Question | Get a Cited Answer |
|---|---|---|
| Drag & drop any PDF | Type in plain English | Answer + exact source excerpt |

**Example:**
```
User    → "What is the confidentiality period?"
System  → "The confidentiality period is 3 years from the date
           of disclosure, and survives for 3 years from termination.
           [Page 2 — Clause 3(g)]"
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      INGESTION PIPELINE                      │
│  PDF → Extract Text → Chunk → Gemini Embed → ChromaDB Store │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      RETRIEVAL PIPELINE                      │
│  Question → Embed → Vector Search → Top-K Chunks Retrieved  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      GENERATION PIPELINE                     │
│  Chunks + Question → Prompt → LLaMA 3.3 → Cited Answer      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Embeddings** | Google Gemini `gemini-embedding-001` | Convert text to vectors |
| **Vector Database** | ChromaDB (persistent, local) | Store & search embeddings |
| **LLM** | LLaMA 3.3 70B via Groq API | Generate answers |
| **Backend** | FastAPI + Uvicorn | REST API |
| **Frontend** | Streamlit | Chat UI |
| **PDF Parsing** | PyPDF | Extract text from PDFs |

---

## 📁 Project Structure

```
legal-rag-assistant/
│
├── api/
│   └── main.py            # FastAPI backend — /ingest, /ask, /documents
│
├── ingestion/
│   └── ingest.py          # PDF parsing, chunking, embedding, storage
│
├── retrieval/
│   └── retrieve.py        # Vector search + LLM answer generation
│
├── frontend/
│   └── app.py             # Streamlit chat UI
│
├── data/                  # Drop your PDF contracts here
├── .env                   # API keys (never committed)
├── .gitignore
├── requirements.txt
└── README.md
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

### 3. Get API Keys (Both Free)

| Key | Where to Get |
|---|---|
| `GOOGLE_API_KEY` | https://aistudio.google.com → API Keys |
| `GROQ_API_KEY` | https://console.groq.com → API Keys |

### 4. Create `.env` File
```bash
GOOGLE_API_KEY=your_google_key_here
GROQ_API_KEY=your_groq_key_here
```

### 5. Add a PDF
Drop any legal PDF into the `data/` folder.

### 6. Ingest the Document
```bash
python ingestion/ingest.py
```

### 7. Start the Backend
```bash
uvicorn api.main:app --reload
```

### 8. Start the Frontend (new terminal)
```bash
streamlit run frontend/app.py
```

### 9. Open in Browser
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

Interactive API docs available at:
```
http://127.0.0.1:8000/docs
```

---

## 💬 Example Questions to Ask

Once you upload a contract, try:

- *"What is the confidentiality period?"*
- *"Which country's law governs this agreement?"*
- *"How many days notice is required to terminate?"*
- *"Who owns the intellectual property?"*
- *"What are the exceptions to confidentiality?"*
- *"Can either party assign this agreement?"*
- *"What happens if a clause is found unenforceable?"*

---

## 🧠 How RAG Works (Simply)

```
Traditional AI          RAG (This Project)
──────────────          ──────────────────
Question                Question
    ↓                       ↓
LLM Memory              Search YOUR documents
    ↓                       ↓
Answer from             Retrieve relevant chunks
general training            ↓
(may hallucinate)       LLM reads chunks → Answer
                        (grounded, cited, accurate)
```

The LLM never guesses — it only answers from the document you uploaded.

---

## 🚀 Future Improvements

- [ ] Multi-document comparison
- [ ] Clause risk flagging
- [ ] Support for DOCX and TXT files
- [ ] Fine-tuned embeddings on legal corpus (CUAD dataset)
- [ ] Authentication and user sessions
- [ ] Deployed on cloud (Railway + Streamlit Cloud)

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 👤 Author

**Mudita Singh Bhardwaj**
- GitHub: [@muditasinghb](https://github.com/muditasinghb)

---

> *Built as a portfolio project to demonstrate end-to-end RAG pipeline development for legal document intelligence.*
