"""Microsoft Graph adapter. No Graph credentials are exposed to the browser."""
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode

import httpx

from core.config import settings
from integrations.base import KnowledgeDocument


GRAPH = "https://graph.microsoft.com/v1.0"
BASE_SCOPES = ["openid", "profile", "email", "offline_access", "User.Read", "Calendars.Read", "OnlineMeetings.Read"]
TRANSCRIPT_SCOPE = "OnlineMeetingTranscript.Read.All"
SCOPES = [*BASE_SCOPES, TRANSCRIPT_SCOPE]


class TeamsGraphError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class MicrosoftTeamsAdapter:
    provider = "microsoft_teams"

    @staticmethod
    def requested_scopes() -> list[str]:
        return BASE_SCOPES if settings.mock_teams_transcripts else SCOPES

    def authorization_url(self, state: str) -> str:
        if not settings.microsoft_redirect_uri:
            raise TeamsGraphError("MICROSOFT_REDIRECT_URI is not configured")
        params = {
            "client_id": settings.microsoft_client_id,
            "response_type": "code",
            "redirect_uri": settings.microsoft_redirect_uri,
            "response_mode": "query",
            "scope": " ".join(self.requested_scopes()),
            "state": state,
        }
        return f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/oauth2/v2.0/authorize?{urlencode(params)}"

    def _token_request(self, data: dict) -> dict:
        response = httpx.post(
            f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/oauth2/v2.0/token",
            data={"client_id": settings.microsoft_client_id, "client_secret": settings.microsoft_client_secret, **data},
            timeout=30,
        )
        if response.status_code >= 400:
            raise TeamsGraphError(f"Microsoft OAuth failed: {response.text[:300]}", response.status_code)
        return response.json()

    def exchange_code(self, code: str) -> dict:
        return self._token_request({"grant_type": "authorization_code", "code": code, "redirect_uri": settings.microsoft_redirect_uri, "scope": " ".join(self.requested_scopes())})

    def refresh_token(self, refresh_token: str) -> dict:
        return self._token_request({"grant_type": "refresh_token", "refresh_token": refresh_token, "scope": " ".join(self.requested_scopes())})

    def me(self, access_token: str) -> dict:
        return self._request("/me", access_token)

    def list_documents(self, access_token: str) -> list[KnowledgeDocument]:
        """Discover calendar-backed Teams meetings, then resolve Graph meeting IDs.

        Graph exposes onlineMeeting GET/filter operations, not a general list
        endpoint. CalendarView is therefore the reliable discovery source.
        """
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=90)).isoformat().replace("+00:00", "Z")
        end = (now + timedelta(days=30)).isoformat().replace("+00:00", "Z")
        path = f"/me/calendarView?startDateTime={quote(start)}&endDateTime={quote(end)}&$top=100&$select=id,subject,start,end,onlineMeeting,onlineMeetingProvider"
        events = self._request_collection(path, access_token)
        documents = []
        seen = set()
        for event in events:
            online = event.get("onlineMeeting") or {}
            join_url = online.get("joinUrl")
            if not join_url or event.get("onlineMeetingProvider") in {None, "unknown"}:
                continue
            filter_value = join_url.replace("'", "''")
            filter_query = quote(f"JoinWebUrl eq '{filter_value}'", safe="")
            meetings = self._request_collection(f"/me/onlineMeetings?$filter={filter_query}", access_token)
            if not meetings:
                continue
            meeting = meetings[0]
            if meeting.get("id") in seen:
                continue
            seen.add(meeting.get("id"))
            documents.append(KnowledgeDocument(
                external_id=meeting["id"], title=event.get("subject") or meeting.get("subject") or "Teams meeting", text="", source=f"teams:{meeting['id']}",
                metadata={"join_url": join_url, "start": (event.get("start") or {}).get("dateTime"), "end": (event.get("end") or {}).get("dateTime"), "event_id": event.get("id")},
            ))
        if not documents and settings.mock_teams_transcripts:
            documents.append(KnowledgeDocument(
                external_id="mock-teams-meeting", title="Recall.AI Mock Teams Meeting", text="", source="teams:mock-teams-meeting",
                metadata={"start": now.isoformat(), "end": now.isoformat(), "mocked": True},
            ))
        return documents

    def fetch_document(self, access_token: str, document: KnowledgeDocument) -> KnowledgeDocument:
        try:
            transcripts = self._request_collection(f"/me/onlineMeetings/{quote(document.external_id, safe='')}/transcripts", access_token)
        except TeamsGraphError as exc:
            if settings.mock_teams_transcripts and exc.status_code in {401, 403}:
                return self._mock_document(document, f"Graph transcript request returned HTTP {exc.status_code}")
            raise
        parts = []
        transcript_ids = []
        for transcript in transcripts:
            transcript_ids.append(transcript.get("id"))
            content = self._request(f"/me/onlineMeetings/{quote(document.external_id, safe='')}/transcripts/{quote(transcript['id'], safe='')}/content?$format=text/vtt", access_token, accept="text/vtt")
            if isinstance(content, str):
                parts.append(content)
        if not parts and settings.mock_teams_transcripts:
            return self._mock_document(document, "Graph returned no transcript for this meeting")
        return KnowledgeDocument(document.external_id, document.title, "\n".join(parts), document.source, {**document.metadata, "transcript_ids": transcript_ids, "mocked": False})

    def _mock_document(self, document: KnowledgeDocument, reason: str) -> KnowledgeDocument:
        text = settings.mock_teams_transcript.replace("\\n", "\n")
        response = {
            "@odata.context": f"{GRAPH}/$metadata#users('mock')/onlineMeetings('{document.external_id}')/transcripts",
            "value": [{"id": "mock-transcript-1", "meetingId": document.external_id, "transcriptContentUrl": f"{GRAPH}/mock/transcripts/mock-transcript-1/content"}],
        }
        return KnowledgeDocument(document.external_id, document.title, text, document.source, {**document.metadata, "transcript_response": response, "mocked": True, "mock_reason": reason, "transcript_ids": ["mock-transcript-1"]})

    def create_subscription(self, access_token: str, user_id: str) -> dict | None:
        webhook_url = settings.graph_webhook_url or settings.teams_webhook_url
        if not webhook_url:
            return None
        response = httpx.post(f"{GRAPH}/subscriptions", headers={"Authorization": f"Bearer {access_token}"}, json={
            "changeType": "created", "notificationUrl": webhook_url,
            "resource": f"users/{user_id}/onlineMeetings/getAllTranscripts", "expirationDateTime": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat().replace("+00:00", "Z"),
            "lifecycleNotificationUrl": webhook_url,
            "clientState": settings.teams_webhook_client_state,
        }, timeout=30)
        if response.status_code >= 400:
            raise TeamsGraphError(f"Could not create Teams subscription: {response.text[:300]}")
        return response.json()

    def renew_subscription(self, access_token: str, subscription_id: str) -> str:
        expiration = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat().replace("+00:00", "Z")
        response = httpx.patch(f"{GRAPH}/subscriptions/{quote(subscription_id, safe='')}", headers={"Authorization": f"Bearer {access_token}"}, json={"expirationDateTime": expiration}, timeout=30)
        if response.status_code >= 400:
            raise TeamsGraphError(f"Could not renew Teams subscription: {response.text[:300]}")
        return expiration

    def delete_subscription(self, access_token: str, subscription_id: str) -> None:
        response = httpx.delete(f"{GRAPH}/subscriptions/{quote(subscription_id, safe='')}", headers={"Authorization": f"Bearer {access_token}"}, timeout=30)
        if response.status_code not in {204, 404} and response.status_code >= 400:
            raise TeamsGraphError(f"Could not delete Teams subscription: {response.text[:300]}")

    def _request_collection(self, path: str, access_token: str) -> list[dict]:
        values = []
        next_path = path
        while next_path:
            payload = self._request(next_path, access_token)
            values.extend(payload.get("value", []))
            next_url = payload.get("@odata.nextLink")
            next_path = next_url[len(GRAPH):] if next_url and next_url.startswith(GRAPH) else None
        return values

    def _request(self, path: str, access_token: str, accept: str = "application/json"):
        response = httpx.get(f"{GRAPH}{path}", headers={"Authorization": f"Bearer {access_token}", "Accept": accept}, timeout=30)
        if response.status_code >= 400:
            raise TeamsGraphError(f"Microsoft Graph failed ({response.status_code}): {response.text[:300]}", response.status_code)
        return response.text if accept != "application/json" else response.json()
