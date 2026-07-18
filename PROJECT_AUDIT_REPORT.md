# Recall.AI — Complete Architecture and Review Report

## Scope

This report consolidates the project understanding, backend review, database review, security audit, frontend review, and logging/exception-handling review. It is based on the repository contents. No code was changed during the reviews.

Sensitive environment-variable values are intentionally excluded.

---

# 1. Project Understanding

## Problem solved

Recall.AI is an organizational memory and reasoning platform. It ingests company knowledge from Slack, PDFs, Excel files, images, audio, and video; extracts decisions, reasons, people, alternatives, topics, timestamps, and impacts; and makes the information searchable through natural language.

The system stores:

- Structured decisions and relationships in Neo4j.
- Raw content chunks and embeddings in ChromaDB.

Users can ask what was decided, why it was decided, who was involved, what alternatives were considered, and what could break if a decision changes.

## Overall architecture

The project contains:

1. A Next.js frontend for authentication, navigation, ingestion, querying, activity history, and graph visualization.
2. A FastAPI backend for ingestion, agent orchestration, LLM calls, database operations, and API responses.

The frontend communicates with the backend over HTTP. Supabase is used by the frontend for authentication. The backend does not visibly validate Supabase JWTs.

## Technology stack

### Frontend

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS
- Framer Motion
- GSAP
- Lucide React
- React Force Graph 2D/3D
- Radix UI
- Supabase JavaScript client

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic and Pydantic Settings
- LangChain
- LangGraph
- LangChain Groq
- LangChain Ollama

### AI and processing

- Groq llama-3.3-70b-versatile for reasoning and extraction
- Groq Vision for image OCR
- Groq Whisper for audio/video transcription
- PyMuPDF for PDF extraction
- OpenPyXL for Excel extraction

### Storage

- Neo4j AuraDB
- ChromaDB Cloud
- Supabase Auth

## Folder structure

~~~text
recallAi/
├── README.md
├── package.json
├── backend/
│   ├── main.py
│   ├── agent.py
│   ├── activity_store.py
│   ├── requirements.txt
│   ├── core/
│   ├── agents/
│   ├── ingestion/
│   ├── db/
│   ├── tools/
│   ├── data/
│   └── graph_response.json
├── frontend/
│   ├── app/
│   ├── components/
│   ├── contexts/
│   ├── lib/
│   ├── public/
│   └── configuration files
└── feature and implementation documentation
~~~

There is no dedicated SQL, migration, ORM model, controller, service, or repository hierarchy.

## Important frontend files

- frontend/app/layout.tsx — global shell, fonts, providers, navbar, footer
- frontend/app/query/page.tsx — query and ingestion workspace
- frontend/app/activity/page.tsx — activity polling and display
- frontend/app/graph/page.tsx — 2D/3D graph
- frontend/contexts/AuthContext.tsx — Supabase session state
- frontend/contexts/ThemeContext.tsx — theme state
- frontend/lib/api.ts — backend API client
- frontend/components/FileSelector.tsx — file list, selection, search, deletion

## Important backend files

- backend/main.py — FastAPI routes and request models
- backend/agents/router.py — query classification
- backend/agents/query_agent.py — history and decision questions
- backend/agents/impact_agent.py — what-if and risk questions
- backend/agents/ingestion_agent.py — Slack ingestion agent
- backend/ingestion/pipeline.py — common extraction and storage
- backend/ingestion/excel.py — spreadsheet extraction
- backend/ingestion/image.py — image OCR
- backend/ingestion/audio.py — transcription
- backend/ingestion/slack.py — Slack retrieval
- backend/db/neo.py — Neo4j access
- backend/db/chroma.py — ChromaDB access
- backend/db/file_registry.py — file hashes and metadata
- backend/activity_store.py — activity persistence
- backend/tools/ — agent tools
- backend/core/config.py — settings
- backend/core/llm.py — LLM provider factory

## Agent flow

~~~text
Question
  ↓
