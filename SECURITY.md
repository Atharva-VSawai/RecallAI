# Security

## Implemented controls

- Protected API routes require a Supabase bearer token, validated on the backend for signature, expiry, issuer, and audience when configured.
- Application roles are `USER`, `REVIEWER`, and `ADMIN`; destructive file deletion requires `ADMIN`.
- Request schemas bound query length, Slack limits, and channel IDs. Uploads have an explicit size cap and extension allowlist.
- PostgreSQL queries use SQLAlchemy bound parameters. SQL is never constructed from request values.
- API errors use a stable code/message/request-ID envelope and do not expose stack traces.
- Logs are structured and request-correlated. Tokens, uploaded content, prompts, and passwords must never be logged.

## 1. Security objective

Recall.AI handles organizational conversations, documents, decisions, meeting content, and user activity. The security design must protect confidentiality, integrity, availability, authentication state, and source ownership.

## 2. Current security posture

The current frontend uses Supabase Auth, but backend API authentication and authorization are not enforced. CORS is permissive, rate limiting is absent, uploads are weakly validated, and raw exceptions may be exposed.

This document describes the required academic-hardening design.

## 3. Authentication

### Required flow

1. User authenticates with Supabase.
2. Frontend receives the access token.
3. Frontend sends Authorization: Bearer token to the backend.
4. FastAPI authentication dependency validates:
   - Signature
   - Expiration
   - Issuer
   - Audience
   - Subject/user ID
5. Backend creates an authenticated request context.
6. Routes never trust user_id from a body or arbitrary header.

### Files to modify

- frontend/lib/api.ts
- frontend/contexts/AuthContext.tsx
- backend/core/config.py
- backend/api/dependencies.py
- backend/services/auth_service.py
- backend/main.py or backend/api/routes/

## 4. Authorization

Authorization should use organization and role membership.

Minimum roles:

- USER — query owned/authorized sources and create ingestion jobs
- REVIEWER — inspect decisions and activities
- ADMIN — manage organization sources and delete data

Authorization checks:

- Source belongs to the user's organization.
- User is permitted to query the source.
- Only ADMIN can delete source data.
- Activity retrieval is limited to the authenticated user's organization.
- Graph responses are organization-scoped.

## 5. Input validation

Validate at both layers.

### Frontend

- Required fields
- Email format
- Password rules
- Query length
- File size
- File extension and MIME type
- Slack channel format
- Slack message limit

### Backend

- Pydantic strict schemas
- File size limits
- MIME and magic-byte checks
- Provider allowlist
- Safe source identifier validation
- Query length bounds
- Pagination bounds
- Slack limit bounds
- Filename normalization

Never rely on frontend validation alone.

## 6. Upload security

Recommended controls:

- Maximum file size per type.
- Validate magic bytes.
- Store uploads in isolated temporary locations.
- Use random temporary names.
- Delete temporary files in finally blocks.
- Restrict supported codecs and formats.
- Avoid executing uploaded content.
- Scan files where required.
- Limit decompression and parser resource usage.

Relevant current files:

- backend/main.py
- backend/ingestion/audio.py
- backend/ingestion/image.py
- backend/ingestion/excel.py
- backend/ingestion/pipeline.py

## 7. CORS and CSRF

Current CORS allows all origins in backend/main.py.

Required fix:

- Allow only development and production frontend origins.
- Do not combine wildcard origins with credentialed requests.
- Prefer bearer-token authentication for the API.
- If cookies are introduced, implement CSRF protection and strict origin checks.

## 8. Secrets

Secrets must remain in environment variables or a managed secret store.

Required controls:

- Keep backend/.env and frontend/.env.local ignored.
- Add safe .env.example files.
- Never log API keys, tokens, or passwords.
- Rotate credentials if repository history ever contained them.
- Use separate development and production credentials.

## 9. Logging security

Do not log:

- Full documents
- Full transcripts
- Full prompts
- Passwords
- JWTs
- API keys
- Authorization headers
- Unredacted provider responses

Use:

- request_id
- user_id hash or internal ID
- organization_id
- source_id
- operation
- status
- duration_ms

## 10. Exception security

Public responses should not contain raw exception strings, database URLs, provider responses, filesystem paths, or stack traces.

Use a standard response:

~~~json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The uploaded file is not supported",
    "request_id": "request-123"
  }
}
~~~

Detailed stack traces belong only in secure server logs.

## 11. Data protection

Recommended controls:

- HTTPS in deployment.
- Encryption at rest through managed providers.
- Least-privilege database credentials.
- Separate read/write credentials where possible.
- Source ownership metadata.
- Audit trail for deletes and administrative actions.
- Retention policy for source and activity data.

## 12. Security testing

Required negative tests:

- Missing JWT
- Expired JWT
- Invalid JWT
- Wrong organization
- Non-admin deletion
- Path/source traversal input
- Oversized upload
- Wrong MIME type
- Slack limit above maximum
- Query exceeding maximum length
- Cypher/SQL injection strings
- Error response information leakage
- CORS origin rejection
- Rate-limit exhaustion

## 13. Academic security decisions

| Decision | Reason |
|---|---|
| Supabase JWT verification | Reuses existing authentication provider while protecting the API |
| Organization scoping | Demonstrates authorization and prevents cross-user leakage |
| Pydantic validation | Provides typed server-side validation |
| Parameterized queries | Prevents injection |
| Structured redacted logs | Provides auditability without exposing content |
| Standard errors | Prevents internal implementation leakage |
