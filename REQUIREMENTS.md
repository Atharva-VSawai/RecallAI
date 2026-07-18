# Recall.AI Requirements Baseline

## Document status

- Phase: 1 — Requirements and scope freeze
- Status: Baseline for supervisor review
- Product name: Recall.AI
- Current implementation type: Working prototype and academic project foundation
- Source of truth for future implementation: This document and REQUIREMENT_TRACEABILITY.md

## Problem statement

Organizational decisions are distributed across documents, spreadsheets, images, audio/video recordings, and Slack conversations. This makes it difficult to find what was decided, why it was decided, who participated, what alternatives were considered, and what impact a decision may have.

Recall.AI ingests these sources, extracts decision-related information with AI, stores structured relationships in Neo4j, stores searchable raw content in ChromaDB, and answers natural-language questions through specialized agents.

## Current approved feature set

The following features are in the Phase 1 baseline and must continue to work during later implementation:

1. User registration, login, and password recovery through Supabase Auth.
2. PDF file ingestion.
3. Excel and spreadsheet ingestion.
4. Image OCR ingestion.
5. Audio and video transcription followed by ingestion.
6. Slack channel ingestion.
7. SHA-256 duplicate file detection for uploaded files.
8. AI extraction of decisions, reasons, alternatives, people, topics, timestamps, and impacts.
9. Natural-language knowledge queries.
10. Query-agent and impact-agent routing.
11. Source-specific query filtering.
12. Neo4j graph data retrieval and frontend graph visualization.
13. ChromaDB semantic search over raw content.
14. Activity timeline retrieval.
15. Source listing, source checking, and source deletion.
16. Responsive frontend with dark/light theme support.

## Approved project objectives

### O1 — Multi-source ingestion

Accept supported organizational knowledge sources and convert them into text or structured extraction input.

### O2 — Decision extraction

Use AI-assisted processing to identify decisions and related context such as reasons, people, alternatives, topics, timestamps, and impacts.

### O3 — Hybrid knowledge storage

Use graph storage for explicit decision relationships and vector storage for semantic retrieval of source content.

### O4 — Decision-oriented question answering

Route user questions to the appropriate reasoning flow and return an answer with reasoning and source traces.

### O5 — Academic hardening

Add the university-required RDBMS, database programming, backend controls, architecture evidence, validation, testing, documentation, research, and deployment evidence in later phases.

## In-scope work

- Preserve the current Recall.AI product idea and feature set.
- Record the current baseline before architectural changes.
- Add a normalized PostgreSQL system of record in a later phase.
- Add the required controller, service, repository, and database separation in a later phase.
- Enforce backend authentication and authorization in a later phase.
- Add database procedures/functions, validation, exception handling, logging, tests, diagrams, research evidence, and deployment documentation in later phases.

## Out-of-scope for the current baseline

The following are explicitly not implemented in Phase 1:

- PostgreSQL schema or migrations.
- Stored procedures or database functions.
- Backend JWT verification.
- Role-based authorization.
- Repository or layered-architecture refactoring.
- Global exception handling.
- Structured logging.
- Rate limiting or production hardening.
- Automated unit, integration, or API test suites.
- New AI models or new ingestion connectors.
- Product redesign or feature expansion.

## Operational boundaries

- Neo4j remains the current structured graph store.
- ChromaDB remains the current semantic/vector store.
- Supabase remains the current frontend authentication provider.
- The current FastAPI routes remain the active API surface.
- The current Next.js pages and components remain the active presentation layer.
- Existing user-visible behavior is treated as regression-sensitive.

## Current API baseline

| Method | Endpoint | Current purpose |
|---|---|---|
| GET | /health | Report API availability |
| GET | /activity | Return recent activity |
| GET | /files/list | List registered sources |
| GET | /files/check/{source} | Check source metadata |
| DELETE | /files/{source} | Delete source data from current stores |
| POST | /ingest/upload | Ingest supported uploaded files |
| POST | /ingest/audio | Transcribe and ingest audio/video |
| POST | /ingest/image | OCR and ingest images |
| POST | /ingest/slack | Fetch and ingest Slack messages |
| POST | /query | Route and answer a knowledge query |
| GET | /graph/data | Return graph nodes and edges |

## Baseline acceptance criteria

- [ ] The current feature list has been reviewed by the project team.
- [ ] The problem statement and objectives have supervisor approval.
- [ ] The current API surface is recorded.
- [ ] Active, diagnostic, generated, and legacy files are identified.
- [ ] No Phase 2 or later implementation is included in the baseline commit.
- [ ] A smoke test confirms the existing application can still be started using the current setup.

