# Recall.AI Project Scope Freeze

## Freeze decision

Phase 1 freezes the current Recall.AI project as a working prototype and academic project foundation. Future work may improve its internal design, but it must preserve the approved product purpose and current demonstrable features unless the supervisor approves a scope change.

This document is a scope-control document. It does not claim that the project already satisfies all university requirements.

## Product boundary

Recall.AI is an organizational memory and reasoning platform. Its boundary begins when a user supplies an organizational source or question and ends when the system returns searchable memory, extracted decision information, graph data, activity information, or a source-management result.

### Included source types

- PDF documents
- Excel workbooks
- Images
- Audio and video files
- Slack channel history

### Included user workflows

1. Register or log in.
2. Open the knowledge/query area.
3. Upload or ingest a supported source.
4. Detect an already-registered uploaded file.
5. Extract and store decision-related information.
6. Ask a natural-language question.
7. Inspect answer reasoning and source traces.
8. Filter a query by source.
9. View activity.
10. View graph data.
11. List, inspect, and delete registered sources.

## Non-goals for this project version

- General-purpose enterprise content management.
- Full document collaboration or editing.
- A replacement for Slack, email, or file storage.
- Training a foundation model.
- Guaranteed legal, financial, medical, or operational advice.
- Automatic irreversible business decisions.
- New product domains unrelated to organizational decisions.

## Baseline architecture boundary

The current implementation is intentionally recorded as:

Frontend → FastAPI routes → ingestion/agent/tool modules → Neo4j and ChromaDB

Supabase Auth is currently integrated in the frontend. Backend enforcement is a later approved phase and is not part of this freeze implementation.

## File classification

### Active runtime files

These are part of the current application path and must not be removed during Phase 1:

- backend/main.py
- backend/activity_store.py
- backend/core/
- backend/agents/
- backend/ingestion/
- backend/db/
- backend/tools/
- backend/services/
- frontend/app/
- frontend/components/
- frontend/contexts/
- frontend/lib/
- frontend/public/

### Active configuration and dependency files

- backend/requirements.txt
- frontend/package.json
- frontend/tsconfig.json
- frontend/next.config.mjs
- frontend/eslint.config.mjs
- frontend/postcss.config.mjs
- package.json
- package-lock.json
- .gitignore files

### Diagnostic or manual verification scripts

These files are not imported by the application routes. They may be useful for manual environment checks and are retained during Phase 1:

- backend/check.py — direct Neo4j inspection and storage smoke script.
- backend/chroma_test.py — manual ChromaDB store/search check.
- backend/image_test.py — image OCR import/manual instruction script.
- backend/slack_test.py — direct Slack API check.
- backend/test_keys.py — direct external-provider key check.
- generate_sample.py — standalone sample-data utility.

These scripts must not be treated as the project’s automated test suite. They should either be replaced by formal tests in the testing phase or explicitly listed as manual diagnostic tools.

### Legacy or experimental scaffolding

The following files are marked for review in a later phase and must not be used as the basis for new features until reviewed:

- backend/agent.py — older standalone agent path; current routes use backend/agents/router.py.
- backend/tools/graph.py — incomplete graph-builder scaffold and not part of the current route path.
- backend/tools/nodes.py — minimal state type used by the incomplete scaffold.
- backend/services/__init__.py — empty package placeholder; no active service implementation currently exists.
- backend/db/supabase_client.py — legacy/incomplete backend Supabase client path; current frontend authentication uses frontend/lib/supabase.ts.

No legacy file is deleted in Phase 1 because the repository contains user changes and these files may still be referenced by manual experiments or prior demonstrations. Phase 2 must decide removal or migration after import and runtime verification.

### Generated or local data

The following are not application source of truth:

- backend/chroma_db/
- backend/graph_response.json
- backend/data/dummy.txt
- root image/logo assets used by documentation or branding

Generated data must not be used as proof of a reproducible database schema. It should be regenerated or excluded from academic evidence in later phases.

### Feature and planning documents

The root Markdown files contain implementation notes, audit findings, design proposals, and submission planning. They are documentation assets, not runtime modules. In particular:

- UNIVERSITY_REQUIREMENTS_IMPLEMENTATION_PLAN.md is the ordered future implementation plan.
- PROJECT_AUDIT_REPORT.md records prior technical audit findings.
- UNIVERSITY_EVALUATION.md records academic evaluation context.
- DEVELOPMENT_ROADMAP.md records the broader roadmap.

## Phase 1 change policy

Allowed:

- Add requirements and scope records.
- Add requirement traceability.
- Correct documentation that makes the current baseline materially inaccurate.
- Mark legacy or diagnostic files in documentation.

Not allowed:

- Moving or renaming runtime files.
- Deleting files without confirmed zero use and team approval.
- Changing routes, data stores, authentication behavior, prompts, UI behavior, or dependencies.
- Adding PostgreSQL, repositories, authentication middleware, logging, exception handlers, or tests from later phases.

## Scope-change process

Any proposed change to the frozen scope must record:

1. Requested change.
2. Reason and academic value.
3. Affected features and files.
4. Additional effort and risks.
5. Regression impact.
6. Supervisor/team approval.
7. Updated requirements and traceability entries.

## Phase 1 completion statement

The current scope is frozen when REQUIREMENTS.md, PROJECT_SCOPE.md, and REQUIREMENT_TRACEABILITY.md are reviewed together and the team agrees that the current feature set and future university work are clearly separated.

