# University Evaluation

## Examiner perspective

This evaluation treats the project as a Computer Engineering final-year major project. It does not use hackathon or startup standards. It evaluates the compulsory academic requirements supplied for the project.

Status labels:

- Present — directly evidenced in current source.
- Partial — some implementation exists, but the university requirement is incomplete.
- Missing — not evidenced in the current source.
- Planned — included in the roadmap but not yet implemented.

## Mark estimate by domain

| Domain | Current level | Indicative marks |
|---|---:|---:|
| Problem definition and implementation idea | Strong | 8/10 |
| Database and database programming | Weak/partial | 3/15 |
| Backend and REST API | Partial | 7/12 |
| Software engineering | Partial | 5/12 |
| Architecture | Partial | 4/10 |
| Logging and exception handling | Weak | 2/7 |
| Validation and security | Weak/partial | 3/8 |
| Documentation and diagrams | Partial | 4/10 |
| Research | Not evidenced | 0/6 |
| Testing | Weak | 2/10 |
| Deployment/demo quality | Partial | 4/10 |
| **Estimated total today** |  | **42/100** |

This is a strict examiner estimate. A generous examiner may award more for the working prototype, but missing compulsory academic artifacts would materially reduce the score.

## Requirement-by-requirement evaluation

### Database

| Requirement | Current Status | Evidence | Why it matters | Missing Items | Recommended Implementation | Expected Marks Improvement |
|---|---|---|---|---|---|---:|
| Proper RDBMS design | Missing | backend/db uses Neo4j and ChromaDB; no SQL schema or migrations | The requirement explicitly asks for an RDBMS | Relational schema, migration scripts, schema explanation | Add PostgreSQL or Supabase Postgres as an academic system-of-record/reporting database while retaining Neo4j for graph reasoning | +3 |
| Parent/master tables | Missing | No relational tables | Demonstrates data ownership and normalization | User, organization, source, decision master tables | Create Organization, UserProfile, Source, Decision master tables | +1 |
| Child tables | Missing | No relational child tables | Demonstrates one-to-many relational design | Reason, Alternative, Participant, Activity child tables | Add child tables with parent IDs | +1 |
| Foreign keys | Missing | No SQL foreign keys | Demonstrates referential integrity | FK definitions and cascade policy | Add foreign keys between master and child entities | +1 |
| Entity design | Partial | Decision, Person, Reason, Alternative nodes in backend/db/neo.py | Shows domain modeling, but not relational modeling | Relational ER design and entity dictionary | Document both graph entities and normalized RDBMS entities | +1 |
| Normalization | Missing | No relational schema | Examiners expect 1NF, 2NF, 3NF reasoning | Normalization explanation | Normalize users, sources, decisions, people, reasons, alternatives, activities | +1 |
| Constraints | Missing | No DB constraints found | Prevents invalid and duplicate records | NOT NULL, UNIQUE, CHECK, FK constraints | Add constraints and demonstrate them in tests | +1 |
| Indexes | Missing | No explicit indexes | Demonstrates performance-aware schema design | Index definitions and rationale | Index email, source hash, source ID, decision topic, activity user/time | +1 |
| ACID properties | Partial | Neo4j session writes exist, but cross-store ingestion is not atomic | Demonstrates transaction correctness | Explicit transaction design and proof | Use Postgres transactions for relational writes and documented compensation for Neo4j/Chroma | +1 |

### Database programming

| Requirement | Current Status | Evidence | Why it matters | Missing Items | Recommended Implementation | Expected Marks Improvement |
|---|---|---|---|---|---|---:|
| Stored procedures | Missing | No stored procedures | Explicit syllabus requirement | Procedure code and execution tests | Add an auditable procedure such as register_ingestion_activity or finalize_ingestion | +1 |
| Database functions | Missing | Operations are Python functions in backend/db | Requirement expects database-side functions or clearly documented application functions | SQL function examples | Add functions for source duplicate checks and activity summaries | +1 |
| Parameterized queries | Partial/Present | Cypher parameters in backend/db/neo.py and file_registry.py | Prevents injection and shows safe data access | Parameterized SQL repository | Use SQLAlchemy/asyncpg parameters for all relational queries | +1 |
| No raw SQL | Not satisfied for academic interpretation | No SQL currently exists, but this also means no stored DB programming | Examiners may expect abstraction or controlled procedures | Repository abstraction and DB routines | Use SQLAlchemy Core/ORM or approved parameterized query layer; keep SQL routines versioned and reviewed | +1 |
| SQL injection protection | Partial | Cypher is parameterized; no SQL API exists | Security requirement must be demonstrated | SQL injection tests and input validation | Add negative API tests with injection payloads and parameterized repository queries | +1 |

### Backend