Router Agent
  ├── QUERY  → Query Agent
  └── IMPACT → Impact Agent
~~~

The Query Agent searches structured decisions and raw semantic memory. The Impact Agent searches related decisions, decisions by person, and raw semantic memory. The Ingestion Agent validates and stores Slack content.

## Data model

No relational tables, SQL migrations, or ORM models exist.

Neo4j node labels:

- Decision
- Person
- Reason
- Alternative
- File
- Activity

Relationships:

~~~text
(:Decision)-[:MADE_BY]->(:Person)
(:Decision)-[:BASED_ON]->(:Reason)
(:Decision)-[:ALTERNATIVE]->(:Alternative)
~~~

Files and decisions are related through matching source properties rather than a direct graph relationship.

ChromaDB uses a collection named notes. Raw content is chunked, embedded, and stored with source metadata.

## Authentication flow

Authentication is frontend-only through Supabase Auth:

1. Login calls Supabase sign-in.
2. Signup calls Supabase sign-up.
3. Password recovery calls Supabase password reset.
4. AuthContext reads the session and redirects unauthenticated users.

The backend accepts user IDs but does not visibly verify Supabase tokens. This creates a critical authentication and authorization gap.

## Main data flows

### Query

~~~text
Frontend
  ↓ POST /query
FastAPI
  ↓
Router Agent
  ↓
Query or Impact Agent
  ↓
Neo4j and ChromaDB tools
  ↓
LLM answer
  ↓
Activity event
  ↓
Frontend response
~~~

### File ingestion

~~~text
Browser file
  ↓ POST /ingest/upload
SHA-256 duplicate check
  ↓
PDF/Excel/OCR/transcription extraction
  ↓
Raw content → ChromaDB
  ↓
Structured decisions → Neo4j
  ↓
File metadata → Neo4j
  ↓
Activity event → Neo4j
~~~

### Slack ingestion

~~~text
POST /ingest/slack
  ↓
Slack channel history
  ↓
Username resolution
  ↓
Ingestion Agent
  ↓
ChromaDB + Neo4j
  ↓
Activity event
~~~

---

# 2. Backend Review

Overall backend score: 5.2/10

## Controllers — 5/10

Current implementation: all controllers are concentrated in backend/main.py.

Strengths:

- Clear endpoint naming.
- Pydantic request models for query and Slack.
- Threadpool execution for synchronous work.
- Main workflows are easy to find.

Weaknesses and smells:

- main.py mixes routing, validation, orchestration, activity logging, and database access.
- Broad exception handling is repeated.
- Expensive work remains tied to HTTP request lifecycles.
- Routes depend directly on concrete agents and database functions.
- Response models are mostly implicit dictionaries.
- Dynamic imports occur inside route functions.
- Graph code accesses a private database driver.

SOLID concerns:

- Single Responsibility Principle violation.
- Dependency Inversion Principle violation.
- Open/Closed Principle violation for new ingestion formats.

Scalability: no durable queue, background job model, cancellation, or progress tracking.

## Services — 4/10

No real service layer exists. backend/services contains only an empty initializer.

Responsibilities are distributed across main.py, ingestion/pipeline.py, agents, tools, and activity_store.py.

Issues:

- No application-service boundary.
- pipeline.py extracts, calls the LLM, stores vectors, and writes Neo4j.
- ingestion_tools.py duplicates ingestion behavior.
- Agents directly invoke storage tools.
- Provider-specific logic is scattered.

Professional direction: introduce QueryService, IngestionService, FileService, ActivityService, and GraphService.

## Repository pattern — 4/10

The closest data-access modules are backend/db/neo.py, backend/db/chroma.py, backend/db/file_registry.py, and backend/activity_store.py.

Issues:

- No repository interfaces or protocols.
- Global drivers are created at import time.
- Multiple Neo4j drivers exist.
- Routes and agents depend directly on concrete functions.
- Database errors are not translated into domain errors.

Professional direction: repository interfaces, dependency injection, centralized connection lifecycle, explicit transaction boundaries, and separate persistence/API models.

