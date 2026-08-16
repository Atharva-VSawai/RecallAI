# Phase 0 change boundary

This worktree contains pre-existing local changes. Phase 0 does not reset,
checkout, stage, or delete any of them.

## In scope for Phase 0

- `backend/application/services/project_service.py`
- `backend/application/services/auth_service.py`
- `backend/application/services/query_service.py`
- `backend/core/llm.py`
- `backend/main.py`
- `backend/tests/test_critical_flows.py`

## Preserved as pre-existing work

All other modified, deleted, and untracked files shown by `git status` are
outside this Phase 0 change set. They may include earlier retrieval,
ingestion, frontend, job, migration, documentation, and asset changes.

## Verification boundary

Only the files listed above are changed by Phase 0. Review and commit them
separately from the remaining worktree changes after tests pass.