| Requirement | Current Status | Evidence | Why it matters | Missing Items | Recommended Implementation | Expected Marks Improvement |
|---|---|---|---|---|---|---:|
| REST APIs | Present/Partial | backend/main.py exposes query, ingestion, files, activity, graph routes | Demonstrates service integration | Response schemas, versioning, API tests | Add /api/v1, typed request/response models, OpenAPI examples | +1 |
| Authentication | Partial | Supabase Auth in frontend; backend does not validate tokens | Backend must enforce identity | JWT verification dependency | Verify Supabase JWTs in FastAPI and derive user identity server-side | +2 |
| Authorization | Missing | No role/ownership checks | Protects user and project data | Roles, ownership, tenant policy | Add user/org ownership and admin-only delete policy | +1 |
| Configuration files | Present/Partial | backend/core/config.py, .env files | Shows configurable deployment | Environment-specific validation | Add settings profiles and startup validation | +1 |
| Environment variables | Present | backend/.env and frontend/.env.local are configured and ignored | Avoids hardcoded secrets | .env.example and deployment mapping | Add safe templates and documented secret handling | +1 |
| Modular design | Partial | agents, ingestion, db, tools directories exist | Supports maintainability | API/application/domain/data boundaries | Refactor toward four-layer structure | +1 |

### Software engineering

| Requirement | Current Status | Evidence | Why it matters | Missing Items | Recommended Implementation | Expected Marks Improvement |
|---|---|---|---|---|---|---:|
| SOLID principles | Weak/Partial | Large main.py and pipeline.py; concrete dependencies | Examines design quality | Interfaces, dependency injection, focused classes | Introduce services, repositories, interfaces, and injected providers | +2 |
| Clean code | Partial | Modules are readable but have duplication and broad exceptions | Shows professional coding practice | Consistent naming, types, linting | Remove duplication, type responses, enforce linting | +1 |
| Reusability | Partial | Shared tools and components exist | Avoids repeated logic | Reusable ingestion strategy and API client | Create common ingestion task service/hook | +1 |
| High cohesion | Partial | Agents and ingestion are grouped, but main.py is overloaded | Each module should have one clear reason to change | Smaller modules | Move orchestration into services | +1 |
| Low coupling | Weak | Routes directly call database functions and agents | Makes testing and replacement difficult | Interfaces and dependency injection | Inject repositories, LLM providers, and source processors | +2 |

### Architecture

| Requirement | Current Status | Evidence | Why it matters | Missing Items | Recommended Implementation | Expected Marks Improvement |
|---|---|---|---|---|---|---:|
| Presentation layer | Present | Next.js frontend | Separates user interaction | Formal diagram and boundary definition | Document frontend as presentation layer | +1 |
| Business layer | Partial | Agents and ingestion contain business logic | Demonstrates separation of rules | Explicit application/domain services | Create QueryService, IngestionService, FileService | +1 |
| Data layer | Partial | backend/db modules exist | Demonstrates persistence separation | Repository contracts and transaction boundary | Add repositories and relational adapter | +1 |
| Four-layer architecture | Missing/Partial | No explicit API/application/domain/infrastructure separation | Architecture is a major viva topic | Layered package structure | Implement API, application, domain, infrastructure layers | +2 |

### Logging

| Requirement | Current Status | Evidence | Why it matters | Missing Items | Recommended Implementation | Expected Marks Improvement |
|---|---|---|---|---|---|---:|
| Structured logging | Missing | Python logging uses text prefixes | Supports debugging and observability | JSON fields and request IDs | Configure JSON logging with correlation IDs | +1 |
| Log levels | Partial | INFO, WARNING, ERROR are used inconsistently | Shows operational maturity | Policy and configuration | Define DEBUG/INFO/WARNING/ERROR/CRITICAL policy | +0.5 |
| Error logs | Partial | Errors are logged in ingestion and database paths | Demonstrates failure visibility | Stack traces and safe context | Use logger.exception with redaction | +0.5 |
| Debug logs | Missing/Partial | Manual print diagnostics exist | Supports development troubleshooting | Debug mode policy | Move diagnostics to scripts and use DEBUG logging | +0.5 |
| Development log book | Missing | No weekly progress record evidenced | Mandatory academic evidence | Supervisor-ready progress history | Complete WEEKLY_LOGBOOK.md with truthful entries | +1 |

### Exception handling

| Requirement | Current Status | Evidence | Why it matters | Missing Items | Recommended Implementation | Expected Marks Improvement |
|---|---|---|---|---|---|---:|
| Global exception handler | Missing | Repeated try/except in backend/main.py | Ensures consistent failures | FastAPI handlers | Add handlers for validation, domain, auth, storage, and unexpected errors | +1 |
| Custom exceptions | Missing | Mainly ValueError and generic Exception | Shows domain-aware design | Exception hierarchy | Add domain exceptions and mapping | +0.5 |
| Standard error responses | Missing/Partial | Mixed HTTPException, dictionaries, raw strings | Makes API behavior predictable | Error schema and error codes | Add ErrorResponse and request_id | +0.5 |

### Validation

