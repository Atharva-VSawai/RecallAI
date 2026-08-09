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

DEFAULT_ORGANIZATION_ID = "default"
DEFAULT_PROJECT_ID = "main-workspace"

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
        self.ensure_default_project(user)
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
                organization_id=user.organization_id or DEFAULT_ORGANIZATION_ID,
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
        projects = self.list_projects(user)
        selected_id = project_id or (projects[0]["id"] if projects else DEFAULT_PROJECT_ID)
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
                organization_id=user.organization_id or DEFAULT_ORGANIZATION_ID,
                organization_name="Default Organization",
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
        if project_id == DEFAULT_PROJECT_ID:
            raise ConflictError("The default workspace cannot be deleted")

        organization_id = user.organization_id or DEFAULT_ORGANIZATION_ID
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
                WITH collect(n) as nodes, count(n) as project_nodes
                MATCH (p:Project {id: $project_id})
                WITH nodes, project_nodes, p
                DETACH DELETE p
                FOREACH (node IN nodes | DETACH DELETE node)
                RETURN project_nodes
                """,
                project_id=project_id,
            ).single()

        chroma_result = {"status": "skipped"}
        try:
            from db.chroma import chroma_delete_by_project
            chroma_result = chroma_delete_by_project(project_id)
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
                organization_id=user.organization_id or DEFAULT_ORGANIZATION_ID,
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

    def ensure_default_project(self, user: AuthenticatedUser) -> None:
        timestamp = _now()
        with _driver.session() as session:
            self._ensure_constraints(session)
            self._migrate_single_member_legacy_projects(session, user)
            session.run(
                """
                MERGE (org:Organization {id: $organization_id})
                ON CREATE SET org.name = $organization_name, org.created_at = $timestamp
                MERGE (p:Project {organization_id: $organization_id, slug: $project_id})
                ON CREATE SET p.name = $project_name,
                              p.id = $project_id,
                              p.status = 'ACTIVE',
                              p.created_at = $timestamp,
                              p.created_by = 'system'
                SET p.id = coalesce(p.id, $project_id),
                    p.name = coalesce(p.name, $project_name),
                    p.status = coalesce(p.status, 'ACTIVE')
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
                """,
                organization_id=user.organization_id or DEFAULT_ORGANIZATION_ID,
                organization_name="Workspace Organization",
                project_id=DEFAULT_PROJECT_ID,
                project_name="Main Workspace",
                user_id=user.user_id,
                email=user.email,
                timestamp=timestamp,
            )
            self._deduplicate_default_project_nodes(session, user.organization_id or DEFAULT_ORGANIZATION_ID)
            self._deduplicate_user_project_memberships(session, user.user_id)

    def _migrate_single_member_legacy_projects(self, session, user: AuthenticatedUser) -> None:
        """Safely move legacy development data out of the shared `default` org.

        Legacy projects with multiple users are intentionally left untouched:
        ownership cannot be inferred safely, so moving or cloning them would
        risk a new cross-organization disclosure.  A one-member project is
        unambiguous; its graph/file data is migrated immediately after the
        project record.
        """
        organization_id = user.organization_id or DEFAULT_ORGANIZATION_ID
        if organization_id == DEFAULT_ORGANIZATION_ID:
            return
        with session.begin_transaction() as transaction:
            result = transaction.run(
                """
                MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(p:Project {organization_id: $legacy_organization_id})
                CALL {
                    WITH p
                    MATCH (:User)-[membership:MEMBER_OF]->(p)
                    RETURN count(membership) AS member_count
                }
                WITH p, member_count
                WHERE member_count = 1
                SET p.organization_id = $organization_id
                RETURN collect(p.id) AS project_ids
                """,
                user_id=user.user_id,
                organization_id=organization_id,
                legacy_organization_id=DEFAULT_ORGANIZATION_ID,
            ).single()
            project_ids = result["project_ids"] if result else []
            if project_ids:
                transaction.run(
                    """
                    MATCH (n)
                    WHERE n.project_id IN $project_ids
                      AND coalesce(n.organization_id, $legacy_organization_id) = $legacy_organization_id
                    SET n.organization_id = $organization_id
                    """,
                    project_ids=project_ids,
                    organization_id=organization_id,
                    legacy_organization_id=DEFAULT_ORGANIZATION_ID,
                ).consume()
            transaction.commit()

    def _ensure_constraints(self, session) -> None:
        for query in (
            "CREATE CONSTRAINT recall_organization_id_unique IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
            "CREATE CONSTRAINT recall_user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
            "CREATE CONSTRAINT recall_project_slug_unique IF NOT EXISTS FOR (p:Project) REQUIRE (p.organization_id, p.slug) IS UNIQUE",
        ):
            try:
                session.run(query).consume()
            except Exception as exc:
                logger.warning("Could not ensure Neo4j constraint: %s", exc)

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

    def _deduplicate_default_project_nodes(self, session, organization_id: str) -> None:
        session.run(
            """
            MATCH (p:Project {organization_id: $organization_id, slug: $project_id})
            WITH collect(p) as projects
            WHERE size(projects) > 1
            WITH head(projects) as canonical, tail(projects) as duplicates
            FOREACH (duplicate IN duplicates |
                SET canonical.name = coalesce(canonical.name, duplicate.name),
                    canonical.status = coalesce(canonical.status, duplicate.status),
                    canonical.created_at = coalesce(canonical.created_at, duplicate.created_at)
            )
            """,
            organization_id=organization_id,
            project_id=DEFAULT_PROJECT_ID,
        ).consume()
