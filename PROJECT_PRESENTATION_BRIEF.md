# Recall.AI — Project Presentation Brief

## 1. Project title

**Recall.AI: An AI-Powered Organizational Memory and Decision-Reasoning Platform**

## 2. One-minute introduction

Organizations create important knowledge in many places: PDF documents, spreadsheets, meetings, Slack conversations, images, and videos. The problem is that people can usually find the final decision, but not the reasoning behind it.

Recall.AI converts scattered organizational information into a searchable memory. It extracts decisions, reasons, people, alternatives, topics, and impacts, then allows a user to ask natural-language questions such as:

- Why did the team choose a particular technology?
- Who was involved in that decision?
- What alternatives were considered?
- What could be affected if the decision changes?

The important point for this presentation is that this is not only a proposed idea. **A working MVP has already been implemented and can be demonstrated.**

## 3. Problem statement

Organizational knowledge is often:

- distributed across different file formats and communication channels;
- difficult to search by meaning;
- disconnected from the people and reasons involved;
- lost when team members leave;
- reduced to isolated documents instead of connected decisions.

Traditional keyword search can find a phrase, but it does not naturally answer questions about relationships, reasoning, impact, or alternatives.

## 4. Proposed solution

Recall.AI uses AI to build two complementary forms of organizational memory:

1. **Structured knowledge graph** — decisions and their relationships are stored in Neo4j.
2. **Semantic document memory** — original text is stored in ChromaDB as searchable vector embeddings.

An LLM-based agent retrieves information from these stores and generates an answer with a source trace showing which tools and sources were used.

## 5. MVP scope currently implemented

The current MVP includes:

- Supabase login, signup, and password recovery;
- PDF upload and ingestion;
- Excel upload and text extraction;
- image OCR ingestion;
- audio/video transcription and ingestion;
- Slack channel ingestion;
- duplicate-file detection using SHA-256 hashes;
- structured decision extraction;
- Neo4j knowledge graph creation;
- ChromaDB semantic search;
- source-specific query filtering;
- Query Agent for normal questions;
- Impact Agent for “what if” and risk questions;
- Groq cloud LLM support;
- Ollama local LLM support;
- file listing and deletion;
- activity timeline;
- interactive graph visualization;
- responsive Next.js interface.

## 6. System architecture

```text
User
  │
  ▼
Next.js + React frontend
  │  Supabase authentication
  │  REST requests
  ▼
FastAPI backend
  │
  ├── File and source management ───────► Neo4j File nodes
  │
  ├── PDF / Excel / OCR / transcription
  │             │
  │             ▼
  │       LLM extraction
  │             │
  │       ┌─────┴─────┐
  │       ▼           ▼
  │   Neo4j        ChromaDB
  │   decisions    raw text + embeddings
  │   relationships
  │       └─────┬─────┘
  │             ▼
  └──────► Query and Impact Agents
                │
                ▼
          Answer + source trace
```

There is no PostgreSQL layer in the current runtime architecture.

## 7. Why two databases are used

### Neo4j: connected organizational knowledge

Neo4j stores nodes such as:

- `Decision`
- `Person`
- `Reason`
- `Alternative`
- `File`
- `Activity`

It stores relationships such as:

- `MADE_BY`
- `BASED_ON`
- `ALTERNATIVE`

This makes questions about relationships and decision history natural to query and display visually.

### ChromaDB: semantic raw-content retrieval

ChromaDB stores chunks of original document text and their embeddings. It can find relevant content even when the user’s words do not exactly match the document’s wording.

For example, a question about “why the database was changed” can retrieve text discussing performance, JSON support, reliability, or operational problems.

The two stores have different roles: Neo4j explains relationships, while ChromaDB retrieves supporting context.

## 8. Original data flow

```text
User uploads a source
        ↓
FastAPI validates the file and checks its hash
        ↓
File parser extracts text
        ↓
OCR or transcription runs when required
        ↓
Groq or Ollama extracts structured decisions
        ↓
Raw text is stored in ChromaDB
        ↓
Decisions and relationships are stored in Neo4j
        ↓
Activity is recorded in Neo4j
        ↓
Agents retrieve graph facts and semantic context
        ↓
The user receives an answer with source trace
```

## 9. Main user journey for the live demo

### Demo preparation

