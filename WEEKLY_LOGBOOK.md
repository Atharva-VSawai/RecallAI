# Weekly Development Logbook

## Instructions

This is a realistic proposed logbook draft. Replace names, dates, supervisor comments, and completed status with truthful records. Do not submit invented work as completed work.

## Week 1 — Problem definition and feasibility

### Objectives

- Define the organizational memory problem.
- Identify target users and data sources.
- Review project feasibility.
- Confirm major project scope with supervisor.

### Work record

- Studied decision-loss problems in documents, Slack, and meetings.
- Defined system goals: ingestion, structured extraction, semantic search, graph reasoning, and impact analysis.
- Identified functional requirements and non-functional requirements.
- Confirmed the need for authentication, source filtering, and activity tracking.

### Evidence

- Problem statement
- Scope document
- Supervisor meeting notes
- Initial requirements list

### Next week

- Literature review and technology comparison.

## Week 2 — Literature review and technology selection

### Objectives

- Study RAG systems.
- Study graph databases and knowledge graphs.
- Study semantic embeddings.
- Study agent orchestration.
- Compare relational, graph, and vector storage.

### Work record

- Collected verified IEEE, ACM, and Springer papers.
- Recorded each paper's problem, method, findings, and relevance.
- Mapped research findings to Neo4j, ChromaDB, embeddings, and agent routing.
- Documented why the system uses multiple storage models.

### Evidence

- Literature matrix
- Citation file
- Research-to-feature mapping

### Next week

- Design system architecture and diagrams.

## Week 3 — Architecture and requirements

### Objectives

- Produce use-case, activity, sequence, class, deployment, and ER diagrams.
- Define current architecture and target three/four-layer architecture.
- Define module responsibilities.

### Work record

- Documented frontend, API, agent, ingestion, and data layers.
- Identified missing service and repository boundaries.
- Defined API contracts.
- Designed authentication and authorization flow.

### Evidence

- ARCHITECTURE.md
- Diagram exports
- API contract document

### Next week

- Refactor backend into layers.

## Week 4 — Backend architecture refactoring

### Objectives

- Create API, application, domain, and infrastructure packages.
- Extract services from main.py.
- Introduce repository interfaces.
- Define custom exceptions.

### Work record

- Created route modules and DTOs.
- Added QueryService, IngestionService, FileService, and ActivityService.
- Added repository protocols.
- Moved provider access behind adapters.
- Added a global exception handler.

### Evidence

- Git commits
- Before/after architecture diagram
- Unit tests for services

### Next week

- Implement relational database design.

## Week 5 — Relational database implementation

### Objectives

- Create PostgreSQL schema.
- Add master and child tables.
- Add foreign keys, constraints, and indexes.
- Add migrations.

### Work record

- Created Organization, UserProfile, Source, Decision, Person, Activity, and IngestionJob tables.
- Created child tables for reasons, alternatives, and participants.
- Added normalization and referential-integrity constraints.
- Added database migration files.

### Evidence

- ER diagram
- Migration output
- Schema screenshots
- Constraint/index tests

### Next week

- Add procedures, functions, and transaction handling.

## Week 6 — Database programming and synchronization

### Objectives

- Add stored procedure and database functions.
- Define relational transaction boundary.
- Document Neo4j/Chroma synchronization.
- Add idempotency handling.

### Work record

- Added ingestion finalization procedure.
- Added source duplicate-check function.
- Added transaction rollback tests.
- Added reconciliation status between PostgreSQL, Neo4j, and ChromaDB.

### Evidence

- Procedure/function scripts
- Transaction test output
- Synchronization design

### Next week

- Implement authentication and authorization.

## Week 7 — Authentication and authorization

### Objectives

- Verify Supabase JWTs in the backend.
- Add organization and user scoping.
- Add role-based authorization.
- Protect all routes.

### Work record

- Added bearer-token dependency.
- Derived user identity from token claims.
- Added source ownership checks.
- Restricted delete operations to authorized users.
- Added unauthorized and forbidden API tests.

### Evidence

- Auth flow diagram
- Test screenshots
- API response examples

### Next week

- Implement structured logging and exception handling.

## Week 8 — Logging and exception handling

### Objectives

- Add structured logs.
- Define log levels.
- Add request IDs.
- Add custom exceptions.
- Standardize error responses.

### Work record

- Configured JSON logging.
- Redacted user content and authorization data.
- Added ValidationError, StorageError, IngestionError, and AuthorizationError.
- Added global FastAPI handlers.
- Added standard error response DTO.

### Evidence

- Log examples
- Error response screenshots
- Exception mapping table

### Next week

- Strengthen validation and security.

## Week 9 — Validation and security

### Objectives

- Add strict frontend and backend validation.
- Add upload limits.
- Add MIME/magic-byte checks.
- Restrict CORS.
- Add rate limits.

### Work record

- Added Pydantic bounds.
- Added upload validation.
- Added provider allowlist.
- Added secure CORS origins.
- Added rate-limit tests.
- Performed security review against injection, XSS, CSRF, and error leakage.

### Evidence

- Security test report
- Validation screenshots
- CORS/rate-limit evidence

### Next week

- Build automated testing suite.

## Week 10 — Testing

### Objectives

- Implement unit tests.
- Implement integration tests.
- Implement API tests.
- Complete test-case matrix.
- Generate coverage report.

### Work record

- Tested parsers, validators, services, repositories, and auth policies.
- Tested all API endpoints.
- Tested failure and unauthorized paths.
- Ran database constraint and transaction tests.
- Recorded actual test results.

### Evidence

- Test report
- Coverage report
- API collection
- Screenshots

### Next week

- Documentation and deployment.

## Week 11 — Documentation and deployment

### Objectives

- Complete README and technical documents.
- Deploy frontend and backend.
- Configure external services.
- Capture screenshots and diagrams.

### Work record

- Completed installation and troubleshooting guide.
- Completed deployment diagram.
- Deployed test environment.
- Verified login, ingestion, query, activity, graph, and deletion flows.

### Evidence

- Deployed URLs
- Screenshots
- Deployment logs
- Final documents

### Next week

- Final evaluation and viva preparation.

## Week 12 — Final verification and viva preparation

### Objectives

- Conduct complete regression test.
- Prepare presentation.
- Prepare viva questions.
- Verify checklist.
- Obtain supervisor sign-off.

### Work record

- Re-ran all test cases.
- Prepared architecture, database, security, and research explanations.
- Practiced failure scenarios and design trade-offs.
- Confirmed that all claims in the report are supported by evidence.

### Evidence

- Final submission checklist
- Presentation
- Viva question bank
- Supervisor approval