## Middleware — 2/10

The only application middleware is CORS in backend/main.py. There is no middleware for authentication, authorization, request IDs, rate limiting, metrics, exception normalization, or request-size enforcement.

The current CORS policy allows every origin.

## Utilities — 5/10

Utility behavior is scattered across file_registry.py, chroma.py, audio.py, excel.py, and main.py.

Issues:

- Duplicated source-prefix handling.
- Repeated file-type checks.
- No common retry utilities.
- No common validation utilities.
- No centralized source identifier policy.

## Configuration — 6/10

backend/core/config.py centralizes environment configuration. backend/core/llm.py centralizes provider creation.

Strengths:

- Environment variables are centralized.
- Required credentials are typed.
- Groq and Ollama are supported.

Issues:

- No environment-specific configuration model.
- No validation for URLs, providers, timeouts, CORS, or limits.
- Settings are instantiated at import time.
- Unknown providers silently fall back to Groq.
- backend/db/supabase_client.py references settings not defined in core/config.py.

## Authentication — 1/10

The backend does not validate Supabase access tokens. Any caller can potentially call query, file, graph, and ingestion endpoints directly.

Professional fix: validate Supabase JWTs server-side, extract identity from the token, and reject missing or invalid tokens.

## Authorization — 1/10

There are no role, tenant, ownership, or permission checks.

Source filtering is not authorization. File deletion and graph access have no visible ownership checks.

Professional fix: associate resources with users/organizations and enforce permissions before reads and deletes.

## API design — 5/10

Strengths:

- Understandable endpoints.
- Mostly appropriate HTTP verbs.
- Multipart uploads.
- Pydantic input models.

Issues:

- No declared response models.
- Inconsistent errors.
- Raw exception details may be returned.
- User IDs are passed inconsistently.
- No pagination.
- No version prefix.
- No idempotency or job status.
- No explicit request limits.

## Business logic — 5/10

Strengths:

- Clear Query, Impact, and Ingestion concepts.
- Structured extraction uses Pydantic.
- Source filtering exists.
- Duplicate detection uses file hashes.
- Graph and vector retrieval complement each other.

Issues:

- Prompt-driven logic is probabilistic.
- Ingestion logic is duplicated.
- ChromaDB and Neo4j are not atomic together.
- Partial failures may appear successful.
- Decisions are written individually.
- Extracted decisions are not strongly validated or deduplicated.
- Agent fallback loops are duplicated.

## Folder organization — 5/10

Strengths:

- Major technical concerns have recognizable directories.
- Configuration is separated.
- Agents and ingestion are visible.

Issues:

- main.py is overloaded.
- services is empty.
- agent.py appears to be an older alternate path.
- tools/graph.py and tools/nodes.py are incomplete.
- Manual diagnostics are mixed into the backend root.
- No formal test package exists.

Testing score: 2/10. Only manual diagnostic scripts were found.

Observability score: 4/10. Logging exists but lacks structured output, request IDs, metrics, tracing, and job status.

---

# 3. Database Review

Overall database score: 5/10

## Tables

No relational tables exist. Neo4j nodes and a ChromaDB collection are used.

Relevant files:

- backend/db/neo.py
- backend/db/file_registry.py
- backend/activity_store.py
- backend/db/chroma.py

## Entity design

Strengths:

- Decision, person, reason, and alternative concepts are separated.
- Relationships express organizational meaning.
- File and activity metadata are distinct.

Issue: backend/db/neo.py uses action text as the decision merge key.

Why it is a problem: unrelated decisions with identical action text can be merged or overwrite each other.

Professional solution: use a stable decision ID or deterministic source/content hash.

People, reasons, and alternatives are globally merged by name/text.

Why it is a problem: identical names or phrases from different sources can become one shared entity.

Professional solution: define source or organization scope where appropriate.

## Parent and child tables

Not applicable because Neo4j is graph-based.

Logical structure:

