# 🧠 Organizational Memory & Reasoning Engine

> Query your company's institutional knowledge. Understand why decisions were made, who was involved, and what breaks if things change.

Built at **Sunhacks** — a full-stack agentic AI system that ingests knowledge from Slack channels and PDF documents, stores it in a graph database, and lets you reason over it using natural language.

---

## ✨ What It Does

- **Ingest** — Upload PDFs or pull Slack channel history. An AI agent extracts structured decisions, people, reasons, and alternatives automatically.
- **Store** — Decisions are stored as a knowledge graph in Neo4j and as semantic vectors in ChromaDB.
- **Smart Upload** — Automatic duplicate detection prevents re-processing. Select from existing files or upload new ones.
- **Query** — Ask anything in plain English. A router agent decides whether to run a **Query Agent** (history, decisions, people) or an **Impact Agent** (what-if, what breaks, risk analysis).
- **Reason** — Powered by `llama-3.3-70b-versatile` via Groq. Every answer includes sources, reasoning, and tool traces.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Next.js Frontend                    │
│         Query · Upload PDF · Slack Ingest                │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────────┐
│                    FastAPI Backend                        │
│                                                          │
│   POST /query          POST /ingest/upload               │
│   POST /ingest/slack   GET  /health                      │
└──────┬──────────────────────────┬───────────────────────┘
       │                          │
┌──────▼──────┐          ┌────────▼────────┐
│   Router    │          │ Ingestion Agent  │
│   Agent     │          │                 │
│  QUERY  ──► │ Neo4j    │ validate_content │
│  IMPACT ──► │ ChromaDB │ extract_and_store│
└─────────────┘          └─────────────────┘
       │
┌──────▼──────────────────────────┐
│         Neo4j AuraDB            │  ← structured decisions graph
│         ChromaDB                │  ← semantic vector search
└─────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, Tailwind CSS, Framer Motion, Lucide React |
| Backend | FastAPI, LangGraph, LangChain |
| LLM | Groq — `llama-3.3-70b-versatile` |
| Graph DB | Neo4j AuraDB |
| Vector DB | ChromaDB |
| Slack | Slack SDK (`slack_sdk`) |
| PDF Parsing | PyMuPDF (`fitz`) |

---

## 📁 Project Structure

```
sunhacks/
├── backend/
│   ├── agents/
│   │   ├── router.py           → classifies QUERY vs IMPACT
│   │   ├── query_agent.py      → answers history/decision questions
│   │   ├── impact_agent.py     → answers what-if/risk questions
│   │   └── ingestion_agent.py  → extracts and stores decisions
│   ├── ingestion/
│   │   ├── pipeline.py         → PDF → Groq → Neo4j
│   │   └── slack.py            → Slack SDK → messages → text
│   ├── tools/
│   │   ├── neo.py              → search_decisions tool
│   │   ├── chroma.py           → search_raw_memory tool
│   │   └── impact_tools.py     → find_related_decisions tool
│   ├── db/
│   │   ├── neo.py              → Neo4j driver + store/search
│   │   └── chroma.py           → ChromaDB store/search
│   ├── core/config.py          → env vars via pydantic-settings
│   ├── main.py                 → FastAPI routes
│   └── requirements.txt
│
└── frontend/
    ├── app/
    │   ├── page.tsx            → Hero + feature cards
    │   ├── query/page.tsx      → Query · Upload PDF · Slack tabs
    │   └── activity/page.tsx   → Animated event timeline
    ├── components/
    │   ├── Navbar.tsx          → Nav + live API health indicator
    │   ├── AgentBadge.tsx      → QUERY / IMPACT badge
    │   └── SourceCard.tsx      → Source trace card
    └── lib/api.ts              → All backend API calls
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Neo4j AuraDB instance
- Groq API key
- ChromaDB (local or cloud)
- Slack Bot Token *(for Slack ingestion)*

---

### 1. Clone

```bash
git clone https://github.com/your-username/sunhacks.git
cd sunhacks
```

### 2. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Fill in `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key

NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=your_username
NEO4J_PASSWORD=your_password

SLACK_BOT_TOKEN=xoxb-your-slack-bot-token

CHROMA_TENANT=your_chroma_tenant_id
CHROMA_API_KEY=your_chroma_api_key
CHROMA_DATABASE=notes
```

```bash
uvicorn main:app --reload
# API running at http://localhost:8000
# Docs at     http://localhost:8000/docs
```

### 3. Frontend

```bash
cd frontend
npm install
# .env.local is already configured — no changes needed for local dev
npm run dev
# App running at http://localhost:3000
```

---

## 🔌 API Reference

| Method | Endpoint | Body | Description |
|---|---|---|---|
| `GET` | `/health` | — | Health check |
| `POST` | `/query` | `{ question, source_filter? }` | Query the knowledge base |
| `POST` | `/ingest/upload` | `multipart/form-data` file | Ingest a file (with duplicate detection) |
| `POST` | `/ingest/slack` | `{ channel_id, limit }` | Ingest a Slack channel |
| `GET` | `/files/list` | — | List all uploaded files |
| `GET` | `/files/check/{source}` | — | Check if file exists by source |

### Query Response Shape

```json
{
  "question": "Why did we switch to Postgres?",
  "agent_used": "QUERY",
  "answer": "The team switched to Postgres in Q3 2023 because...",
  "reasoning": "Tools used: search_decisions, search_raw_memory",
  "source_trace": [
    {
      "tool": "search_decisions",
      "args": { "query": "Postgres migration" },
      "result_preview": "Decision: Migrate from MySQL..."
    }
  ],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 🤖 Agent Routing

Every query is automatically classified before being answered:

```
User question
     │
     ▼
  Router Agent (llama-3.3-70b)
     │
     ├── QUERY  → "Why did we...?" / "Who decided...?" / "What was decided?"
     │            Uses: search_decisions (Neo4j) + search_raw_memory (ChromaDB)
     │
     └── IMPACT → "What breaks if...?" / "What would happen if...?" / "Risk of..."
                  Uses: find_related_decisions + find_decisions_by_person + search_raw_memory
```

---

## 📸 Pages

| Page | Route | Description |
|---|---|---|
| Home | `/` | Hero section, feature cards, file selection dialog |
| Knowledge Engine | `/query` | Query · Upload PDF · Slack ingest tabs |
| Activity | `/activity` | Animated timeline of recent events |

---

## 🔑 Environment Variables

### Backend — `backend/.env`

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ | Groq API key for LLM |
| `NEO4J_URI` | ✅ | Neo4j AuraDB connection URI |
| `NEO4J_USERNAME` | ✅ | Neo4j username |
| `NEO4J_PASSWORD` | ✅ | Neo4j password |
| `SLACK_BOT_TOKEN` | Slack only | Bot token for Slack ingestion |
| `CHROMA_TENANT` | ✅ | ChromaDB tenant ID |
| `CHROMA_API_KEY` | ✅ | ChromaDB API key |
| `CHROMA_DATABASE` | ✅ | ChromaDB database name |

### Frontend — `frontend/.env.local`

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

---

## 📄 License

MIT
