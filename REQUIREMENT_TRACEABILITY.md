# Recall.AI Requirement Traceability Matrix

## Status definitions

- Present — visible in the current project and usable for demonstration.
- Partial — present in a limited or incomplete form.
- Missing — not implemented in the current project.
- Planned — assigned to a later implementation phase.
- Baseline — recorded in Phase 1 without changing runtime behavior.

## Product requirements

| ID | Requirement | Current status | Evidence in current project | Future phase |
|---|---|---|---|---|
| PR-01 | User can register, log in, and recover a password | Partial | frontend/app/login, frontend/app/signup, frontend/app/forgot-password, frontend/lib/supabase.ts | Phase 5 |
| PR-02 | User can upload PDF files | Present | backend/main.py and backend/ingestion/pipeline.py | Regression protection |
| PR-03 | User can upload Excel files | Present | backend/ingestion/excel.py and frontend query flow | Regression protection |
| PR-04 | User can ingest images through OCR | Present | backend/ingestion/image.py and backend/main.py | Regression protection |
| PR-05 | User can ingest audio/video | Present | backend/ingestion/audio.py and backend/main.py | Regression protection |
| PR-06 | User can ingest Slack history | Present | backend/ingestion/slack.py and backend/main.py | Regression protection |
| PR-07 | Duplicate uploaded files are detected | Present | backend/db/file_registry.py and backend/main.py | Phase 3 persistence mapping |
| PR-08 | Decisions and related context are extracted | Present | backend/ingestion/pipeline.py and backend/tools/ingestion_tools.py | Phase 3 persistence mapping |
| PR-09 | User can ask a natural-language question | Present | backend/main.py, backend/agents/router.py, frontend/lib/api.ts | Regression protection |
| PR-10 | Queries can use source filtering | Present | backend/agents/query_agent.py, backend/agents/impact_agent.py, backend/db/neo.py, backend/db/chroma.py | Phase 5 ownership rules |
| PR-11 | Impact analysis is available | Present | backend/agents/impact_agent.py and backend/tools/impact_tools.py | Regression protection |
| PR-12 | User can view graph data | Present | backend/main.py /graph/data and frontend/app/graph/page.tsx | Phase 2 separation |
| PR-13 | User can view activity | Present | backend/activity_store.py, backend/main.py, frontend/app/activity/page.tsx | Phase 2 separation |
| PR-14 | User can list, inspect, and delete sources | Present | backend/db/file_registry.py and /files routes | Phase 5 authorization |

## University requirements

