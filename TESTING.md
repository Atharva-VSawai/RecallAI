# Testing Strategy

## 1. Testing objectives

Testing must demonstrate:

- Correct domain behavior
- Correct API contracts
- Secure authentication and authorization
- Reliable ingestion behavior
- Database integrity
- Error handling
- Frontend validation and user flows
- Regression protection

## 2. Test pyramid

~~~text
                 E2E / Acceptance
                /                 \
          API and Integration Tests
             /                 \
       Service and Repository Tests
          /                 \
            Unit Tests
~~~

## 3. Unit testing

Use pytest for backend unit tests and a modern JavaScript test runner for frontend utilities/components.

### Backend unit targets

- File extension and MIME validation
- SHA-256 duplicate detection
- Excel text extraction
- Source identifier normalization
- Decision validation
- Query routing
- Activity formatting
- Error mapping
- Authorization policy
- Chunking logic
- LLM response parsing

### Frontend unit targets

- Password validation
- Query form validation
- Source context handling
- API error parsing
- File selector filtering
- Theme switching
- Agent badge rendering

## 4. Integration testing

Test the service and repository boundaries:

- IngestionService with mocked source processors.
- IngestionService with a test PostgreSQL database.
- DecisionRepository persistence.
- ActivityRepository persistence.
- ChromaDB adapter with a test collection.
- Neo4j adapter with a test database or test doubles.
- Auth dependency with valid and invalid tokens.

## 5. API testing

Use FastAPI TestClient or HTTPX.

Required endpoint coverage:

| ID | Endpoint | Test |
|---|---|---|
| API-001 | GET /health | Returns successful health response |
| API-002 | POST /query | Valid query returns typed response |
| API-003 | POST /query | Empty query returns 422 |
| API-004 | POST /query | Missing token returns 401 |
| API-005 | POST /query | Unauthorized source returns 403 |
| API-006 | POST /ingest/upload | Supported file succeeds |
| API-007 | POST /ingest/upload | Unsupported extension returns 400 |
| API-008 | POST /ingest/upload | Oversized file is rejected |
| API-009 | POST /ingest/slack | Valid bounded request succeeds |
| API-010 | POST /ingest/slack | Invalid limit is rejected |
| API-011 | GET /files/list | Returns only authorized sources |
| API-012 | DELETE /files/{source} | Admin can delete |
| API-013 | DELETE /files/{source} | Non-admin receives 403 |
| API-014 | GET /activity | Returns organization/user-scoped events |
| API-015 | GET /graph/data | Returns authorized graph data |
| API-016 | Unknown route | Standard 404 response |
| API-017 | Internal failure | Standard 500 response without stack trace |

## 6. Database tests

Required database tests:

- Unique source hash constraint.
- Foreign-key rejection.
- Invalid role rejection.
- Invalid ingestion status rejection.
- Transaction rollback.
- Stored procedure valid transition.
- Stored procedure invalid transition.
- Database function output.
- Index existence verification.
- Query parameterization.
- Injection payload rejection.
- PostgreSQL/Neo4j synchronization reconciliation.

## 7. Security tests

Required cases:

- Missing bearer token.
- Invalid bearer token.
- Expired bearer token.
- Wrong audience/issuer.
- Cross-organization read.
- Cross-organization delete.
- Non-admin delete.
- Oversized upload.
- Malicious filename.
- Unsupported MIME type.
- Injection payload.
- CORS rejection.
- Rate-limit response.
- Error response redaction.

## 8. Frontend tests

Required cases:

- Login error display.
- Signup password mismatch.
- Password reset success.
- Query button disabled for empty input.
- Query loading state.
- Query failure state.
- Source filter context.
- PDF upload success.
- File upload failure.
- File deletion confirmation.
- Activity loading/error/empty states.
- Graph loading/error/empty states.
- Keyboard dialog use.
- Screen-reader error announcement.

## 9. Test case format

Every final test case should contain:

- Test ID
- Requirement
- Component/module
- Preconditions
- Input
- Steps
- Expected result
- Actual result
- Status
- Evidence screenshot or log
- Tester/date

## 10. Coverage target

Suggested academic target:

- Unit coverage: 70% or higher for business logic.
- API endpoint coverage: 100% of public endpoints.
- Authentication/authorization negative tests: 100% of protected routes.
- Critical ingestion paths: 100% happy path and failure path.
- Frontend smoke tests: all main routes.

## 11. Evidence for viva

Prepare:

- Test execution report.
- Screenshots of passing tests.
- API collection.
- Coverage report.
- Database constraint test output.
- Security negative-test output.
- Failed test and correction example.

