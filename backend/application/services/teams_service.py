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

    @staticmethod
    def frontend_url() -> str:
        configured = settings.frontend_url.strip()
        if configured:
            return configured.rstrip("/")
        return next((origin.strip().rstrip("/") for origin in settings.cors_origins.split(",") if origin.strip()), "")

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
        missing = [
            name for name, value in (
                ("MICROSOFT_CLIENT_ID", settings.microsoft_client_id),
                ("MICROSOFT_CLIENT_SECRET", settings.microsoft_client_secret),
                ("MICROSOFT_REDIRECT_URI", settings.microsoft_redirect_uri),
                ("FRONTEND_URL or CORS_ORIGINS", TeamsService.frontend_url()),
            ) if not value
        ]
        if missing:
            raise ConflictError(f"Microsoft OAuth is not fully configured. Missing: {', '.join(missing)}")
        if (settings.graph_webhook_url or settings.teams_webhook_url) and not settings.teams_webhook_client_state.strip():
            raise ConflictError("TEAMS_WEBHOOK_CLIENT_STATE is required when Teams notifications are enabled")
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
                MERGE (p:Project {id: $project_id, organization_id: $organization_id})
                MERGE (c:TeamsConnection {project_id: $project_id, organization_id: $organization_id})
                SET c.user_id=$user_id, c.email=$email,
                    c.access_token=$access_token, c.refresh_token=$refresh_token,
                    c.expires_at=$expires_at, c.subscription_id=$subscription_id, c.subscription_expires_at=$subscription_expires_at, c.updated_at=$updated_at, c.status='connected'
                MERGE (c)-[:BELONGS_TO]->(p)
            """, project_id=state_data["project_id"], organization_id=state_data["organization_id"], user_id=state_data["user_id"], email=profile.get("mail") or profile.get("userPrincipalName", ""), access_token=encrypt(tokens["access_token"]), refresh_token=encrypt(tokens.get("refresh_token", "")), expires_at=now + int(tokens.get("expires_in", 3600)), subscription_id=subscription_id, subscription_expires_at=subscription_expires_at, updated_at=now)
        return state_data

    def _connection(self, project_id: str, organization_id: str) -> dict | None:
        with _driver.session() as session:
            record = session.run("MATCH (c:TeamsConnection {project_id: $project_id, organization_id: $organization_id}) RETURN c", project_id=project_id, organization_id=organization_id).single()
            return record["c"].data() if record else None

    def _access_token(self, project_id: str, organization_id: str) -> str:
        connection = self._connection(project_id, organization_id)
        if not connection: raise ValidationError("Microsoft Teams is not connected to this project")
        if int(connection.get("expires_at", 0)) <= int(time.time()) + 60:
            try:
                tokens = self.adapter.refresh_token(decrypt(connection["refresh_token"]))
            except Exception:
                with _driver.session() as session:
                    session.run("MATCH (c:TeamsConnection {project_id: $project_id, organization_id: $organization_id}) SET c.status='reauthorization_required', c.updated_at=$updated_at", project_id=project_id, organization_id=organization_id, updated_at=int(time.time()))
                raise ValidationError("Teams authorization expired. Disconnect and reconnect Teams.")
            with _driver.session() as session:
                session.run("MATCH (c:TeamsConnection {project_id: $project_id, organization_id: $organization_id}) SET c.access_token=$access_token, c.refresh_token=$refresh_token, c.expires_at=$expires_at, c.updated_at=$updated_at", project_id=project_id, organization_id=organization_id, access_token=encrypt(tokens["access_token"]), refresh_token=encrypt(tokens.get("refresh_token") or decrypt(connection["refresh_token"])), expires_at=int(time.time()) + int(tokens.get("expires_in", 3600)), updated_at=int(time.time()))
            return tokens["access_token"]
        return decrypt(connection["access_token"])

    def status(self, project: ProjectContext) -> dict:
        connection = self._connection(project.project_id, project.organization_id)
        return {"connected": bool(connection) and connection.get("status") == "connected", "provider": "microsoft_teams", "status": connection.get("status") if connection else "disconnected", "email": connection.get("email") if connection else None, "updated_at": connection.get("updated_at") if connection else None, "subscription_configured": bool(connection and connection.get("subscription_id")), "mock_transcripts_enabled": settings.mock_teams_transcripts}

    def disconnect(self, project: ProjectContext) -> dict:
        connection = self._connection(project.project_id, project.organization_id)
        if connection and connection.get("subscription_id"):
            try:
                self.adapter.delete_subscription(self._access_token(project.project_id, project.organization_id), connection["subscription_id"])
            except Exception as exc:
                logger.warning("Could not delete Teams subscription during disconnect: %s", exc)
        with _driver.session() as session:
            session.run("MATCH (c:TeamsConnection {project_id: $project_id, organization_id: $organization_id}) DETACH DELETE c", project_id=project.project_id, organization_id=project.organization_id)
        return {"connected": False}

    def sync(self, project: ProjectContext, user: AuthenticatedUser, background_tasks=None, provider: str = "groq") -> dict:
        try:
            # Basic validation
            access_token = self._access_token(project.project_id, project.organization_id)
            
            from application.services.job_service import JobService
            job = JobService().create_job(
                organization_id=project.organization_id,
                project_id=project.project_id,
                user_id=user.user_id,
                source_type="teams_sync",
                source_id="microsoft_teams",
                source_config={"provider": provider},
            )
            
            if background_tasks:
                from ingestion.teams import TeamsSyncRunner
                runner = TeamsSyncRunner(job.job_id, JobService(), project.organization_id)
                background_tasks.add_task(runner.process_teams_sync, project_id=project.project_id, organization_id=project.organization_id, user_id=user.user_id, provider=provider)
                return {"status": "success", "job_id": job.job_id}
            else:
                return {"status": "error", "message": "Background tasks missing"}
        except Exception as exc:
            raise IngestionError(f"Teams sync could not be started: {exc}") from exc

    def renew_subscriptions(self) -> int:
        renewed = 0
        with _driver.session() as session:
            connections = [record["c"].data() for record in session.run("MATCH (c:TeamsConnection {status: 'connected'}) WHERE c.subscription_id IS NOT NULL RETURN c")]
        for connection in connections:
            if not connection.get("expires_at") or int(connection.get("subscription_expires_at", 0)) > int(time.time()) + 86400:
                continue
            try:
                expiration = self.adapter.renew_subscription(self._access_token(connection["project_id"], connection.get("organization_id", "default")), connection["subscription_id"])
                with _driver.session() as session:
                    session.run("MATCH (c:TeamsConnection {project_id: $project_id, organization_id: $organization_id}) SET c.subscription_expires_at=$expires_at, c.updated_at=$updated_at", project_id=connection["project_id"], organization_id=connection.get("organization_id", "default"), expires_at=int(time.time()) + 172800, updated_at=int(time.time()))
                renewed += 1
            except Exception as exc:
                logger.warning("Could not renew Teams subscription for project %s: %s", connection.get("project_id"), exc)
        return renewed

    def meetings(self, project: ProjectContext) -> list[dict]:
        with _driver.session() as session:
            return [record.data() for record in session.run("MATCH (m:Meeting {project_id: $project_id, organization_id: $organization_id}) RETURN m.id as id, m.title as title, m.source as source, m.start as start, m.end as end, m.synced_at as synced_at ORDER BY m.start DESC", project_id=project.project_id, organization_id=project.organization_id)]

    def sync_subscription(self, subscription_id: str, background_tasks=None) -> dict | None:
        with _driver.session() as session:
            record = session.run("MATCH (c:TeamsConnection {subscription_id: $subscription_id}) RETURN c", subscription_id=subscription_id).single()
        if not record:
            return None
        connection = record["c"].data()
        if not connection.get("organization_id"):
            logger.error(f"Subscription {subscription_id} belongs to a connection missing organization_id")
            return None
        project = ProjectContext(connection["project_id"], connection.get("organization_id"), "Teams project", "", "OWNER", ("knowledge:write",))
        user = AuthenticatedUser(connection.get("user_id", "teams-webhook"), connection.get("organization_id"), "OWNER", connection.get("email", ""))
        return self.sync(project, user, background_tasks=background_tasks)

    def meeting(self, project: ProjectContext, meeting_id: str) -> dict:
        with _driver.session() as session:
            record = session.run("MATCH (m:Meeting {id: $meeting_id, project_id: $project_id, organization_id: $organization_id}) OPTIONAL MATCH (m)-[:HAS_KNOWLEDGE]->(k:MeetingKnowledge) OPTIONAL MATCH (k)-[:INVOLVES]->(p:Person) RETURN m, collect(DISTINCT k) as knowledge, collect(DISTINCT p.name) as participants", meeting_id=meeting_id, project_id=project.project_id, organization_id=project.organization_id).single()
        if not record: raise ValidationError("Meeting not found")
        meeting = record["m"].data(); meeting["knowledge"] = [item.data() for item in record["knowledge"] if item]; meeting["participants"] = [p for p in record["participants"] if p]
        meeting.pop("transcript", None)
        return meeting
