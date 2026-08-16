import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from application.services.grounded_query_service import (
    ANSWERABLE,
    CONFLICTING_EVIDENCE,
    INSUFFICIENT_EVIDENCE,
    _compressed_context,
    retrieve_evidence,
    run_grounded_query,
)


def _neo(reason="scalability", timestamp="2026-03-01"):
    return [{
        "id": "decision-1", "decision": "PostgreSQL selected", "topic": "database",
        "impact": "migration", "source": "document:architecture.pdf", "timestamp": timestamp,
        "reasons": [reason], "people": ["Sarah"], "alternatives": ["MongoDB"],
    }]


def test_evidence_preserves_tenant_and_source_metadata():
    items = retrieve_evidence(
        "Why was PostgreSQL selected?", "org-a", "project-a",
        neo_retriever=lambda **_: _neo(),
        chroma_retriever=lambda **_: [{"page_content": "PostgreSQL was selected for scalability.", "metadata": {
            "organization_id": "org-a", "project_id": "project-a", "document_id": "doc-1",
            "source": "document:architecture.pdf", "page": 17, "section": "Database Migration", "chunk_id": "chunk-7",
        }}],
    )
    assert len(items) == 2
    assert all(item.organization_id == "org-a" and item.project_id == "project-a" for item in items)
    assert any(item.metadata.get("page") == 17 and item.metadata.get("section") == "Database Migration" for item in items)


def test_empty_or_irrelevant_retrieval_abstains_without_llm_call():
    with patch("application.services.grounded_query_service.retrieve_evidence", return_value=[]), patch("application.services.grounded_query_service.get_llm") as llm:
        result = run_grounded_query("What database does the project use?", None, "groq", "project-a", "org-a")
    assert result["status"] == INSUFFICIENT_EVIDENCE
    llm.assert_not_called()

    irrelevant = SimpleNamespace(evidence_id="ev_x", organization_id="org-a", project_id="project-a", document_id="doc", source_type="document", content="The team discussed lunch.", relevance_score=None, metadata={"source": "notes.txt"}, to_dict=lambda: {"evidence_id": "ev_x"})
    with patch("application.services.grounded_query_service.retrieve_evidence", return_value=[irrelevant]), patch("application.services.grounded_query_service.get_llm") as llm:
        result = run_grounded_query("What database does the project use?", None, "groq", "project-a", "org-a")
    assert result["status"] == INSUFFICIENT_EVIDENCE
    llm.assert_not_called()


def test_conflicting_sources_are_returned_without_generation():
    with patch("application.services.grounded_query_service.retrieve_evidence", side_effect=lambda *args, **kwargs: [
        retrieve_evidence("when", "org-a", "project-a", neo_retriever=lambda **_: _neo(timestamp="March 2026"), chroma_retriever=lambda **_: [])[0],
        retrieve_evidence("when", "org-a", "project-a", neo_retriever=lambda **_: _neo(timestamp="April 2026"), chroma_retriever=lambda **_: [])[0],
    ]), patch("application.services.grounded_query_service.get_llm") as llm:
        result = run_grounded_query("When did the migration happen?", None, "groq", "project-a", "org-a")
    assert result["status"] == CONFLICTING_EVIDENCE
    assert len(result["evidence"]) == 2
    llm.assert_not_called()


def test_claims_must_reference_returned_evidence_ids():
    fake_llm = MagicMock()
    evidence = retrieve_evidence("why PostgreSQL", "org-a", "project-a", neo_retriever=lambda **_: [], chroma_retriever=lambda **_: [{"page_content": "PostgreSQL was selected for scalability. Sarah proposed it.", "metadata": {"organization_id": "org-a", "project_id": "project-a", "document_id": "doc-1", "source": "meeting.txt"}}])
    valid_id = evidence[0].evidence_id
    fake_llm.invoke.return_value = SimpleNamespace(content=json.dumps({"status": "answerable", "claims": [
        {"text": "Unsupported claim.", "evidence_ids": ["ev_missing"]},
        {"text": "Sarah proposed the decision.", "evidence_ids": [valid_id]},
    ]}))
    with patch("application.services.grounded_query_service.retrieve_evidence", return_value=evidence), patch("application.services.grounded_query_service.get_llm", return_value=fake_llm):
        result = run_grounded_query("Why was PostgreSQL selected?", None, "groq", "project-a", "org-a")
    assert result["status"] == ANSWERABLE
    assert result["claims"] == [{"text": "Sarah proposed the decision.", "evidence_ids": [valid_id]}]