~~~text
Decision
 ├── MADE_BY → Person
 ├── BASED_ON → Reason
 └── ALTERNATIVE → Alternative
~~~

## Foreign keys

No foreign keys exist. Files and decisions are connected only through matching source properties.

Why it is a problem: string matching is weaker than a direct graph relationship.

Professional solution:

~~~text
(:Decision)-[:EXTRACTED_FROM]->(:File)
~~~

## Indexes and constraints

No explicit indexes, uniqueness constraints, existence constraints, or type constraints were found.

Why it is a problem: MERGE and search operations may degrade as the graph grows, and application code alone cannot prevent duplicate or malformed nodes.

Recommended schema controls:

- Unique Decision.id
- Unique File.hash
- Index or unique File.source
- Index Person.name
- Unique Activity.id
- Index Activity.user_id
- Index Decision.source

## Transactions and ACID

Individual Neo4j sessions use Neo4j transaction behavior. Ingestion writes to ChromaDB and Neo4j independently.

Relevant files:

- backend/ingestion/pipeline.py
- backend/tools/ingestion_tools.py

Why it is a problem: ChromaDB can succeed while Neo4j fails, or vice versa.

Professional solution: use idempotent workflows with processing states, retries, and compensating cleanup.

## Stored procedures and SQL

No database-side procedures, SQL files, migrations, or SQL queries were found.

Cypher inputs are generally parameterized, so no direct SQL/Cypher injection issue was identified. Input validation for source identifiers, providers, paths, and request bounds remains limited.

---

# 4. Security Audit

## Authentication bypass — Critical

Affected files:

- backend/main.py
- frontend/contexts/AuthContext.tsx
- frontend/lib/api.ts

The frontend checks Supabase sessions, but the backend does not validate access tokens.

Exploit: attackers can call API endpoints directly without logging in.

Fix: validate Supabase JWTs server-side and derive identity from the verified token.

## Authorization failure — Critical

Affected files:

- backend/main.py
- backend/db/file_registry.py
- backend/activity_store.py

There are no ownership, organization, tenant, role, or permission checks.

Exploit: callers may list files, delete sources, read graph data, query shared knowledge, or provide arbitrary user IDs.

Fix: associate resources with users/organizations and enforce permissions before protected operations.

## Wildcard CORS — High

File: backend/main.py

allow_origins=["*"] permits requests from any origin.

Fix: restrict CORS to known frontend origins.

## Missing rate limiting — High

Affected files:

- backend/main.py
- backend/ingestion/audio.py
- backend/ingestion/image.py

There are no upload-size limits, request limits, rate limits, or concurrency controls.

Exploit: attackers can cause LLM cost exhaustion, memory pressure, worker exhaustion, or denial of service.

Fix: add per-user/IP limits, upload limits, timeouts, concurrency controls, and background jobs.

## Insufficient file validation — High

Affected files:

- backend/main.py
- backend/ingestion/audio.py
- backend/ingestion/image.py

Validation mainly checks filename extensions.

Fix: validate MIME type and magic bytes, enforce size/decompression limits, use safe temporary storage, and scan files when required.

## Sensitive information in logs — Medium/High

Potentially logged:

- User questions
- Filenames and source identifiers
- Slack IDs
- Provider errors
- Raw exceptions
- Tool arguments

Affected files:

- backend/agents/query_agent.py
- backend/agents/impact_agent.py
- backend/ingestion/pipeline.py
- backend/ingestion/audio.py
- backend/ingestion/image.py

Fix: redact content, use stable identifiers, and never log full prompts, transcripts, or external API error bodies in production.

## Raw exception disclosure — Medium

File: backend/main.py

Many routes return detail=str(e).

Fix: return generic public errors and keep detailed exceptions in secure server logs.

## Secrets in repository — Low current risk

Affected files:

- backend/.env
- frontend/.env.local
- .gitignore

The environment files exist locally and are ignored. No hardcoded secret values were found in source code.

Fix: verify git history, rotate any exposed credentials, and keep only .env.example templates under version control.

