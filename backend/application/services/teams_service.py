import base64
import hashlib
import hmac
import json
import logging
import time

from application.services.auth_service import AuthenticatedUser
from application.services.project_service import ProjectContext
from core.config import settings
from db.neo import _driver
from domain.exceptions import ConflictError, IngestionError, ValidationError
from integrations.microsoft_teams import MicrosoftTeamsAdapter
from integrations.base import KnowledgeDocument
from security.token_cipher import decrypt, encrypt

logger = logging.getLogger(__name__)


class TeamsService:
    def __init__(self):
        self.adapter = MicrosoftTeamsAdapter()

    def _state(self, project: ProjectContext, user: AuthenticatedUser) -> str:
        payload = json.dumps({"project_id": project.project_id, "organization_id": project.organization_id, "user_id": user.user_id, "exp": int(time.time()) + 600}, separators=(",", ":")).encode()
        encoded = base64.urlsafe_b64encode(payload).decode().rstrip("=")
        signature = hmac.new(settings.teams_token_encryption_key.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        return f"{encoded}.{signature}"

    def _read_state(self, value: str) -> dict:
        try:
            encoded, signature = value.split(".", 1)
        except ValueError as exc:
            raise ValidationError("Invalid Teams OAuth state") from exc
        expected = hmac.new(settings.teams_token_encryption_key.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected): raise ValidationError("Invalid Teams OAuth state")
        try:
            payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValidationError("Invalid Teams OAuth state") from exc
        if payload["exp"] < time.time(): raise ValidationError("Teams OAuth state expired")
        return payload

    def connect_url(self, project: ProjectContext, user: AuthenticatedUser) -> str:
        if not settings.microsoft_client_id or not settings.microsoft_client_secret or not settings.microsoft_redirect_uri or not settings.frontend_url:
            raise ConflictError("Microsoft OAuth is not fully configured")
        if not settings.teams_token_encryption_key or settings.teams_token_encryption_key == "change-me-in-production":
            raise ConflictError("TEAMS_TOKEN_ENCRYPTION_KEY is not configured")
        return self.adapter.authorization_url(self._state(project, user))

    def complete_oauth(self, code: str, state: str) -> dict:
        state_data = self._read_state(state)
        tokens = self.adapter.exchange_code(code)
        if not tokens.get("access_token") or not tokens.get("refresh_token"):
            raise ValidationError("Microsoft OAuth did not return the required tokens")
        profile = self.adapter.me(tokens["access_token"])
        subscription_id = None
        subscription_expires_at = None
        try:
            subscription = self.adapter.create_subscription(tokens["access_token"], profile.get("id", ""))
            subscription_id = subscription.get("id") if subscription else None
            subscription_expires_at = int(time.time()) + 172800 if subscription_id else None
        except Exception:
            # Connection still works through manual sync when Graph subscriptions
            # are unavailable (for example on a local, non-public callback URL).
            subscription_id = None
        now = int(time.time())
        with _driver.session() as session:
            session.run("""
                MERGE (p:Project {id: $project_id})
                MERGE (c:TeamsConnection {project_id: $project_id})
                SET c.organization_id=$organization_id, c.user_id=$user_id, c.email=$email,
                    c.access_token=$access_token, c.refresh_token=$refresh_token,
                    c.expires_at=$expires_at, c.subscription_id=$subscription_id, c.subscription_expires_at=$subscription_expires_at, c.updated_at=$updated_at, c.status='connected'
                MERGE (c)-[:BELONGS_TO]->(p)
            """, project_id=state_data["project_id"], organization_id=state_data["organization_id"], user_id=state_data["user_id"], email=profile.get("mail") or profile.get("userPrincipalName", ""), access_token=encrypt(tokens["access_token"]), refresh_token=encrypt(tokens.get("refresh_token", "")), expires_at=now + int(tokens.get("expires_in", 3600)), subscription_id=subscription_id, subscription_expires_at=subscription_expires_at, updated_at=now)
        return state_data

    def _connection(self, project_id: str) -> dict | None:
        with _driver.session() as session:
            record = session.run("MATCH (c:TeamsConnection {project_id: $project_id}) RETURN c", project_id=project_id).single()
            return record["c"].data() if record else None

    def _access_token(self, project_id: str) -> str:
        connection = self._connection(project_id)
        if not connection: raise ValidationError("Microsoft Teams is not connected to this project")
        if int(connection.get("expires_at", 0)) <= int(time.time()) + 60:
            try:
                tokens = self.adapter.refresh_token(decrypt(connection["refresh_token"]))
            except Exception:
                with _driver.session() as session:
                    session.run("MATCH (c:TeamsConnection {project_id: $project_id}) SET c.status='reauthorization_required', c.updated_at=$updated_at", project_id=project_id, updated_at=int(time.time()))
                raise ValidationError("Teams authorization expired. Disconnect and reconnect Teams.")
            with _driver.session() as session:
                session.run("MATCH (c:TeamsConnection {project_id: $project_id}) SET c.access_token=$access_token, c.refresh_token=$refresh_token, c.expires_at=$expires_at, c.updated_at=$updated_at", project_id=project_id, access_token=encrypt(tokens["access_token"]), refresh_token=encrypt(tokens.get("refresh_token") or decrypt(connection["refresh_token"])), expires_at=int(time.time()) + int(tokens.get("expires_in", 3600)), updated_at=int(time.time()))
            return tokens["access_token"]
        return decrypt(connection["access_token"])

    def status(self, project: ProjectContext) -> dict:
        connection = self._connection(project.project_id)
        return {"connected": bool(connection) and connection.get("status") == "connected", "provider": "microsoft_teams", "status": connection.get("status") if connection else "disconnected", "email": connection.get("email") if connection else None, "updated_at": connection.get("updated_at") if connection else None, "subscription_configured": bool(connection and connection.get("subscription_id")), "mock_transcripts_enabled": settings.mock_teams_transcripts}

    def disconnect(self, project: ProjectContext) -> dict:
        connection = self._connection(project.project_id)
        if connection and connection.get("subscription_id"):
            try:
                self.adapter.delete_subscription(self._access_token(project.project_id), connection["subscription_id"])
            except Exception as exc:
                logger.warning("Could not delete Teams subscription during disconnect: %s", exc)
        with _driver.session() as session:
            session.run("MATCH (c:TeamsConnection {project_id: $project_id}) DETACH DELETE c", project_id=project.project_id)
        return {"connected": False}

    def sync(self, project: ProjectContext, user: AuthenticatedUser, provider: str = "groq") -> dict:
        try:
            access_token = self._access_token(project.project_id)
            documents = self.adapter.list_documents(access_token)
            imported = []
            mocked_count = 0
            permission_required = False
            from ingestion.pipeline import run_meeting_ingestion_from_text
            for document in documents:
                try:
                    full = self.adapter.fetch_document(access_token, document)
                except Exception as exc:
                    status_code = getattr(exc, "status_code", None)
                    if status_code not in {401, 403}:
                        raise
                    permission_required = True
                    full = KnowledgeDocument(document.external_id, document.title, "", document.source, {**document.metadata, "transcript_error": status_code})
                transcript_hash = hashlib.sha256(full.text.encode("utf-8")).hexdigest() if full.text.strip() else None
                with _driver.session() as session:
                    existing = session.run("MATCH (m:Meeting {id: $id, project_id: $project_id}) RETURN m.transcript_hash as transcript_hash", id=full.external_id, project_id=project.project_id).single()
                if transcript_hash and existing and existing.get("transcript_hash") == transcript_hash:
                    continue
                if full.metadata.get("mocked"):
                    mocked_count += 1
                with _driver.session() as session:
                    session.run("""
                        MERGE (m:Meeting {id: $id, project_id: $project_id})
                        SET m.title=$title, m.source=$source, m.start=$start, m.end=$end, m.join_url=$join_url, m.transcript=$transcript, m.transcript_hash=$transcript_hash, m.project_id=$project_id, m.organization_id=$organization_id, m.synced_at=$synced_at
                    """, id=full.external_id, project_id=project.project_id, title=full.title, source=full.source, start=full.metadata.get("start"), end=full.metadata.get("end"), join_url=full.metadata.get("join_url"), transcript=full.text, transcript_hash=transcript_hash, organization_id=project.organization_id, synced_at=int(time.time()))
                if full.text.strip():
                    result = run_meeting_ingestion_from_text(full.text, full.source, full.external_id, provider, project.project_id, project.organization_id, full.metadata)
                    imported.append({"id": full.external_id, "title": full.title, "result": result})
                    from activity_store import activity_store
                    activity_store.add_event("teams", f"Teams meeting ingested: {full.title}", "Transcript and structured knowledge processed", full.source, user.user_id, project.project_id)
            result = {"status": "partial" if permission_required else "success", "meetings": imported, "count": len(imported), "mocked_count": mocked_count, "transcript_access": "requires_admin_consent" if permission_required else ("mock" if mocked_count else "available")}
            if permission_required:
                result["message"] = "Transcript access requires Microsoft Entra administrator consent."
            return result
        except Exception as exc:
            raise IngestionError(f"Teams sync could not be completed: {exc}") from exc

    def renew_subscriptions(self) -> int:
        renewed = 0
        with _driver.session() as session:
            connections = [record["c"].data() for record in session.run("MATCH (c:TeamsConnection {status: 'connected'}) WHERE c.subscription_id IS NOT NULL RETURN c")]
        for connection in connections:
            if not connection.get("expires_at") or int(connection.get("subscription_expires_at", 0)) > int(time.time()) + 86400:
                continue
            try:
                expiration = self.adapter.renew_subscription(self._access_token(connection["project_id"]), connection["subscription_id"])
                with _driver.session() as session:
                    session.run("MATCH (c:TeamsConnection {project_id: $project_id}) SET c.subscription_expires_at=$expires_at, c.updated_at=$updated_at", project_id=connection["project_id"], expires_at=int(time.time()) + 172800, updated_at=int(time.time()))
                renewed += 1
            except Exception as exc:
                logger.warning("Could not renew Teams subscription for project %s: %s", connection.get("project_id"), exc)
        return renewed

    def meetings(self, project: ProjectContext) -> list[dict]:
        with _driver.session() as session:
            return [record.data() for record in session.run("MATCH (m:Meeting {project_id: $project_id}) RETURN m.id as id, m.title as title, m.source as source, m.start as start, m.end as end, m.synced_at as synced_at ORDER BY m.start DESC", project_id=project.project_id)]

    def sync_subscription(self, subscription_id: str) -> dict | None:
        with _driver.session() as session:
            record = session.run("MATCH (c:TeamsConnection {subscription_id: $subscription_id}) RETURN c", subscription_id=subscription_id).single()
        if not record:
            return None
        connection = record["c"].data()
        project = ProjectContext(connection["project_id"], connection.get("organization_id", "default"), "Teams project", "", "OWNER", ("knowledge:write",))
        user = AuthenticatedUser(connection.get("user_id", "teams-webhook"), connection.get("organization_id", "default"), "OWNER", connection.get("email", ""))
        return self.sync(project, user)

    def meeting(self, project: ProjectContext, meeting_id: str) -> dict:
        with _driver.session() as session:
            record = session.run("MATCH (m:Meeting {id: $meeting_id, project_id: $project_id}) OPTIONAL MATCH (m)-[:HAS_KNOWLEDGE]->(k:MeetingKnowledge) OPTIONAL MATCH (k)-[:INVOLVES]->(p:Person) RETURN m, collect(DISTINCT k) as knowledge, collect(DISTINCT p.name) as participants", meeting_id=meeting_id, project_id=project.project_id).single()
        if not record: raise ValidationError("Meeting not found")
        meeting = record["m"].data(); meeting["knowledge"] = [item.data() for item in record["knowledge"] if item]; meeting["participants"] = [p for p in record["participants"] if p]
        meeting.pop("transcript", None)
        return meeting
