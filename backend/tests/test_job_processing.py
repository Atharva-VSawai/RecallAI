import base64
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from domain.job import IngestionJob, JobStatus
from infrastructure.repositories.job_repository import JobRepository


class MemoryJobRepository(JobRepository):
    def __init__(self, job):
        self.job = job

    def create_job(self, job): self.job = job
    def get_job(self, job_id, organization_id=None): return self.job if self.job and self.job.job_id == job_id else None
    def update_job(self, job, expected_version=None): self.job = job; return True
    def get_stale_jobs(self, timeout_seconds): return [self.job] if self.job.status in {JobStatus.QUEUED, JobStatus.PROCESSING} else []
    def transition(self, job_id, from_statuses, to_status):
        if not self.job or self.job.job_id != job_id or self.job.status not in from_statuses:
            return False
        self.job.status = to_status
        return True
    def claim_job(self, job_id, worker_id, lease_seconds): return True
    def release_lease(self, job_id, worker_id): return True
    def complete_job(self, job_id, worker_id, expected_version): return True
    def fail_job(self, job_id, worker_id, expected_version, error_message): return True
    def get_reclaimable_jobs(self): return [self.job] if self.job and self.job.status == JobStatus.PROCESSING else []


def make_job(status=JobStatus.FAILED, organization_id="org-a", project_id="project-a"):
    return IngestionJob(job_id="job-1", organization_id=organization_id, project_id=project_id, user_id="user-a", source_type="PDF", source_id="document:one.pdf", status=status, created_at=1, updated_at=1, input_payload_b64=base64.b64encode(b"pdf-bytes").decode(), source_config={"filename": "one.pdf", "provider": "groq"})


def test_same_user_same_project_job_is_authorized(monkeypatch):
    import api.routes.ingestion_routes as routes
    job = make_job()
    monkeypatch.setattr(routes, "JobService", lambda: SimpleNamespace(get_job=lambda _id: job))
    monkeypatch.setattr(routes, "ProjectService", lambda: SimpleNamespace(get_project_context=lambda *_args: SimpleNamespace(project_id="project-a", organization_id="org-a")))
    user = SimpleNamespace(user_id="user-a", organization_id="org-a")
    assert routes._authorize_job("job-1", user).job_id == "job-1"


@pytest.mark.parametrize("job_kwargs", [{"project_id": "project-b"}, {"organization_id": "org-b"}])
def test_cross_project_or_cross_tenant_job_is_denied(monkeypatch, job_kwargs):
    import api.routes.ingestion_routes as routes
    job = make_job(**job_kwargs)
    monkeypatch.setattr(routes, "JobService", lambda: SimpleNamespace(get_job=lambda _id: job))
    monkeypatch.setattr(routes, "ProjectService", lambda: SimpleNamespace(get_project_context=lambda *_args: SimpleNamespace(project_id="project-a", organization_id="org-a")))
    with pytest.raises(Exception, match="do not have access"):
        routes._authorize_job("job-1", SimpleNamespace(user_id="user-a", organization_id="org-a"))


def test_unknown_job_uses_same_safe_authorization_error(monkeypatch):
    import api.routes.ingestion_routes as routes
    monkeypatch.setattr(routes, "JobService", lambda: SimpleNamespace(get_job=lambda _id: None))
    with pytest.raises(Exception, match="do not have access"):
        routes._authorize_job("missing", SimpleNamespace(user_id="user-a", organization_id="org-a"))


def test_job_state_transitions_are_conditional():
    from application.services.job_service import JobService
    repo = MemoryJobRepository(make_job(JobStatus.PROCESSING))
    service = JobService(repo)
    assert service.retry_job("job-1") is False
    assert service.cancel_job("job-1") is True
    assert service.cancel_job("job-1") is False


def test_stale_detection_transitions_only_active_jobs():
    from application.services.job_service import JobService
    repo = MemoryJobRepository(make_job(JobStatus.PROCESSING))
    assert JobService(repo).check_stale_jobs(1) == 1
    assert repo.job.status == JobStatus.STALE


def test_retry_dispatches_durable_file_input(monkeypatch):
    import api.routes.ingestion_routes as routes
    job = make_job()
    class FakeService:
        def get_job(self, _id): return job
    monkeypatch.setattr(routes, "JobService", FakeService)
    monkeypatch.setattr(routes, "ProjectService", lambda: SimpleNamespace(get_project_context=lambda *_args: SimpleNamespace(project_id="project-a", organization_id="org-a")))
    from fastapi import BackgroundTasks
    background = BackgroundTasks()
    routes._dispatch_job(job, background)
    assert background.tasks and background.tasks[0].kwargs["file_bytes"] == b"pdf-bytes"


