# Recall.AI

Recall.AI is an organizational memory and reasoning platform that converts company documents, Slack conversations, spreadsheets, images, audio, and video into searchable institutional knowledge.

The system combines structured decision storage in Neo4j, semantic raw-content retrieval in ChromaDB, LLM-assisted extraction, specialized reasoning agents, Supabase authentication, and a Next.js user interface.

This repository is currently a working prototype and academic major-project foundation. The university hardening roadmap is documented in DEVELOPMENT_ROADMAP.md.

## Project overview

Organizations often lose the reasoning behind decisions because knowledge is distributed across chats, documents, spreadsheets, and meetings. Recall.AI addresses this by:

1. Ingesting heterogeneous organizational sources.
2. Extracting decisions, reasons, people, alternatives, topics, timestamps, and impacts.
3. Storing structured knowledge as a graph.
4. Storing raw text as embedding-searchable memory.
5. Routing natural-language questions to specialized agents.
6. Returning answers with source traces.

## Features

### Current features

- PDF ingestion
- Excel ingestion
- Image OCR ingestion
- Audio/video transcription
- Slack channel ingestion
- SHA-256 duplicate file detection
- Query Agent
- Impact Agent
- Source-specific query filtering
- Neo4j graph visualization
- ChromaDB semantic search
- Activity timeline
- Supabase login, signup, and password recovery
- Dark/light theme
- Responsive interface

### Academic-hardening features to implement

- Relational database schema with parent/child tables and foreign keys
- Database constraints and indexes
- Stored procedures and database functions where required
- Backend JWT verification
- Role/ownership authorization
- Three- or four-layer backend architecture
- Structured logging
- Global exception handling
- Custom exception hierarchy
- Unit, integration, API, and acceptance tests
- Complete academic diagrams and research documentation

## Architecture

Current flow:

Frontend → FastAPI REST API → Agents and ingestion pipelines → Neo4j and ChromaDB

Target academic flow:

Presentation Layer → API/Application Layer → Business/Domain Layer → Data Access Layer → Databases and external providers

See ARCHITECTURE.md.

## Technology stack

| Area | Technology |
|---|---|
| Frontend | Next.js, React, TypeScript |
| Styling | Tailwind CSS, Framer Motion, GSAP |
| UI | Radix UI, Lucide React |
| Backend | Python, FastAPI, Uvicorn |
| Agent framework | LangChain, LangGraph |
| Cloud LLM | Groq |
| Local LLM option | Ollama |
| Graph storage | Neo4j AuraDB |
| Vector storage | ChromaDB Cloud |
| Embeddings | Cohere |
| Authentication | Supabase Auth |
| PDF processing | PyMuPDF |
| Spreadsheet processing | OpenPyXL |
| Messaging source | Slack SDK |

## Folder structure

~~~text
recallAi/
├── backend/
│   ├── main.py
│   ├── agent.py
│   ├── activity_store.py
│   ├── core/
│   ├── agents/
│   ├── ingestion/
│   ├── db/
│   ├── tools/
│   ├── services/
│   └── requirements.txt
├── frontend/
│   ├── app/
│   ├── components/
│   ├── contexts/
│   ├── lib/
│   └── public/
├── README.md
├── PROJECT_STRUCTURE.md
├── UNIVERSITY_EVALUATION.md
├── DEVELOPMENT_ROADMAP.md
├── ARCHITECTURE.md
├── DATABASE_DESIGN.md
├── SECURITY.md
├── TESTING.md
├── DEPLOYMENT.md
├── WEEKLY_LOGBOOK.md
└── FINAL_SUBMISSION_CHECKLIST.md
~~~

## Installation

### Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- npm
- Neo4j instance
- ChromaDB Cloud account
- Groq API key
- Cohere API key
- Slack bot token for Slack ingestion
- Supabase project

### Backend

~~~text
cd backend
python -m venv venv
~~~

Windows:

~~~text
venv\Scripts\activate
~~~

macOS/Linux:

~~~text
source venv/bin/activate
~~~

Install:

~~~text
pip install -r requirements.txt
~~~

Create backend/.env:

~~~text
GROQ_API_KEY=
NEO4J_URI=
NEO4J_USERNAME=
NEO4J_PASSWORD=
SLACK_BOT_TOKEN=
COHERE_API_KEY=
CHROMA_API_KEY=
CHROMA_TENANT=
CHROMA_DATABASE=notes
OLLAMA_MODEL=llama3.1
~~~

### Frontend

~~~text
cd frontend
npm install
~~~

Create frontend/.env.local:

~~~text
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000
~~~

## Running locally

Backend:

~~~text
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
~~~

Frontend:

~~~text
cd frontend
npm run dev
~~~

URLs:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Swagger documentation: http://localhost:8000/docs

## API summary

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /health | Health check |
| POST | /query | Query organizational memory |
| POST | /ingest/upload | Upload supported files |
| POST | /ingest/audio | Transcribe and ingest audio/video |
| POST | /ingest/image | OCR and ingest images |
| POST | /ingest/slack | Ingest Slack history |
| GET | /files/list | List files |
| GET | /files/check/{source} | Check source metadata |
| DELETE | /files/{source} | Delete source data |
| GET | /activity | Retrieve activity |
| GET | /graph/data | Retrieve graph data |

## Deployment

A typical deployment uses a Next.js host, a Python API host, Neo4j AuraDB, ChromaDB Cloud, and Supabase Auth. See DEPLOYMENT.md.

## Screenshots placeholder

Add screenshots before final submission:

- [ ] Home page
- [ ] Login page
- [ ] Query page
- [ ] Ingestion workflow
- [ ] Activity page
- [ ] Graph page
- [ ] API documentation
- [ ] Database evidence

## Future scope

- Relational academic reporting database
- Multi-tenant organizations
- Role-based access control
- Background ingestion jobs
- More connectors
- Decision conflict detection
- Decision lifecycle workflows
- Evaluation datasets
- Multilingual OCR and transcription

## Contributors

Add student names, roll numbers, supervisor, department, and institution before submission.

## License

Confirm the final license with the supervisor before submission.