def test_cross_tenant_records_are_discarded_before_generation():
    items = retrieve_evidence("database", "org-a", "project-a", neo_retriever=lambda **_: [{"id": "bad", "decision": "secret database", "topic": "database", "source": "secret", "organization_id": "org-b", "project_id": "project-b"}], chroma_retriever=lambda **_: [{"page_content": "secret", "metadata": {"organization_id": "org-b", "project_id": "project-b", "document_id": "bad", "source": "secret"}}])
    assert items == []


def test_phase3_hybrid_retrieval_passes_metadata_filters_and_reranks_exact_identifier():
    calls = {}

    def neo_retriever(**kwargs):
        calls["neo"] = kwargs
        return []

    def chroma_retriever(**kwargs):
        calls["chroma"] = kwargs
        return [
            {"page_content": "General PostgreSQL migration notes.", "metadata": {"organization_id": "org-a", "project_id": "project-a", "document_id": "doc-general", "source": "doc"}},
            {"page_content": "Ticket ARCH-123 selected PostgreSQL for the reporting database.", "metadata": {"organization_id": "org-a", "project_id": "project-a", "document_id": "doc-arch", "chunk_id": "ARCH-123", "source": "doc"}},
        ]

    items = retrieve_evidence(
        "What does chunk_id:ARCH-123 say about PostgreSQL?",
        "org-a",
        "project-a",
        neo_retriever=neo_retriever,
        chroma_retriever=chroma_retriever,
    )

    assert calls["neo"]["metadata_filters"] == {"chunk_id": "ARCH-123"}
    assert calls["chroma"]["metadata_filters"] == {"chunk_id": "ARCH-123"}
    assert items[0].metadata["chunk_id"] == "ARCH-123"
    assert items[0].metadata["rerank_score"] > items[1].metadata["rerank_score"]


def test_phase3_hierarchical_section_expansion_adds_same_section_siblings():
    def chroma_retriever(**_):
        return [{"page_content": "The migration section says PostgreSQL was selected.", "metadata": {
            "organization_id": "org-a", "project_id": "project-a", "document_id": "doc-1",
            "source": "document:architecture.pdf", "section": "Database Migration", "chunk_id": "chunk-1",
        }}]

    def section_fetcher(organization_id, project_id, filters, limit):
        assert organization_id == "org-a"
        assert project_id == "project-a"
        assert filters == {"document_id": "doc-1", "section": "Database Migration"}
        assert limit == 3
        return [{"page_content": "The same section also lists MongoDB as an alternative.", "metadata": {
            "organization_id": "org-a", "project_id": "project-a", "document_id": "doc-1",
            "source": "document:architecture.pdf", "section": "Database Migration", "chunk_id": "chunk-2",
        }}]

    items = retrieve_evidence(
        "What alternatives were considered in the Database Migration section?",
        "org-a",
        "project-a",
        neo_retriever=lambda **_: [],
        chroma_retriever=chroma_retriever,
        section_fetcher=section_fetcher,
    )

    assert {item.metadata["chunk_id"] for item in items} == {"chunk-1", "chunk-2"}
    assert any("section" in item.metadata["retrieval_sources"] for item in items)


def test_phase3_conflict_response_includes_conflict_groups():
    with patch("application.services.grounded_query_service.retrieve_evidence", side_effect=lambda *args, **kwargs: [
        retrieve_evidence("when", "org-a", "project-a", neo_retriever=lambda **_: _neo(timestamp="March 2026"), chroma_retriever=lambda **_: [])[0],
        retrieve_evidence("when", "org-a", "project-a", neo_retriever=lambda **_: _neo(timestamp="April 2026"), chroma_retriever=lambda **_: [])[0],
    ]), patch("application.services.grounded_query_service.get_llm") as llm:
        result = run_grounded_query("When did the migration happen?", None, "groq", "project-a", "org-a")

    assert result["status"] == CONFLICTING_EVIDENCE
    assert result["conflicts"][0]["type"] == "temporal"
    llm.assert_not_called()


def test_phase3_context_compression_preserves_evidence_span_metadata():
    long_prefix = "Intro filler. " * 120
    long_suffix = " Closing filler." * 120
    evidence = retrieve_evidence(
        "Why was PostgreSQL selected?",
        "org-a",
        "project-a",
        neo_retriever=lambda **_: [],
        chroma_retriever=lambda **_: [{"page_content": f"{long_prefix}PostgreSQL was selected for scalability and reliability.{long_suffix}", "metadata": {"organization_id": "org-a", "project_id": "project-a", "document_id": "doc-1", "source": "architecture.pdf"}}],
    )

    context, compressed = _compressed_context("Why was PostgreSQL selected?", evidence)

    assert len(compressed[0].content) < len(evidence[0].content)
    assert "PostgreSQL was selected for scalability" in context
    assert compressed[0].metadata["evidence_span"]["compressed"] is True
    assert compressed[0].metadata["evidence_span"]["start"] >= 0