def test_runner_modules_do_not_access_chroma_collection_directly():
    for name in ("ingestion/job_runner.py", "ingestion/teams.py"):
        assert "_collection" not in Path(name).read_text(encoding="utf-8")


def test_vector_repository_requires_provenance_and_tenant_metadata(monkeypatch):
    import db.chroma as chroma
    collection = MagicMock()
    monkeypatch.setattr(chroma, "_collection", collection)
    repo = chroma.ChromaVectorStoreRepository()
    with pytest.raises(ValueError):
        repo.add_vectors(["text"], [[0.1]], [{}], ["id"])
    repo.add_vectors(["text"], [[0.1]], [{"organization_id": "org-a", "project_id": "p-a", "document_id": "d", "chunk_id": "c", "content_hash": "h"}], ["id"])
    collection.upsert.assert_called_once()


def test_vector_query_and_delete_include_both_tenant_dimensions(monkeypatch):
    import db.chroma as chroma
    collection = MagicMock()
    collection.query.return_value = {"documents": [["a"]], "metadatas": [[{"organization_id": "org-a", "project_id": "p-a"}]]}
    monkeypatch.setattr(chroma, "_collection", collection)
    repo = chroma.ChromaVectorStoreRepository()
    assert repo.query_vectors([0.1], 1, "org-a", "p-a")
    repo.delete_by_project("org-a", "p-a")
    assert collection.query.call_args.kwargs["where"] == {"$and": [{"organization_id": {"$eq": "org-a"}}, {"project_id": {"$eq": "p-a"}}]}
    assert collection.delete.call_args.kwargs["where"] == {"$and": [{"organization_id": {"$eq": "org-a"}}, {"project_id": {"$eq": "p-a"}}]}


def test_graph_identity_is_deterministic(monkeypatch):
    import db.neo as neo
    session = MagicMock()
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    monkeypatch.setattr(neo, "_driver", driver)
    first = neo.neo_store("topic", "decision", "reason", "doc-a", project_id="p-a", organization_id="org-a")
    second = neo.neo_store("topic", "decision", "reason", "doc-a", project_id="p-a", organization_id="org-a")
    assert first == second
    assert "MERGE (d:Decision" in session.run.call_args_list[0].args[0]


def test_file_retrieval_excludes_soft_deleted_records():
    source = Path("db/file_registry.py").read_text(encoding="utf-8")
    assert source.count("f.deleted_at IS NULL") >= 2


def test_project_deletion_requires_organization_scope():
    source = Path("application/services/project_service.py").read_text(encoding="utf-8")
    assert "n.organization_id = $organization_id" in source
    assert "Project {id: $project_id, organization_id: $organization_id}" in source


def test_runtime_paths_do_not_create_neo4j_schema():
    assert "ensure_search_indexes" not in Path("main.py").read_text(encoding="utf-8")
    assert "_ensure_constraints" not in Path("application/services/project_service.py").read_text(encoding="utf-8")


def test_slack_sync_has_stable_message_claim_and_exclusive_boundary():
    source = Path("ingestion/slack.py").read_text(encoding="utf-8")
    assert "SlackMessage" in source and "message_id" in source
    assert "inclusive=False" in source


def test_teams_processing_state_is_explicit_and_retryable():
    source = Path("ingestion/teams.py").read_text(encoding="utf-8")
    assert "processing_state='COMPLETED'" in source
    assert "processing_state='FAILED'" in source
    assert "WHERE m.processing_state = 'COMPLETED'" in source


def test_webhook_dispatches_teams_job():
    source = Path("api/routes/teams_routes.py").read_text(encoding="utf-8")
    assert "sync_subscription, subscription_id, background_tasks" in source


def test_stale_is_terminal_in_frontend_polling():
    source = Path("../frontend/lib/api.ts").read_text(encoding="utf-8")
    assert '"STALE"' in source and "must be retried" in source


def test_file_pagination_is_bounded_and_returns_metadata():
    source = Path("api/routes/file_routes.py").read_text(encoding="utf-8")
    assert "le=100" in source and "has_more" in source and "total" in source


def test_activity_failures_are_not_returned_as_empty_success():
    source = Path("infrastructure/repositories/activity_repository.py").read_text(encoding="utf-8")
    assert "raise RuntimeError(\"Activity storage is unavailable\")" in source

