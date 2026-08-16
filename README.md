# Recall.AI

Recall.AI is an organizational memory and reasoning platform. It ingests company documents, conversations, and integrations to build a multi-tenant knowledge graph, enabling AI to reason over past decisions, context, and project history.

## Architecture

The system consists of a FastAPI backend and a Next.js frontend, heavily leveraging graph and vector databases to store and retrieve organizational context.

### Technologies
- **Frontend**: Next.js (App Router), Tailwind CSS, React
- **Backend**: FastAPI, Python, LangGraph (ReAct agent pattern)
- **Database (Graph)**: Neo4j AuraDB (Entities, Decisions, Provenance)
- **Database (Vector)**: ChromaDB (Embeddings, semantic similarity)
- **Database (Relational)**: Supabase (Auth, Users, Tenancy, Jobs, Activities)
- **LLM**: Groq (`llama-3.3-70b-versatile`)
- **Document Parsing**: PyMuPDF

## Backend Setup

1. **Virtual Environment**
   ```bash
   cd backend
   python -m venv venv
   # Windows: venv\Scripts\activate
   # macOS/Linux: source venv/bin/activate
   ```

2. **Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables**
   ```bash
   cp .env.example .env
   ```
   Required keys: `GROQ_API_KEY`, `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_AUDIENCE`, `SUPABASE_JWT_ISSUER`.

4. **Initialize Database**
   Apply Supabase migrations to your database instance, then create the required Neo4j indexes:
   ```bash
   python scripts/create_indexes.py
   ```

5. **Run Development Server**
   ```bash
   uvicorn main:app --reload
   ```
   API endpoints are available at `http://localhost:8000` (docs at `/docs`).

## Frontend Setup

1. **Install Dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Environment Variables**
   Copy `.env.example` to `.env.local` and populate the frontend Supabase variables:
   `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`.

3. **Run Development Server**
   ```bash
   npm run dev
   ```
   The UI will be accessible at `http://localhost:3000`.

## Features
- **Project Workspaces**: Multi-tenant isolation for distinct projects and teams.
- **Durable Ingestion**: Reliable background processing of PDFs, text files, and integrations (Slack, MS Teams) with retry and lease mechanisms.
- **Knowledge Graph Retrieval**: ReAct agent traverses nodes to answer "who", "what", and "why" queries rather than just regurgitating semantic search results.
- **Provenance Tracking**: Every generated answer can be traced back to the specific ingested document or activity.