Before presenting, make sure:

- the backend is running on port `8000`;
- the frontend is running on port `3000`;
- Neo4j credentials are configured;
- ChromaDB credentials are configured;
- the selected LLM provider is available;
- one small decision-oriented PDF is ready;
- one prepared question is ready.

### Recommended demonstration

1. Open the Recall.AI login page.
2. Sign in and show the dashboard.
3. Open the upload/query page.
4. Upload a short decision document.
5. Show the successful ingestion result.
6. Open the Knowledge Graph page and point out decision, person, reason, and alternative nodes.
7. Return to the query page and ask:

   > Why did the team choose this option, who was involved, and what alternatives were considered?

8. Show the answer and source trace.
9. Ask an impact question:

   > What could happen if this decision is reversed?

10. Open the Activity page and show the ingestion/query history.
11. Open the existing-file selector and show that the uploaded source can be selected for a source-specific query.

### Strong demo sentence

> “The same uploaded document is represented in two ways: Neo4j shows how the decision is connected to people, reasons, and alternatives, while ChromaDB retrieves the original supporting context for natural-language questions.”

## 10. Example input and expected output

### Example input document

```text
The engineering team decided to move from MySQL to PostgreSQL because of JSON-query limitations and slow search performance. Alice led the evaluation with David and Sarah. MongoDB was considered as an alternative.
```

### Extracted structured knowledge

```text
Decision: Move from MySQL to PostgreSQL
Reason: JSON-query limitations and slow search performance
People: Alice, David, Sarah
Alternative: MongoDB
Topic: Database migration
```

### Possible user question

```text
Why did the engineering team change the database?
```

### Expected system behavior

The Query Agent searches structured Neo4j decisions first and uses ChromaDB for supporting document context. It returns a concise answer and identifies the source document.

## 11. AI and agent design

The system uses specialized agents instead of treating every question identically.

### Router Agent

Classifies a question as either:

- `QUERY` — asks about known decisions or organizational facts;
- `IMPACT` — asks about risks, consequences, or “what if” scenarios.

### Query Agent

Uses:

- Neo4j decision search;
- ChromaDB raw-memory search;
- source filtering;
- LLM synthesis.

### Impact Agent

Uses decision relationships and supporting context to reason about consequences and related decisions.

### Ollama mode

Ollama provides a local LLM option. The system directly executes retrieval tools and then gives the retrieved context to the local model. This makes the project less dependent on a cloud model during demonstrations or privacy-sensitive experiments.

## 12. Technology stack

| Layer | Technology | Role |
|---|---|---|
| Frontend | Next.js, React, TypeScript | User interface and workflows |
| Styling | Tailwind CSS, Framer Motion, GSAP | Responsive visual interface |
| Backend | Python, FastAPI, Uvicorn | REST API and orchestration |
| Agent tooling | LangChain and LangGraph | Tool calling and agent workflows |
| Cloud LLM | Groq | Fast extraction and reasoning |
| Local LLM | Ollama | Local model alternative |
| Graph database | Neo4j AuraDB | Decisions and relationships |
| Vector database | ChromaDB | Semantic raw-content retrieval |
| Authentication | Supabase Auth | Login and session management |
| PDF parsing | PyMuPDF | PDF text extraction |
| Spreadsheet parsing | OpenPyXL and pandas | Excel extraction |
| OCR | Groq vision integration | Image text extraction |
| Transcription | Groq Whisper integration | Audio/video text extraction |
| Messaging | Slack SDK | Slack ingestion |

## 13. Important implementation details

- Uploaded files are checked using SHA-256 content hashes to prevent duplicate ingestion.
- Source identifiers such as `document:filename.pdf`, `audio:meeting.mp3`, and `slack:channel` are used to trace knowledge back to its origin.
- Long content is chunked before LLM processing.
- Neo4j nodes are connected with explicit relationship types.
- ChromaDB stores raw text separately from structured graph facts.
- The frontend sends the selected LLM provider through the `X-LLM-Provider` header.
- Source filters prevent retrieval from unrelated documents.
- The activity timeline records ingestion and query actions.

## 14. What makes the idea different

The project is not only a document chatbot. Its focus is **decision memory**.

A normal document chatbot may answer from text, but Recall.AI also tries to identify:

