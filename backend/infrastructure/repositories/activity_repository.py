import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import logging

from db.neo import _driver
from db.supabase_client import supabase

logger = logging.getLogger(__name__)

class ActivityRepository(ABC):
    """Abstract repository for operational application events."""

    @abstractmethod
    def create_event(
        self,
        event_type: str,
        title: str,
        description: str = None,
        source: str = None,
        user_id: str = None,
        project_id: str = None,
        organization_id: str = None,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_events(
        self,
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        pass


class Neo4jActivityRepository(ActivityRepository):
    """Legacy Neo4j-based activity store."""

    def __init__(self):
        self._driver = _driver

    def create_event(
        self,
        event_type: str,
        title: str,
        description: str = None,
        source: str = None,
        user_id: str = None,
        project_id: str = None,
        organization_id: str = None,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        event_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        if not organization_id:
            raise ValueError("organization_id is required")
        if not project_id:
            raise ValueError("project_id is required")

        with self._driver.session() as session:
            session.run(
                """
                CREATE (a:Activity {
                    id: $id,
                    type: $type,
                    title: $title,
                    description: $description,
                    timestamp: $timestamp,
                    source: $source,
                    user_id: $user_id,
                    project_id: $project_id,
                    organization_id: $organization_id
                })
                """,
                id=event_id,
                type=event_type,
                title=title,
                description=description or "",
                timestamp=timestamp,
                source=source or "",
                user_id=user_id or "anonymous",
                project_id=project_id,
                organization_id=organization_id
            )
        
        return {
            "id": event_id,
            "type": event_type,
            "title": title,
            "description": description,
            "timestamp": timestamp,
            "source": source,
            "user_id": user_id,
            "project_id": project_id,
            "organization_id": organization_id,
        }

    def list_events(
        self,
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (a:Activity)
                WHERE ($user_id IS NULL OR a.user_id = $user_id)
                  AND ($project_id IS NULL OR a.project_id = $project_id)
                  AND ($organization_id IS NULL OR a.organization_id = $organization_id)
                RETURN a.id as id, a.type as type, a.title as title,
                       a.description as description, a.timestamp as timestamp,
                       a.source as source, a.project_id as project_id,
                       a.organization_id as organization_id
                ORDER BY a.timestamp DESC
                SKIP $offset
                LIMIT $limit
                """,
                user_id=user_id,
                project_id=project_id,
                organization_id=organization_id,
                offset=offset,
                limit=limit,
            )
            return [record.data() for record in result]


class SupabaseActivityRepository(ActivityRepository):
    """Supabase-based operational activity store."""
    
    def create_event(
        self,
        event_type: str,
        title: str,
        description: str = None,
        source: str = None,
        user_id: str = None,
        project_id: str = None,
        organization_id: str = None,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        if not organization_id:
            raise ValueError("organization_id is required")
        if not project_id:
            raise ValueError("project_id is required")

        data = {
            "event_type": event_type,
            "title": title,
            "description": description,
            "source": source,
            "user_id": user_id or "anonymous",
            "project_id": project_id,
            "organization_id": organization_id,
            "metadata": metadata or {},
        }
        try:
            response = supabase.table("activities").insert(data).execute()
            if response.data:
                # Map to standard format
                row = response.data[0]
                return {
                    "id": row["id"],
                    "type": row["event_type"],
                    "title": row["title"],
                    "description": row["description"],
                    "timestamp": row["created_at"],
                    "source": row["source"],
                    "user_id": row["user_id"],
                    "project_id": row["project_id"],
                    "organization_id": row["organization_id"],
                }
            return data
        except Exception as exc:
            logger.error(f"Failed to write activity to Supabase: {exc}")
            raise RuntimeError("Activity storage is unavailable") from exc

    def list_events(
        self,
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        try:
            query = supabase.table("activities").select("*")
            if user_id:
                query = query.eq("user_id", user_id)
            if project_id:
                query = query.eq("project_id", project_id)
            if organization_id:
                query = query.eq("organization_id", organization_id)
            
            response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            
            return [
                {
                    "id": row["id"],
                    "type": row["event_type"],
                    "title": row["title"],
                    "description": row["description"],
                    "timestamp": row["created_at"],
                    "source": row["source"],
                    "user_id": row["user_id"],
                    "project_id": row["project_id"],
                    "organization_id": row["organization_id"],
                }
                for row in (response.data or [])
            ]
        except Exception as exc:
            logger.error(f"Failed to read activity from Supabase: {exc}")
            raise RuntimeError("Activity storage is unavailable") from exc
