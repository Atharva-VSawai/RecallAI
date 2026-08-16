from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import re
import uuid

from application.services.auth_service import AuthenticatedUser
from core.config import settings
from db.neo import _driver
from domain.exceptions import AuthorizationError, ConflictError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)


PROJECT_ROLES = {"OWNER", "ADMIN", "MANAGER", "CONTRIBUTOR", "VIEWER"}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "OWNER": {"project:read", "project:manage", "knowledge:read", "knowledge:write", "knowledge:delete"},
    "ADMIN": {"project:read", "project:manage", "knowledge:read", "knowledge:write", "knowledge:delete"},
    "MANAGER": {"project:read", "knowledge:read", "knowledge:write", "knowledge:delete"},
    "CONTRIBUTOR": {"project:read", "knowledge:read", "knowledge:write"},
    "VIEWER": {"project:read", "knowledge:read"},
}

@dataclass(frozen=True)
class ProjectContext:
    project_id: str
    organization_id: str
    name: str
    slug: str
    role: str
    permissions: tuple[str, ...]

    def can(self, permission: str) -> bool:
        return permission in self.permissions


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or f"project-{uuid.uuid4().hex[:8]}"


class ProjectService:
    def list_projects(self, user: AuthenticatedUser) -> list[dict]:
        with _driver.session() as session:
            result = session.run(
                """
                MATCH (u:User {id: $user_id})-[m:MEMBER_OF]->(p:Project)
                WHERE p.organization_id = $organization_id AND coalesce(p.status, 'ACTIVE') = 'ACTIVE'
                WITH p, collect(m.role) as roles, min(p.created_at) as created_at
                RETURN p.id as id, p.name as name, p.slug as slug,
                       p.organization_id as organization_id,
                       CASE
                         WHEN 'OWNER' IN roles THEN 'OWNER'
                         WHEN 'ADMIN' IN roles THEN 'ADMIN'
                         WHEN 'MANAGER' IN roles THEN 'MANAGER'
                         WHEN 'CONTRIBUTOR' IN roles THEN 'CONTRIBUTOR'
                         ELSE 'VIEWER'
                       END as role,
                       created_at as created_at
                ORDER BY coalesce(p.created_at, '') ASC, p.name ASC
                """,
                user_id=user.user_id,
                organization_id=user.organization_id,
            )
            projects_by_key = {}
            for record in result:
                project_id = record["id"]
                project_key = f"{record['organization_id']}:{record['slug'] or project_id}"
                if not project_id or project_key in projects_by_key:
                    continue
                role = record["role"] or "VIEWER"
                projects_by_key[project_key] = {
                    "id": project_id,
                    "name": record["name"],
                    "slug": record["slug"],
                    "organization_id": record["organization_id"],
                    "role": role,
                    "permissions": sorted(ROLE_PERMISSIONS.get(role, set())),
                    "created_at": record["created_at"],
                }
            return list(projects_by_key.values())

    def get_project_context(self, user: AuthenticatedUser, project_id: str | None) -> ProjectContext:
        if not user.organization_id:
            raise AuthorizationError("Missing organization context")
        projects = self.list_projects(user)
        if not projects:
            # Bootstrap only when the authenticated user has no accessible
            # workspace. Existing projects are never replaced or duplicated.
            try:
                self.ensure_default_project(user)
            except ValidationError as exc:
                logger.warning("Could not bootstrap default workspace for user=%s: %s", user.user_id, type(exc).__name__)
                raise NotFoundError("Project not found or you do not have access to it") from exc
            projects = self.list_projects(user)
        if not projects:
            raise NotFoundError("Project not found or you do not have access to it")
        selected_id = project_id or projects[0]["id"]
        for project in projects:
            if project["id"] == selected_id:
                role = project["role"]
                return ProjectContext(
                    project_id=project["id"],
                    organization_id=project["organization_id"],
                    name=project["name"],
                    slug=project["slug"],
                    role=role,
                    permissions=tuple(project["permissions"]),
                )
        raise NotFoundError("Project not found or you do not have access to it")

    def require_permission(self, context: ProjectContext, permission: str) -> ProjectContext:
        if not context.can(permission):
            raise AuthorizationError("You do not have permission to perform this project action")
        return context

    def create_project(self, name: str, user: AuthenticatedUser) -> dict:
        name = name.strip()
        if not name:
            raise ValidationError("Project name cannot be blank")
        slug_base = _slugify(name)
        timestamp = _now()
        with _driver.session() as session:
            result = session.run(
                """
                MERGE (org:Organization {id: $organization_id})
                ON CREATE SET org.name = $organization_name, org.created_at = $timestamp
                MERGE (u:User {id: $user_id})
                SET u.email = $email
                MERGE (p:Project {organization_id: $organization_id, slug: $slug})
                ON CREATE SET p.id = $project_id,
                              p.name = $name,
                              p.status = 'ACTIVE',
                              p.created_at = $timestamp,
                              p.created_by = $user_id
                SET p.name = coalesce(p.name, $name),
                    p.status = coalesce(p.status, 'ACTIVE')
                WITH u, p
                OPTIONAL MATCH (u)-[existing:MEMBER_OF]->(p)
                WITH u, p, collect(existing) as memberships
                FOREACH (_ IN CASE WHEN size(memberships) = 0 THEN [1] ELSE [] END |
                    CREATE (u)-[:MEMBER_OF {role: 'OWNER', created_at: $timestamp}]->(p)
                )
                WITH p
                RETURN p.id as id, p.name as name, p.slug as slug,
                       p.organization_id as organization_id, 'OWNER' as role,
                       p.created_at as created_at
                """,
                organization_id=user.organization_id,
                organization_name="Workspace Organization",
                user_id=user.user_id,
                email=user.email,
                project_id=f"{slug_base}-{uuid.uuid4().hex[:8]}",
                name=name,
                slug=slug_base,
                timestamp=timestamp,
            )
            record = result.single()
            if not record:
                raise ValidationError("Project could not be created")
            self._deduplicate_user_project_memberships(session, user.user_id)
            return {
                "id": record["id"],
                "name": record["name"],
                "slug": record["slug"],
                "organization_id": record["organization_id"],
                "role": record["role"],
                "permissions": sorted(ROLE_PERMISSIONS["OWNER"]),
                "created_at": record["created_at"],
            }

    def delete_project(self, project_id: str, user: AuthenticatedUser) -> dict:
        if not user.organization_id:
            raise AuthorizationError("Missing organization context")
        organization_id = user.organization_id
        with _driver.session() as session:
            access = session.run(
                """
                MATCH (u:User {id: $user_id})-[m:MEMBER_OF]->(p:Project {id: $project_id})
                WHERE p.organization_id = $organization_id AND coalesce(p.status, 'ACTIVE') = 'ACTIVE'
                RETURN p.id as id, p.name as name, p.slug as slug, m.role as role
                """,
                user_id=user.user_id,
                project_id=project_id,
                organization_id=organization_id,
            ).single()
            if not access:
                raise NotFoundError("Project not found or you do not have access to it")
            role = access["role"] or "VIEWER"
            if "project:manage" not in ROLE_PERMISSIONS.get(role, set()):
                raise AuthorizationError("Only project owners or admins can delete a workspace")

            counts = session.run(
                """
                MATCH (n)
                WHERE n.project_id = $project_id
                  AND n.organization_id = $organization_id
                WITH collect(n) as nodes, count(n) as project_nodes
                MATCH (p:Project {id: $project_id, organization_id: $organization_id})
                WITH nodes, project_nodes, p
                DETACH DELETE p
                FOREACH (node IN nodes | DETACH DELETE node)
                RETURN project_nodes
                """,
                project_id=project_id,
                organization_id=organization_id,
            ).single()

        chroma_result = {"status": "skipped"}
        try:
            from db.chroma import chroma_delete_by_project
            chroma_result = chroma_delete_by_project(project_id, organization_id)
        except Exception as exc:
            logger.warning("Could not delete Chroma vectors for project %s: %s", project_id, exc)
            chroma_result = {"status": "error", "error": str(exc)}

        return {
            "deleted_project": project_id,
            "deleted_graph_nodes": counts["project_nodes"] if counts else 0,
            "chroma": chroma_result,
        }

    def update_project(self, project_id: str, name: str, user: AuthenticatedUser) -> dict:
        name = name.strip()
        if not name:
            raise ValidationError("Workspace name cannot be blank")
        with _driver.session() as session:
            result = session.run(
                """
                MATCH (u:User {id: $user_id})-[m:MEMBER_OF]->(p:Project {id: $project_id})
                WHERE p.organization_id = $organization_id AND coalesce(p.status, 'ACTIVE') = 'ACTIVE'
                WITH p, m
                WHERE m.role IN ['OWNER', 'ADMIN']
                SET p.name = $name
                RETURN p.id as id, p.name as name, p.slug as slug,
                       p.organization_id as organization_id,
                       CASE WHEN m.role = 'OWNER' THEN 'OWNER' ELSE 'ADMIN' END as role,
                       p.created_at as created_at
                """,
                user_id=user.user_id,
                project_id=project_id,
                organization_id=user.organization_id,
                name=name,
            ).single()
            if not result:
                raise AuthorizationError("Only workspace owners or admins can edit this workspace")
            role = result["role"] or "ADMIN"
            return {
                "id": result["id"], "name": result["name"], "slug": result["slug"],
                "organization_id": result["organization_id"], "role": role,
                "permissions": sorted(ROLE_PERMISSIONS[role]), "created_at": result["created_at"],
            }

    def ensure_default_project(self, user: AuthenticatedUser) -> dict:
        """Create the user's initial workspace exactly once.

        This is intentionally an explicit bootstrap operation. Normal project
        listing remains read-only and existing projects are preserved.
        """
        if not user.organization_id:
            raise AuthorizationError("Missing organization context")
        timestamp = _now()
        with _driver.session() as session:
            result = session.run(
                """
                MERGE (org:Organization {id: $organization_id})
                ON CREATE SET org.name = $organization_name, org.created_at = $timestamp
                MERGE (p:Project {organization_id: $organization_id, slug: 'main-workspace'})
                ON CREATE SET p.name = $project_name,
                              p.id = $project_id,
                              p.status = 'ACTIVE',
                              p.created_at = $timestamp,
                              p.created_by = $user_id
                SET p.status = coalesce(p.status, 'ACTIVE')
                MERGE (u:User {id: $user_id})
                SET u.email = $email,
                    u.organization_id = $organization_id
                MERGE (u)-[:MEMBER_OF_ORGANIZATION]->(org)
                WITH u, p
                OPTIONAL MATCH (u)-[existing:MEMBER_OF]->(p)
                WITH u, p, collect(existing) as memberships
                FOREACH (_ IN CASE WHEN size(memberships) = 0 THEN [1] ELSE [] END |
                    CREATE (u)-[:MEMBER_OF {role: 'OWNER', created_at: $timestamp}]->(p)
                )
                RETURN p.id as id, p.name as name, p.slug as slug,
                       p.organization_id as organization_id, 'OWNER' as role,
                       p.created_at as created_at
                """,
                organization_id=user.organization_id,
                organization_name="Workspace Organization",
                project_id=f"main-{uuid.uuid5(uuid.NAMESPACE_URL, user.organization_id).hex[:12]}",
                project_name="Main Workspace",
                user_id=user.user_id,
                email=user.email,
                timestamp=timestamp,
            )
            record = result.single()
            if not record:
                raise ValidationError("Default workspace could not be initialized")
            self._deduplicate_user_project_memberships(session, user.user_id)
            return {
                "id": record["id"], "name": record["name"], "slug": record["slug"],
                "organization_id": record["organization_id"], "role": record["role"],
                "permissions": sorted(ROLE_PERMISSIONS["OWNER"]), "created_at": record["created_at"],
            }

    def _deduplicate_user_project_memberships(self, session, user_id: str) -> None:
        session.run(
            """
            MATCH (u:User {id: $user_id})-[m:MEMBER_OF]->(p:Project)
            WITH u, p, collect(m) as memberships
            WHERE size(memberships) > 1
            FOREACH (membership IN tail(memberships) | DELETE membership)
            """,
            user_id=user_id,
        ).consume()