- what was decided;
- why it was decided;
- who participated;
- which alternatives were considered;
- what impact the decision had;
- how the decision is connected to other organizational knowledge.

This combination of semantic retrieval, structured extraction, and graph-based relationships is the central contribution of the project.

## 15. Current MVP versus future production scope

### Working now

- End-to-end upload-to-query workflow;
- multiple input types;
- graph storage and visualization;
- semantic search;
- agent-based query handling;
- authentication;
- activity history;
- local and cloud LLM options.

### Future improvements

- background processing for large files;
- stronger role-based authorization;
- multi-tenant organization isolation;
- document versioning;
- scheduled connectors;
- evaluation datasets and accuracy metrics;
- answer confidence scoring;
- multilingual support;
- graph conflict detection;
- production observability and retry queues.

## 16. Honest limitations to mention

The current implementation is an MVP, not a final enterprise deployment. The main limitations are:

- ingestion is currently synchronous;
- external services require valid credentials and network access;
- LLM extraction quality depends on the selected model and document quality;
- OCR and transcription can introduce errors;
- Neo4j and ChromaDB are separate services and require configuration;
- authorization and multi-tenant isolation can be strengthened for production;
- large-scale ingestion would benefit from background jobs and a durable queue.

Mentioning these limitations demonstrates technical understanding and gives a clear path for future work.

## 17. Suggested presentation structure

### Slide 1 — Title

Recall.AI: An AI-Powered Organizational Memory and Decision-Reasoning Platform

### Slide 2 — Problem

Important decisions are distributed across documents, meetings, chats, and spreadsheets. The reasoning behind them is difficult to recover.

### Slide 3 — Proposed idea

Convert scattered information into searchable organizational memory using LLM extraction, a knowledge graph, and semantic search.

### Slide 4 — Architecture

Show the frontend → FastAPI → extraction → Neo4j/ChromaDB → agents flow.

### Slide 5 — MVP features

Show upload, graph, query, activity, authentication, and multiple source types.

### Slide 6 — Live demo

Upload a document, show graph creation, ask a question, show source trace.

### Slide 7 — Technical contribution

Explain why Neo4j is used for relationships and ChromaDB for semantic retrieval.

### Slide 8 — Future scope

Background jobs, multi-tenancy, stronger authorization, evaluation, and more connectors.

## 18. Thirty-second elevator pitch

> “Recall.AI is an AI-powered organizational memory system. It ingests documents, spreadsheets, images, audio, video, and Slack content, extracts decisions and their reasoning, and stores the knowledge as both a graph and searchable semantic memory. Users can ask natural-language questions about what was decided, why it was decided, who was involved, and what alternatives or impacts exist. I have already built a working MVP with authentication, file ingestion, Neo4j graph visualization, ChromaDB semantic search, Groq and Ollama support, activity tracking, and agent-based querying.”

## 19. Likely teacher questions and answers

### Why use both Neo4j and ChromaDB?

Neo4j is optimized for relationships and graph traversal. ChromaDB is optimized for semantic similarity search over raw text. They solve different retrieval problems.

### Why not use only keyword search?

Keyword search depends on exact words. Semantic search can retrieve conceptually related content, while the graph provides explicit relationships between decisions and entities.

### Why is this an AI project rather than a normal database project?

The system uses AI for extraction, OCR, transcription, semantic retrieval, question routing, and answer generation. The databases provide reliable memory structures for the AI workflow.

### What happens if the document contains no decision?

The raw content can still be stored in ChromaDB for semantic retrieval. The structured decision graph may contain few or no new decision nodes.

### How do you avoid duplicate uploads?

The backend calculates a SHA-256 hash of the file contents and checks the Neo4j file registry before processing it.

### How do you verify an answer?

The response includes a source trace showing the retrieval tools and source context used to generate it. The user can also query a specific source.

### What is the next major improvement?

The next major improvement is background ingestion with job status, retry handling, and evaluation metrics for extraction and answer quality.

## 20. Final message to the teacher

> “The key achievement at this stage is a working end-to-end MVP, not only a design document. The system already accepts real organizational sources, extracts structured knowledge, stores it in Neo4j and ChromaDB, and answers questions through an interactive interface. The remaining work is mainly production hardening, evaluation, scalability, and additional integrations.”

