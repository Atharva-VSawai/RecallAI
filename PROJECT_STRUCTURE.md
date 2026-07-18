# Project Structure

## Root

| Path | Responsibility |
|---|---|
| README.md | Project overview, setup, features, and API summary |
| PROJECT_STRUCTURE.md | Folder-by-folder explanation |
| DEVELOPMENT_ROADMAP.md | Academic implementation plan |
| UNIVERSITY_EVALUATION.md | Examiner-style requirement assessment |
| ARCHITECTURE.md | Current and target architecture diagrams |
| DATABASE_DESIGN.md | Current graph/vector model and proposed RDBMS model |
| SECURITY.md | Security design and implementation requirements |
| TESTING.md | Testing strategy and test case catalog |
| DEPLOYMENT.md | Local and hosted deployment instructions |
| WEEKLY_LOGBOOK.md | Proposed academic progress record |
| FINAL_SUBMISSION_CHECKLIST.md | Final evaluation checklist |
| Feature markdown files | Historical feature and implementation notes |

## Backend

### backend/main.py

FastAPI application entry point. Currently contains FastAPI app creation, CORS configuration, request models, REST routes, file upload orchestration, query orchestration, activity logging, and graph transformation.

Academic target: keep this file limited to route declarations, dependency injection, request/response schemas, and controller calls.

### backend/core/

Cross-cutting configuration and provider factories.

- config.py — environment settings
- llm.py — Groq/Ollama LLM factory
- __init__.py — package initializer

Academic target: add logging configuration, security settings, and application constants.

### backend/agents/

LLM-driven agents.

- router.py — QUERY versus IMPACT classification
- query_agent.py — decision/history retrieval and synthesis
- impact_agent.py — impact/risk analysis
- ingestion_agent.py — ingestion validation and processing
- __init__.py — package initializer

Academic target: agents should orchestrate reasoning while services own business workflows and repositories own persistence.

### backend/ingestion/

Source-specific extraction.

- pipeline.py — common extraction and storage pipeline
- excel.py — Excel normalization
- image.py — OCR
- audio.py — transcription
- slack.py — Slack history retrieval
- __init__.py — package initializer

Academic target: use a source-processor strategy and a service for workflow coordination.

### backend/db/

Data-access adapters.

- neo.py — Neo4j decision storage and search
- chroma.py — vector storage, search, and deletion
- file_registry.py — file metadata and duplicate detection
- supabase_client.py — currently incomplete/unused backend Supabase adapter
- __init__.py — package initializer

Academic target: introduce repository interfaces and a dedicated RDBMS repository for master/child academic requirements.

### backend/tools/

LangChain tool wrappers.

- neo.py — decision search tool
- chroma.py — raw-memory search tool
- impact_tools.py — impact search tools
- ingestion_tools.py — validation and extraction tools
- graph.py — incomplete LangGraph scaffold
- nodes.py — agent state type
- __init__.py — package initializer

Academic target: tools should call application services or repositories rather than embedding storage workflows.

### backend/services/

Currently empty.

Academic target:

~~~text
services/
├── query_service.py
├── ingestion_service.py
├── file_service.py
├── activity_service.py
├── graph_service.py
└── auth_service.py
~~~

### backend/activity_store.py

Neo4j-backed activity event persistence. It stores event type, title, description, timestamp, source, and user ID.

Academic target: move this into ActivityRepository and ActivityService.

### backend/agent.py

Older or alternate single-agent path. Its relationship to agents/router.py should be documented or removed after confirmation.

### backend/data/

Sample or dummy data used by development scripts.

### Backend test/support scripts

- check.py
- chroma_test.py
- image_test.py
- slack_test.py
- test_keys.py

Academic target: migrate real tests into backend/tests/ using pytest. Keep manual diagnostics under scripts/ or docs/.

## Frontend

### frontend/app/

Next.js App Router routes.

- page.tsx — landing page
- layout.tsx — application shell
- login/page.tsx — login
- signup/page.tsx — registration
- forgot-password/page.tsx — recovery
- query/page.tsx — query and ingestion
- activity/page.tsx — activity timeline
- graph/page.tsx — graph visualization
- globals.css — global styles

### frontend/components/

Reusable and visual components.

- Navbar.tsx — navigation, auth controls, API health indicator
- Footer.tsx — footer content
- FileSelector.tsx — files and deletion
- AgentBadge.tsx — agent display
- SourceCard.tsx — tool/source trace
- ThemeToggle.tsx — theme switching
- AnimatedSection.tsx — animation wrapper
- Aurora.tsx — background effect
- BorderGlow.tsx — border effect
- MagicBento.tsx — interactive visual cards
- MouseGlow.tsx — pointer effect
- TextType.tsx — typing animation
- ui/ — button, card, dialog, input, tabs, badge primitives

### frontend/contexts/

- AuthContext.tsx — Supabase session and route protection
- ThemeContext.tsx — theme state and local storage

### frontend/lib/

- api.ts — backend requests and TypeScript response types
- supabase.ts — browser Supabase client
- utils.ts — class-name utility

### frontend/public/

Static logos, icons, favicon, and browser assets.

## Target academic structure

~~~text
backend/
├── api/
│   ├── routes/
│   ├── dependencies.py
│   └── error_handlers.py
├── application/
│   ├── services/
│   └── dto/
├── domain/
│   ├── entities/
│   ├── exceptions/
│   └── interfaces/
├── infrastructure/
│   ├── repositories/
│   ├── providers/
│   └── logging/
├── ingestion/
├── agents/
├── schemas/
├── config/
├── middleware/
└── tests/
~~~