## Password hashing

No application password-storage issue was identified. Password handling is delegated to Supabase Auth.

Affected files:

- frontend/app/login/page.tsx
- frontend/app/signup/page.tsx

Backend API authentication remains missing.

## JWT implementation — Missing on backend

Affected files:

- backend/main.py
- frontend/contexts/AuthContext.tsx

The backend does not verify token signature, expiry, issuer, audience, or claims.

Fix: require and validate Authorization bearer tokens.

## Session management — Medium

Affected files:

- frontend/contexts/AuthContext.tsx
- frontend/lib/supabase.ts

The frontend manages the session, but backend requests are not linked to a verified session.

Fix: enforce backend token validation and handle expiry/revocation consistently.

## SQL injection

No issue identified. SQL is not used, and Cypher inputs are generally parameterized.

Affected files:

- backend/db/neo.py
- backend/db/file_registry.py

## XSS — Low current risk

Affected files:

- frontend/app/layout.tsx
- frontend/app/query/page.tsx

React escapes rendered values by default. dangerouslySetInnerHTML is used for a static theme script.

Fix: keep the script static, never interpolate user data, and add a Content Security Policy.

## CSRF — Conditional Medium

Affected files:

- backend/main.py
- frontend/lib/api.ts

There is no CSRF protection. Current risk is lower because backend cookie authentication is not implemented. Risk increases if cookie sessions are introduced.

Fix: use bearer tokens or implement CSRF tokens and strict origin checks.

## Input validation — Medium

Affected files:

- backend/main.py
- backend/ingestion/slack.py
- backend/core/llm.py

Issues:

- No upper query-length limit.
- No bounded Slack message limit.
- Arbitrary provider values.
- Weak source/path validation.
- No upload-size enforcement.

Fix: add strict Pydantic bounds, provider allowlists, source validation, and upload limits.

---

# 5. Frontend Review

## Project structure — P1

Strengths:

- Clear Next.js App Router structure.
- Shared components, contexts, and API utilities are separated.
- Routes are easy to identify.

Issues:

- app/query/page.tsx contains most feature behavior.
- Visual components and UI primitives share the same component area.
- No feature-oriented folder structure.
- No frontend tests.

## Components and reusability — P0

Issues:

- app/query/page.tsx contains query, five ingestion flows, previews, progress, and response rendering.
- Login, signup, and password-reset pages repeat patterns.
- PDF, Excel, audio, image, and Slack flows duplicate handlers and state.
- Navbar.tsx, MagicBento.tsx, and the graph page are complex.

Professional direction: split into QueryPanel, IngestionTabs, individual ingestion forms, QueryResult, and SourceTraceList.

## State management — P1

Issues:

- Query page has many parallel state variables.
- Invalid state combinations are possible.
- No reducer or state machine.
- ThemeContext.tsx has unused mounted state.
- API authorization is not derived from shared auth state.

Professional direction: use useReducer or a reusable useIngestionTask hook.

## API integration — P0

Strengths:

- Backend calls are centralized in frontend/lib/api.ts.
- Multipart uploads are used.
- Non-2xx responses are generally checked.

Issues:

- Supabase access tokens are not attached.
- User identity is passed as request data.
- IngestSlackResponse is reused for unrelated response types.
- Some functions hide failures by returning empty arrays.
- No timeout, cancellation, or runtime response validation.
- Local API fallback can target the wrong service in production.

Professional direction: use a typed API client with token handling, timeouts, consistent errors, and runtime schemas.

## Validation — P1

Issues:

- No file-size validation.
- No MIME/content validation.
- Limited Slack validation.
- Email validation relies mostly on browser behavior.
- Backend validation is not consistently represented in the UI.

## Error handling — P1

Issues:

- Many failures only go to console.error.
- Empty arrays can hide backend failures.
- No global React error boundary.
- No consistent unauthorized/session-expiration handling.
- No retry/backoff strategy.

## Loading states — P2

Strengths:

