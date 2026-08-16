from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def _result(**values):
    return SimpleNamespace(single=lambda: values)


def test_delete_file_cleans_source_containers_and_processing_state():
    from db import file_registry

    session = MagicMock()
    session.run.side_effect = [
        _result(deleted_files=1),
        _result(deleted_decisions=1),
        _result(deleted_knowledge=1),
        _result(deleted_orphans=2),
        _result(deleted_documents=1),
        _result(deleted_meetings=1),
        _result(affected_jobs=1),
    ]
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value = session

    with patch.object(file_registry, "_driver", driver):
        result = file_registry.delete_file_by_source("document:hash", "project-a", "org-a")

    assert result["deleted_documents"] == 1
    assert result["deleted_meetings"] == 1
    assert result["affected_jobs"] == 1
    statements = [call.args[0] for call in session.run.call_args_list]
    assert any("DETACH DELETE doc" in statement for statement in statements)
    assert any("ProcessedChunk" in statement and "CANCELLED" in statement for statement in statements)
    for call in session.run.call_args_list:
        assert call.kwargs["organization_id"] == "org-a"
        assert call.kwargs["project_id"] == "project-a"


def test_runner_treats_deleted_job_as_cancelled():
    from ingestion.job_runner import IngestionJobRunner

    service = MagicMock()
    service.get_job.return_value = None
    runner = IngestionJobRunner("job-1", service, "org-a")

    try:
        runner._check_cancelled()
    except Exception as exc:
        assert "deleted while processing" in str(exc)
    else:
        raise AssertionError("A deleted job must stop its worker")


def test_reingestion_repairs_old_deleted_source_before_creating_job(monkeypatch):
    from application.services.ingestion_service import IngestionService
    from application.services.project_service import ProjectContext
    from application.services.auth_service import AuthenticatedUser
    from fastapi import BackgroundTasks

    cleanup = MagicMock(return_value={})
    monkeypatch.setattr("db.file_registry.check_file_exists", lambda *args: None)
    monkeypatch.setattr("db.file_registry.delete_file_by_source", cleanup)
    monkeypatch.setattr("infrastructure.repositories.input_store.get_input_store", lambda: MagicMock(store=MagicMock(return_value=(None, None, None))))
    monkeypatch.setattr("application.services.job_service.JobService.create_job", lambda self, **kwargs: SimpleNamespace(job_id="job-1"))
    monkeypatch.setattr("application.services.ingestion_service.IngestionJobRunner", lambda *_args, **_kwargs: SimpleNamespace(process_file_bytes=MagicMock()))
    monkeypatch.setattr("activity_store.activity_store.add_event", MagicMock())

    project = ProjectContext("project-a", "org-a", "Project A", "project-a", "OWNER", ("knowledge:write",))
    user = AuthenticatedUser("user-a", "org-a", "USER", "a@example.test")
    result = IngestionService().ingest_upload(BackgroundTasks(), b"new content", "notes.pdf", user, "groq", project)

    assert result["status"] == "success"
    cleanup.assert_called_once()
    assert cleanup.call_args.args[1:] == ("project-a", "org-a")
