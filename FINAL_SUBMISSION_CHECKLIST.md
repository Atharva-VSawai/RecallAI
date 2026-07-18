# Final Submission Checklist

## Project fundamentals

- [ ] Problem statement approved.
- [ ] Objectives are measurable.
- [ ] Scope and limitations are documented.
- [ ] Functional requirements are documented.
- [ ] Non-functional requirements are documented.
- [ ] User roles are documented.
- [ ] Supervisor approval is recorded.
- [ ] Student names and roll numbers are added.

## Database

- [ ] Proper relational database selected.
- [ ] Master/parent tables implemented.
- [ ] Child tables implemented.
- [ ] Foreign keys implemented.
- [ ] Entity dictionary completed.
- [ ] 1NF explanation completed.
- [ ] 2NF explanation completed.
- [ ] 3NF explanation completed.
- [ ] NOT NULL constraints implemented.
- [ ] UNIQUE constraints implemented.
- [ ] CHECK constraints implemented.
- [ ] Foreign-key delete behavior documented.
- [ ] Indexes implemented.
- [ ] Index rationale documented.
- [ ] Transaction boundary documented.
- [ ] Rollback test completed.
- [ ] ACID behavior explained.
- [ ] Stored procedure implemented.
- [ ] Stored procedure tested.
- [ ] Database function implemented.
- [ ] Database function tested.
- [ ] Parameterized query evidence collected.
- [ ] SQL injection negative tests passed.
- [ ] ER diagram completed.
- [ ] Database migration scripts committed.
- [ ] Database backup/restore procedure documented.

## Backend

- [ ] REST endpoints are versioned.
- [ ] Request DTOs are typed.
- [ ] Response DTOs are typed.
- [ ] OpenAPI documentation is accurate.
- [ ] JWT verification is enforced server-side.
- [ ] User identity is derived from the token.
- [ ] Authorization policy is implemented.
- [ ] Organization/resource ownership is enforced.
- [ ] Configuration is centralized.
- [ ] Environment variables are documented.
- [ ] Secrets are excluded from source control.
- [ ] Backend is modular.
- [ ] Controllers are thin.
- [ ] Services contain workflows.
- [ ] Repositories contain persistence.
- [ ] Provider adapters hide external clients.

## Software engineering

- [ ] SOLID review completed.
- [ ] Single-responsibility violations addressed.
- [ ] Interfaces/protocols added where useful.
- [ ] Dependency injection implemented.
- [ ] Duplicate logic removed.
- [ ] Naming reviewed.
- [ ] Type checking passes.
- [ ] Linting passes.
- [ ] Unused code reviewed.
- [ ] Cohesion and coupling documented.
- [ ] Code review completed by team members.

## Architecture

- [ ] Presentation layer documented.
- [ ] API/application layer documented.
- [ ] Business/domain layer documented.
- [ ] Data/infrastructure layer documented.
- [ ] Architecture diagram completed.
- [ ] Component diagram completed.
- [ ] Sequence diagram completed.
- [ ] Activity diagram completed.
- [ ] Class diagram completed.
- [ ] Deployment diagram completed.
- [ ] Data flow explained.
- [ ] Authentication flow explained.
- [ ] Failure flow explained.

## Logging

- [ ] Structured logging implemented.
- [ ] Log levels documented.
- [ ] Request ID implemented.
- [ ] Error logs implemented.
- [ ] Debug logs are disabled or controlled in production.
- [ ] Sensitive values are redacted.
- [ ] Logs avoid passwords, JWTs, API keys, prompts, and transcripts.
- [ ] Log retention is documented.
- [ ] Development logbook is complete.
- [ ] Supervisor weekly sign-offs are collected.

## Exception handling

- [ ] Global exception handler exists.
- [ ] Custom exception hierarchy exists.
- [ ] Validation errors are standardized.
- [ ] Authentication errors are standardized.
- [ ] Authorization errors are standardized.
- [ ] Storage errors are standardized.
- [ ] External-provider errors are standardized.
- [ ] Unexpected errors do not expose stack traces.
- [ ] Every error includes a request ID.
- [ ] Frontend has an error boundary.
- [ ] Error states have recovery instructions.

## Validation

- [ ] Frontend required-field validation.
- [ ] Frontend file type validation.
- [ ] Frontend file size validation.
- [ ] Backend request validation.
- [ ] Backend MIME/magic-byte validation.
- [ ] Query length validation.
- [ ] Slack limit validation.
- [ ] Provider allowlist validation.
- [ ] Source identifier validation.
- [ ] Pagination bounds.
- [ ] Error messages are accessible.
- [ ] Validation bypass tests completed.

## Documentation

- [ ] Professional README.
- [ ] Installation guide.
- [ ] Troubleshooting guide.
- [ ] Project structure document.
- [ ] Architecture document.
- [ ] Database design document.
- [ ] Security document.
- [ ] Testing document.
- [ ] Deployment document.
- [ ] Weekly logbook.
- [ ] Final checklist.
- [ ] Screenshots added.
- [ ] API examples added.
- [ ] Limitations documented.
- [ ] Future scope documented.

## Research

- [ ] Literature review completed.
- [ ] IEEE papers verified.
- [ ] ACM papers verified.
- [ ] Springer papers verified.
- [ ] Citation style is consistent.
- [ ] Every reference has a DOI, publisher URL, or stable source.
- [ ] Research-to-feature mapping completed.
- [ ] Research limitations discussed.
- [ ] Novelty/engineering contribution explained.

Do not invent citations. Verify every paper through the actual publisher or library source.

## Testing

- [ ] Unit tests implemented.
- [ ] Service tests implemented.
- [ ] Repository tests implemented.
- [ ] Integration tests implemented.
- [ ] API tests implemented.
- [ ] Authentication tests implemented.
- [ ] Authorization tests implemented.
- [ ] Database constraint tests implemented.
- [ ] Transaction rollback tests implemented.
- [ ] Injection tests implemented.
- [ ] Frontend component tests implemented.
- [ ] End-to-end smoke test completed.
- [ ] Test case matrix completed.
- [ ] Coverage report generated.
- [ ] Failed-test fixes documented.

## Demonstration

- [ ] Register/login demo works.
- [ ] Unauthorized access is rejected.
- [ ] Upload demo works.
- [ ] Slack demo works if configured.
- [ ] Query demo works.
- [ ] Impact demo works.
- [ ] Source filter demo works.
- [ ] Activity demo works.
- [ ] Graph demo works.
- [ ] Error scenario demo works.
- [ ] Database transaction demo works.
- [ ] Test report can be shown.
- [ ] Logs can be shown.
- [ ] Diagrams match the implementation.

## Final marks readiness

- [ ] All current claims are truthful.
- [ ] Planned items are not described as completed.
- [ ] Every compulsory requirement has evidence.
- [ ] Source code and report are consistent.
- [ ] Demo environment is reproducible.
- [ ] Backup demo data is available.
- [ ] Presentation is complete.
- [ ] Viva questions have been rehearsed.