- Auth, query, graph, activity, and ingestion flows have loading indicators.
- Buttons are disabled during many operations.

Issues:

- Progress bars are time-based estimates, not actual backend progress.
- No cancellation for long-running requests.
- Activity polling does not clearly pause when the tab is hidden.

## Performance — P1

Issues:

- Heavy visual effects can consume CPU/GPU.
- Graph data is not paginated or limited.
- No request deduplication.
- Activity polling runs every ten seconds regardless of visibility.
- Large graph rendering may become expensive.
- Client-side rendering and animation increase JavaScript cost.

Professional direction: limit graph data, virtualize lists, pause polling when hidden, and reduce effects on low-power devices.

## Accessibility — P1

Strengths:

- Several icon-only controls have aria-label.
- Authentication fields have labels.
- Loading and disabled states are visible.

Issues:

- Errors are not consistently announced with aria-live.
- Some drop zones and clickable containers rely on mouse interaction.
- Graph interactions are not keyboard/screen-reader friendly.
- Focus management is inconsistent.
- Reduced-motion behavior is not clearly implemented.

## Responsiveness — P2

Strengths:

- Tailwind responsive classes are used.
- Mobile navigation exists.
- Graph dimensions adapt to the container.

Issues:

- Effects may be costly on mobile.
- Graph interaction is difficult on touch screens.
- Query workflows can become crowded on small screens.
- Fixed sizing and absolute positioning may cause overflow.

## User experience — P2

Strengths:

- Strong visual identity.
- Clear ingestion feedback.
- Source context and traces improve transparency.
- File selection and deletion are understandable.
- Query suggestions assist first-time users.

Issues:

- Too many workflows are exposed simultaneously.
- Simulated progress can create inaccurate expectations.
- Destructive deletion has no undo.
- Empty, unavailable, and unauthorized states are not always distinguished.

## Code quality — P1

Issues:

- Frequent any usage, especially in graph/page.tsx and FileSelector.tsx.
- Production console logging remains.
- Generic names include BASE, load, result, state, and data.
- Auth form markup is repeated.
- Ingestion handlers and state structures are repeated.
- API types do not accurately represent every response.
- Some comments and documentation refer to outdated behavior.

---

# 6. Logging and Exception Handling Review

Overall quality: 4/10

## Global exception handling — P1

File: backend/main.py

Every route repeats try/except. No global FastAPI exception handlers exist.

Problems:

- Inconsistent error behavior.
- Repeated code.
- Raw implementation details can reach clients.

Professional solution: add centralized handlers for validation errors, domain errors, external-service errors, and unexpected exceptions. Return a request ID and generic public message.

## Custom exceptions — P1

No custom exception hierarchy exists. The project mainly raises ValueError and generic Exception.

Professional solution: define ValidationError, ExternalServiceError, StorageError, IngestionError, and AuthorizationError, then map them centrally to HTTP responses.

## Logging framework — P1

Python logging is used in agents, database adapters, and ingestion modules. No centralized configuration exists.

Missing:

- Global formatter
- Handler configuration
- Log rotation
- JSON output
- Central log-level policy

Professional solution: configure structured logging once at application startup.

## Logging structure — P2

The code uses manual prefixes such as [QUERY AGENT], [NEO4J], and [CHROMA].

Affected files:

- backend/agents/query_agent.py
- backend/agents/impact_agent.py
- backend/ingestion/pipeline.py

Professional solution: use structured fields such as request_id, user_id, operation, source_id, provider, and duration_ms.

## Sensitive information in logs — P0

Potentially logged:

- User questions
- Filenames and source identifiers
- Slack IDs
- Provider errors
- Raw exceptions
- Tool arguments

Affected files:

- backend/agents/query_agent.py
- backend/agents/impact_agent.py
- backend/ingestion/pipeline.py
- backend/ingestion/audio.py
- backend/ingestion/image.py

Professional solution: redact content, use stable identifiers, and never log full prompts, transcripts, or external API error bodies in production.

