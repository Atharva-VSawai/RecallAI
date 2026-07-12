# Backend — Org Memory & Reasoning

Agentic AI backend that ingests company documents and builds an organizational memory — enabling reasoning over past decisions, who made them, and why.

## Tech Stack

| Layer | Tech |
|-------|------|
| API | FastAPI |
| LLM | Groq (`llama-3.3-70b-versatile`) |
| Agent | LangGraph (ReAct) |
| LLM Tooling | LangChain |
| Graph DB | Neo4j AuraDB |
| Doc Parsing | PyMuPDF |

## How It Works

```
PDF Upload
  → PyMuPDF        extract raw text
  → Groq LLM       raw text → structured JSON
                   (decision, reason, impact, alternatives, people, topic, timestamp)
  → Neo4j          Person + Decision nodes + [:MADE] relationships

Query
  → LangGraph agent (ReAct loop)
  → Tools: search Neo4j by entity, topic, decision chain
  → Groq synthesizes final answer with reasoning
```

## Structure

```
backend/
├── core/
│   └── config.py             → env vars (pydantic-settings)
├── ingestion/
│   └── pipeline.py           → pymupdf extract → groq → neo4j store
├── tools/
│   ├── neo.py                → LangChain tools for agent (search neo4j)
│   └── chroma.py             → LangChain tools for agent (search chroma)
├── db/
│   ├── neo.py                → neo4j driver + store/search functions
│   └── chroma.py             → chroma store/search (coming soon)
├── agent.py                  → LangGraph ReAct agent
├── main.py                   → FastAPI routes
├── .env.example
└── requirements.txt
```

## Setup

### 1. Create virtual environment

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

`.env` values:

```
GROQ_API_KEY=your_groq_api_key
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=your_username
NEO4J_PASSWORD=your_password
```

### 4. Run

```bash
uvicorn main:app --reload
```

API → `http://localhost:8000`  
Docs → `http://localhost:8000/docs`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/ingest/upload` | Upload PDF → extract → store in Neo4j |
| POST | `/query` | Ask a question, agent reasons over Neo4j |

## Example

**Ingest:**
```bash
curl -X POST http://localhost:8000/ingest/upload \
  -F "file=@company_notes.pdf"
```

**Query:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Why did we switch to Python?"}'
```
