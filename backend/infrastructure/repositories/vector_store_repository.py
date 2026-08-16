from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class VectorStoreRepository(ABC):
    """Abstract repository for storing and retrieving semantic vectors."""

    @abstractmethod
    def add_vectors(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """Add vectors to the store."""
        pass

    @abstractmethod
    def query_vectors(
        self,
        query_embedding: List[float],
        k: int,
        organization_id: str,
        project_id: str,
        source_filter: Optional[str] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Query vectors strictly isolated by organization and project."""
        pass

    def get_by_metadata(
        self,
        organization_id: str,
        project_id: str,
        metadata_filters: Dict[str, Any],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Fetch vectors by exact metadata filters within a tenant/project."""
        return []

    @abstractmethod
    def get_existing_ids(self, ids: List[str], organization_id: str, project_id: str) -> set[str]:
        """Check which of the given IDs already exist in the vector store."""
        pass

    @abstractmethod
    def delete_by_source(self, organization_id: str, project_id: str, source: str) -> bool:
        """Delete all vectors for a specific source within a project."""
        pass

    @abstractmethod
    def delete_by_project(self, organization_id: str, project_id: str) -> bool:
        """Delete all vectors for a project."""
        pass

    @abstractmethod
    def delete_by_ids(self, organization_id: str, project_id: str, ids: List[str]) -> bool:
        """Delete specific vectors by ID."""
        pass
