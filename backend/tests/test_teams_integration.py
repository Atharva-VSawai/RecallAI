import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, ".")

from fastapi.testclient import TestClient

from api.routes.teams_routes import router
from core.config import settings
from integrations.base import KnowledgeDocument
from integrations.microsoft_teams import MicrosoftTeamsAdapter, SCOPES, TeamsGraphError
from ingestion.pipeline import MeetingExtractionResult, MeetingKnowledgeItem, run_meeting_ingestion_from_text
from application.services.auth_service import AuthenticatedUser
from application.services.project_service import ProjectContext
from application.services.teams_service import TeamsService
from main import app
from security.token_cipher import decrypt, encrypt


def test_teams_tokens_are_authenticated_encrypted():
    token = "access-token-value"
    encoded = encrypt(token)
    assert encoded != token
    assert decrypt(encoded) == token


def test_teams_oauth_scopes_include_calendar_and_transcripts():
    assert "Calendars.Read" in SCOPES
    assert "OnlineMeetings.Read" in SCOPES
    assert "OnlineMeetingTranscript.Read.All" in SCOPES
    assert "offline_access" in SCOPES


def test_mock_mode_avoids_unconsented_transcript_scope(monkeypatch):
    adapter = MicrosoftTeamsAdapter()
    monkeypatch.setattr(settings, "mock_teams_transcripts", True)
    assert "OnlineMeetingTranscript.Read.All" not in adapter.requested_scopes()
    monkeypatch.setattr(settings, "mock_teams_transcripts", False)
    assert "OnlineMeetingTranscript.Read.All" in adapter.requested_scopes()


def test_refresh_token_flow_uses_refresh_grant():
    response = SimpleNamespace(status_code=200, text="", json=lambda: {"access_token": "new-access", "expires_in": 3600})
    with patch("integrations.microsoft_teams.httpx.post", return_value=response) as request:
        result = MicrosoftTeamsAdapter().refresh_token("refresh-token")
    assert result["access_token"] == "new-access"
    assert request.call_args.kwargs["data"]["grant_type"] == "refresh_token"


def test_subscription_payload_targets_user_transcripts(monkeypatch):
    monkeypatch.setattr(settings, "graph_webhook_url", "https://api.example.com/integrations/teams/notifications")
    response = SimpleNamespace(status_code=201, text="", json=lambda: {"id": "subscription-1"})
    with patch("integrations.microsoft_teams.httpx.post", return_value=response) as request:
        result = MicrosoftTeamsAdapter().create_subscription("access-token", "user-1")
    assert result["id"] == "subscription-1"
    payload = request.call_args.kwargs["json"]
    assert payload["changeType"] == "created"
    assert payload["resource"] == "users/user-1/onlineMeetings/getAllTranscripts"


def test_graph_validation_handshake_returns_plain_text():
    response = TestClient(app).post("/integrations/teams/notifications?validationToken=validation-value")
    assert response.status_code == 200
    assert response.text == "validation-value"
    assert response.headers["content-type"].startswith("text/plain")


def test_teams_notifications_require_explicit_client_state(monkeypatch):
    monkeypatch.setattr(settings, "teams_webhook_client_state", "")
    response = TestClient(app).post("/integrations/teams/notifications", json={"value": [{"subscriptionId": "untrusted"}]})
    assert response.status_code == 400


def test_teams_notifications_ignore_wrong_client_state(monkeypatch):
    monkeypatch.setattr(settings, "teams_webhook_client_state", "expected-state")
    with patch.object(TeamsService, "sync_subscription") as sync:
        response = TestClient(app).post(
            "/integrations/teams/notifications",
            json={"value": [{"subscriptionId": "subscription-1", "clientState": "wrong-state"}]},
        )
    assert response.status_code == 200
    assert response.json()["received"] == 1
    sync.assert_not_called()


def test_transcript_permission_falls_back_to_graph_shaped_mock(monkeypatch):
    monkeypatch.setattr(settings, "mock_teams_transcripts", True)
    adapter = MicrosoftTeamsAdapter()
    document = KnowledgeDocument("meeting-1", "Mock meeting", "", "teams:meeting-1", {})
    with patch.object(adapter, "_request_collection", side_effect=TeamsGraphError("forbidden", 403)):
        result = adapter.fetch_document("access-token", document)
    assert result.metadata["mocked"] is True
    assert result.metadata["transcript_response"]["value"][0]["meetingId"] == "meeting-1"
    assert "Alex" in result.text


def test_mock_transcript_runs_through_shared_ingestion_stages(monkeypatch):
    from langchain_core.runnables import RunnableLambda

    class FakeLLM:
        def with_structured_output(self, _model):
            return RunnableLambda(lambda _payload: MeetingExtractionResult(items=[MeetingKnowledgeItem(category="decision", title="Ship reporting API", details="Ship next Friday", people=["Alex"])]))

    stored = []
    monkeypatch.setattr("ingestion.pipeline.get_llm", lambda _provider: FakeLLM())
    with patch("db.chroma.chroma_store") as vectors, patch("db.neo.neo_store_meeting_knowledge", side_effect=lambda **item: stored.append(item)):
        result = run_meeting_ingestion_from_text("WEBVTT\\n\\nAlex: Ship the reporting API next Friday.", "teams:mock", "mock-meeting", project_id="project-1", organization_id="org-1")
    vectors.assert_called_once()
    assert result["ingested"] == 1
    assert stored[0]["project_id"] == "project-1"


def test_sync_starts_background_job_and_returns_job_id(monkeypatch):
    class FakeResult:
        def single(self):
            return None

    class FakeSession:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def run(self, *_args, **_kwargs): return FakeResult()

    class FakeDriver:
        def session(self): return FakeSession()

    from fastapi import BackgroundTasks
    bg = BackgroundTasks()

    project = ProjectContext("project-1", "org-1", "Project", "project", "OWNER", ("knowledge:write",))
    user = AuthenticatedUser("user-1", "org-1", "OWNER", "user@example.com")
    service = TeamsService()
    monkeypatch.setattr("application.services.teams_service._driver", FakeDriver())
    monkeypatch.setattr(service, "_access_token", lambda _project_id, _organization_id: "access-token")
    monkeypatch.setattr("application.services.job_service.JobService.create_job", lambda self, **_kwargs: SimpleNamespace(job_id="job-1"))
    monkeypatch.setattr("ingestion.teams.TeamsSyncRunner", MagicMock())
    result = service.sync(project, user, background_tasks=bg)
    assert result["status"] == "success"
    assert "job_id" in result


def test_frontend_url_falls_back_to_cors_origin(monkeypatch):
    monkeypatch.setattr(settings, "frontend_url", "")
    monkeypatch.setattr(settings, "cors_origins", "https://recall-ai-86lp-omega.vercel.app")
    assert TeamsService.frontend_url() == "https://recall-ai-86lp-omega.vercel.app"