## Exception swallowing — P1

Affected files:

- backend/db/chroma.py
- backend/ingestion/slack.py
- backend/agents/ingestion_agent.py

Bare exception handling or empty-result fallbacks make failures look like no data.

Professional solution: catch expected exceptions specifically, log stack traces with context, and propagate typed failures.

## Partial failure handling — P0

Affected files:

- backend/ingestion/pipeline.py
- backend/tools/ingestion_tools.py

ChromaDB failures may be logged while processing continues. Neo4j failures may be collected while returning partial success.

Professional solution: use explicit ingestion states, retries, compensating cleanup, and clear partial-failure responses.

## Log levels — P2

Most events use INFO. WARNING and ERROR are inconsistent. There is no clear DEBUG policy.

Recommended policy:

- DEBUG — internal diagnostics, disabled in production
- INFO — successful lifecycle events
- WARNING — recoverable degradation
- ERROR — failed operations
- CRITICAL — service-wide failure

Full user content should not be logged at any level.

## Console/debug logs — P2

Backend diagnostic scripts use print():

- backend/check.py
- backend/test_keys.py
- backend/slack_test.py
- backend/chroma_test.py

Frontend console logging exists in:

- frontend/lib/api.ts
- frontend/components/FileSelector.tsx

Professional solution: separate diagnostic scripts from production code and remove or gate browser console logging.

## Error response consistency — P1

The backend mixes HTTPException, raw exception strings, error dictionaries, and empty-array fallbacks.

Recommended response:

~~~json
{
  "error": {
    "code": "INGESTION_FAILED",
    "message": "Unable to process the file",
    "request_id": "..."
  }
}
~~~

## Frontend exception handling — P1

Affected files:

- frontend/lib/api.ts
- frontend/app/query/page.tsx
- frontend/app/activity/page.tsx

Strengths:

- Most async actions use try/catch.
- Local error states exist.

Weaknesses:

- No global React error boundary.
- No request IDs.
- No centralized client-side error mapping.
- Empty-array fallbacks hide failures.

Professional solution: add an application-level error boundary and shared API error handler.

---

# 7. Consolidated Priorities

## P0

1. Add backend JWT authentication.
2. Add authorization and tenant/resource ownership checks.
3. Stop logging raw questions, prompts, transcripts, and sensitive sources.
4. Prevent partial ingestion from being reported as complete success.
5. Split the large query page and centralize ingestion behavior.
6. Restrict CORS to known origins.

## P1

1. Add global exception handlers and custom exception types.
2. Add typed API response models and consistent error envelopes.
3. Add upload, query, and Slack limits, timeouts, rate limits, and concurrency controls.
4. Add structured centralized logging with request IDs.
5. Add frontend response validation, cancellation, and authentication handling.
6. Improve accessibility, focus management, live regions, and error boundaries.
7. Add service and repository abstractions.
8. Replace any with explicit TypeScript types.
9. Add automated unit and integration tests.

## P2

1. Improve log-level policy and remove production console logs.
2. Optimize graph rendering, animation, and polling.
3. Improve mobile graph controls and reduced-motion support.
4. Add pagination and graph-size limits.
5. Add Neo4j constraints and indexes.
6. Separate feature areas and diagnostic scripts more clearly.

---

# 8. Final Assessment

Recall.AI has a strong product concept and a clear workflow from organizational content to structured memory and natural-language reasoning.

The implementation is currently closer to a working prototype than a production-hardened system.

Largest risks:

- Unauthenticated backend access
- Missing authorization and tenant isolation
- Sensitive data in logs and error responses
- Expensive endpoints without rate limiting
- Partial persistence across Neo4j and ChromaDB
- Large duplicated frontend/backend modules
- Lack of automated testing and centralized observability

Strongest areas:

- Clear Query, Impact, and Ingestion agent concepts
- Multiple source-format integrations
- Combined graph and semantic retrieval
- Source filtering and source traces
- Strong visual frontend workflows
- Useful ingestion and query feedback

