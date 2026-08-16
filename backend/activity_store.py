from typing import Any, Dict, List, Optional
from infrastructure.repositories.activity_repository import SupabaseActivityRepository, Neo4jActivityRepository

# Defaulting to Supabase based on Phase 3 architecture
# To revert to Neo4j temporarily during migration rollouts, swap with Neo4jActivityRepository()
activity_repository = SupabaseActivityRepository()

class ActivityStoreWrapper:
    """Wrapper for backward compatibility during Phase 3 migration."""
    
    def add_event(self, event_type: str, title: str, description: str = None, source: str = None, user_id: str = None, project_id: str = None, organization_id: str = None):
        activity_repository.create_event(
            event_type=event_type,
            title=title,
            description=description,
            source=source,
            user_id=user_id,
            project_id=project_id,
            organization_id=organization_id
        )
    
    def get_events(self, limit: int = 50, user_id: Optional[str] = None, project_id: Optional[str] = None, organization_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return activity_repository.list_events(
            limit=limit,
            user_id=user_id,
            project_id=project_id,
            organization_id=organization_id
        )

# Global activity store instance
activity_store = ActivityStoreWrapper()