| Requirement | Current Status | Evidence | Why it matters | Missing Items | Recommended Implementation | Expected Marks Improvement |
|---|---|---|---|---|---|---:|
| Frontend validation | Partial | Required fields, password checks, empty query check | Demonstrates user-input quality | File size/type, Slack bounds, accessible errors | Add shared schemas and field-level messages | +1 |
| Backend validation | Partial | File extension and Pydantic request models | Server must not trust the client | MIME, limits, provider allowlist, source validation | Add strict schemas and centralized validators | +1 |

### Documentation

| Requirement | Current Status | Evidence | Why it matters | Missing Items | Recommended Implementation | Expected Marks Improvement |
|---|---|---|---|---|---|---:|
| README | Present/Partial | Root README and backend README | Basic project orientation | Professional academic README | Replace with this report’s README structure | +0.5 |
| Installation guide | Partial | README setup commands | Enables reproducibility | OS-specific and dependency troubleshooting | Expand README and DEPLOYMENT.md | +0.5 |
| Troubleshooting guide | Partial | Feature markdown files contain troubleshooting fragments | Helps demonstration and viva | Central troubleshooting guide | Add common API, DB, auth, and provider failures | +0.5 |
| Weekly progress log | Missing | No verified logbook | Mandatory academic evidence | Supervisor-signable weekly entries | Complete WEEKLY_LOGBOOK.md truthfully | +1 |
| Architecture diagrams | Partial | README has a high-level diagram | Architecture must be explainable | Formal diagrams | Add ARCHITECTURE.md diagrams | +0.5 |
| ER diagram | Missing | No relational ERD | Required database evidence | ERD and data dictionary | Add planned RDBMS ERD | +1 |
| Sequence diagram | Missing | No formal sequence diagram | Shows runtime behavior | Query and ingestion sequences | Add sequence diagrams | +0.5 |
| Activity diagram | Missing | No formal activity diagram | Shows workflow logic | Ingestion and query activity diagrams | Add activity diagrams | +0.5 |
| Class diagram | Missing | No class diagram | Shows object design | Domain/service/repository class diagram | Add class diagram after refactor | +0.5 |
| Deployment diagram | Missing | No deployment diagram | Shows infrastructure deployment | Component topology | Add deployment diagram | +0.5 |

### Research

| Requirement | Current Status | Evidence | Why it matters | Missing Items | Recommended Implementation | Expected Marks Improvement |
|---|---|---|---|---|---|---:|
| Literature review | Missing | No research chapter evidenced | Major project must demonstrate academic context | Literature review | Compare organizational memory, RAG, graph databases, semantic search, and agent systems | +1 |
| IEEE papers | Missing | No verified citations | Demonstrates scholarly grounding | 3–5 relevant papers | Add verified IEEE sources with DOI/URL | +1 |
| ACM papers | Missing | No verified citations | Demonstrates computing research | 2–4 sources | Add verified ACM sources | +1 |
| Springer papers | Missing | No verified citations | Demonstrates broader literature | 2–4 sources | Add verified Springer sources | +1 |
| Research influence | Missing | Implementation decisions are not mapped to papers | Examiners ask why techniques were chosen | Research-to-feature mapping | Document how RAG, graph modeling, embeddings, and agent routing influenced design | +1 |

### Testing

| Requirement | Current Status | Evidence | Why it matters | Missing Items | Recommended Implementation | Expected Marks Improvement |
|---|---|---|---|---|---|---:|
| Unit testing | Missing/Weak | Manual scripts only | Proves individual correctness | pytest unit suite | Test validators, services, parsers, agents with mocks | +1 |
| Integration testing | Missing | No suite | Proves component integration | DB/provider test environment | Test service-to-repository flows | +1 |
| API testing | Partial | FastAPI routes exist; no automated API suite | Demonstrates interface reliability | TestClient/Postman collection | Test all routes and error statuses | +1 |
| Test cases | Partial | Markdown test plans exist | Shows planned verification | Formal test-case matrix and results | Add IDs, preconditions, input, expected, actual, status | +1 |

## Strict current marks

If submitted today, the project would realistically receive approximately **42/100** under the compulsory requirements.

The working demo and interesting AI/graph idea may earn additional marks from a generous examiner, but the missing RDBMS design, research evidence, diagrams, automated tests, authentication enforcement, layered architecture, and formal exception/logging design would significantly reduce the result.

## Realistic post-roadmap marks

If the roadmap is fully implemented, documented, tested, and demonstrated honestly:

- Conservative outcome: 75/100
- Strong execution: 82–88/100
- Above 90 requires unusually strong research, test evidence, diagrams, viva performance, and polished implementation

## Biggest university weaknesses

1. No proper RDBMS master/child schema.
2. No foreign keys, constraints, indexes, or relational normalization evidence.
3. No stored procedures or database functions.
4. Frontend-only authentication and no backend authorization.
5. No explicit three/four-layer architecture.
6. No custom exceptions or global exception handler.
7. Weak structured logging.
8. No verified literature review or research-to-implementation mapping.
9. No automated unit, integration, or API tests.
10. Missing ER, sequence, activity, class, and deployment diagrams.
11. No verified weekly development log.
12. Large modules and duplicated business logic.

