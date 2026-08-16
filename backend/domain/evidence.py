from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Evidence:
    """A traceable, tenant-scoped unit passed between retrieval and generation."""

    evidence_id: str
    organization_id: str
    project_id: str
    document_id: str
    source_type: str
    content: str
    relevance_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "organization_id": self.organization_id,
            "project_id": self.project_id,
            "document_id": self.document_id,
            "source_type": self.source_type,
            "content": self.content,
            "relevance_score": self.relevance_score,
            "metadata": dict(self.metadata),
        }
