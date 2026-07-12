from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import uuid
from neo4j import GraphDatabase
from core.config import settings

class ActivityStore:
    """Database-backed activity store with user-specific tracking."""
    
    def __init__(self):
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )
    
    def add_event(self, event_type: str, title: str, description: str, source: str = None, user_id: str = None):
        """Add a new activity event for a specific user."""
        event_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
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
                    user_id: $user_id
                })
                """,
                id=event_id,
                type=event_type,
                title=title,
                description=description,
                timestamp=timestamp,
                source=source or "",
                user_id=user_id or "anonymous"
            )
    
    def get_events(self, limit: int = 50, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent activity events for a specific user."""
        with self._driver.session() as session:
            if user_id:
                result = session.run(
                    """
                    MATCH (a:Activity {user_id: $user_id})
                    RETURN a.id as id, a.type as type, a.title as title,
                           a.description as description, a.timestamp as timestamp,
                           a.source as source
                    ORDER BY a.timestamp DESC
                    LIMIT $limit
                    """,
                    user_id=user_id,
                    limit=limit
                )
            else:
                result = session.run(
                    """
                    MATCH (a:Activity)
                    RETURN a.id as id, a.type as type, a.title as title,
                           a.description as description, a.timestamp as timestamp,
                           a.source as source
                    ORDER BY a.timestamp DESC
                    LIMIT $limit
                    """,
                    limit=limit
                )
            
            return [record.data() for record in result]
    
    def clear_user_events(self, user_id: str):
        """Clear all events for a specific user."""
        with self._driver.session() as session:
            session.run(
                "MATCH (a:Activity {user_id: $user_id}) DELETE a",
                user_id=user_id
            )

# Global activity store instance
activity_store = ActivityStore()