| ID | Requirement | Current status | Evidence or gap | Planned completion |
|---|---|---|---|---|
| U-01 | Proper RDBMS design | Missing | Current persistence is Neo4j plus ChromaDB; no relational schema | Phase 3 |
| U-02 | Parent/master tables | Missing | No PostgreSQL master tables | Phase 3 |
| U-03 | Child tables | Missing | No PostgreSQL child or junction tables | Phase 3 |
| U-04 | Foreign-key relationships | Missing | No relational foreign keys | Phase 3 |
| U-05 | Normalization | Missing | No implemented 1NF/2NF/3NF schema | Phase 3 |
| U-06 | Constraints | Partial | Application-level checks exist, but no relational constraints | Phase 3 |
| U-07 | Indexes | Missing | No PostgreSQL indexes | Phase 3 |
| U-08 | ACID properties | Partial | Individual external-store operations exist; no documented relational transaction boundary | Phase 3 |
| U-09 | Stored procedures | Missing | No stored procedure | Phase 4 |
| U-10 | Database functions | Missing | No database functions | Phase 4 |
| U-11 | Parameterized queries/ORM | Partial | Neo4j queries use parameters in places; no ORM/repository policy | Phase 4 |
| U-12 | No raw SQL in business logic | Missing | Database calls are mixed into current routes/tools | Phase 2 and 4 |
| U-13 | SQL injection protection | Partial | No SQL database exists and no injection test suite exists | Phase 4 and 10 |
| U-14 | REST APIs | Present | FastAPI routes in backend/main.py | Phase 2 modularization |
| U-15 | Backend authentication | Missing | Frontend Supabase session exists; backend does not enforce JWTs | Phase 5 |
| U-16 | Authorization | Missing | No server-side role/ownership policy | Phase 5 |
| U-17 | Configuration and environment management | Partial | backend/core/config.py and frontend environment usage exist | Phase 2 and deployment phase |
| U-18 | Modular backend | Partial | Agents, ingestion, database, and tools are separated; routes remain concentrated in main.py | Phase 2 |
| U-19 | SOLID and clean code | Partial | Some modules have focused responsibilities; route and persistence concerns are mixed | Phase 2 |
| U-20 | Low coupling/high cohesion | Partial | Direct imports and route-level workflows create coupling | Phase 2 |
| U-21 | Global exception handling | Missing | Routes use repeated local try/except blocks | Phase 6 |
| U-22 | Custom exceptions | Missing | Generic ValueError/Exception handling is used | Phase 6 |
| U-23 | Standard error responses | Missing | Error response shapes are not centralized | Phase 6 |
| U-24 | Structured logging | Missing | Current logs are mostly text messages and direct prints in diagnostic scripts | Phase 7 |
| U-25 | Log levels | Partial | Python logging is used in some modules, but no project policy exists | Phase 7 |
| U-26 | Development logbook | Partial | WEEKLY_LOGBOOK.md exists as planning documentation | Phase 11 |
| U-27 | Frontend validation | Partial | Basic form and file handling exists; shared validation is not centralized | Phase 8 |
| U-28 | Backend validation | Partial | Pydantic request models and extension checks exist; limits and business validation are incomplete | Phase 8 |
| U-29 | Three/four-layer architecture | Missing | Current flow is functional but not formally separated into controller, service, repository, database layers | Phase 2 |
| U-30 | Security controls | Partial | Supabase frontend auth exists; backend enforcement and hardening are missing | Phase 5 and security work |
| U-31 | Installation/configuration/troubleshooting/user documentation | Partial | README and supporting Markdown files exist; final consistency review remains | Phase 11 |
| U-32 | Design diagrams | Partial | Architecture and database planning documents exist; final diagrams must match final code | Phase 12 |
| U-33 | Literature review and verified papers | Missing | No verified research evidence is recorded in the source baseline | Phase 13 |
| U-34 | Research gap and implementation influence | Missing | Planned in the research phase | Phase 13 |
| U-35 | Unit, integration, API, error, and edge testing | Missing | Manual diagnostic scripts exist, but no formal automated suite is present | Phase 10 |
| U-36 | Deployment evidence | Partial | Local run instructions and deployment planning exist; reproducible deployment evidence is pending | Phase 14 |

## Traceability to implementation artifacts

| Future phase | Primary artifacts expected | Requirements covered |
|---|---|---|
| Phase 2 — Architecture | backend API/controller modules, services, repository interfaces and implementations | U-12, U-18, U-19, U-20, U-29 |
| Phase 3 — RDBMS | PostgreSQL migrations, models, constraints, indexes, transaction documentation | U-01 through U-08 |
| Phase 4 — Database programming | procedures, functions, repository query policy, injection tests | U-09 through U-13 |
| Phase 5 — Auth and authorization | backend token dependency, role policy, ownership checks, frontend token attachment | U-15, U-16, U-30 |
| Phase 6 — Exceptions | custom exception package, global handlers, error schema | U-21 through U-23 |
| Phase 7 — Logging | logging configuration, request context, redaction policy | U-24 through U-26 |
| Phase 8 — Validation | shared frontend validators, Pydantic schemas, file/business checks | U-27, U-28 |
| Phase 10 — Testing | unit, integration, API, error, edge, and security tests | U-35 |
| Phase 11/12 — Documentation and diagrams | installation, user, API, troubleshooting, architecture and design evidence | U-26, U-31, U-32 |
| Phase 13 — Research | literature review, research gap, verified citations, implementation mapping | U-33, U-34 |
| Phase 14 — Deployment | deployment configuration, environment records, health checks, smoke evidence | U-36 |

## Phase 1 sign-off

- [ ] Requirements reviewed by the team.
- [ ] Current feature set demonstrated or manually verified.
- [ ] Active and non-active files classified.
- [ ] No later-phase code changes included.
- [ ] Supervisor approval recorded outside this file.

