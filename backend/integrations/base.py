from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class KnowledgeDocument:
    external_id: str
    title: str
    text: str
    source: str
    metadata: dict


class KnowledgeSourceAdapter(Protocol):
    provider: str

    def list_documents(self, access_token: str) -> list[KnowledgeDocument]: ...

    def fetch_document(self, access_token: str, document: KnowledgeDocument) -> KnowledgeDocument: ...
