import hashlib
import json
import logging
import re
from dataclasses import dataclass, replace
from typing import Any, Callable

from core.llm import get_llm
from db.chroma import chroma_search, vector_store
from db.neo import neo_search
from domain.evidence import Evidence
from langchain_core.messages import HumanMessage, SystemMessage
from application.services.observability_service import store

logger = logging.getLogger(__name__)

ANSWERABLE = "answerable"
INSUFFICIENT_EVIDENCE = "insufficient_evidence"
CONFLICTING_EVIDENCE = "conflicting_evidence"
_STOPWORDS = {"what", "was", "were", "the", "a", "an", "is", "does", "did", "who", "why", "when", "where", "how", "which", "about", "this", "that", "and", "or", "to", "of", "in", "on", "for", "from", "during", "after", "before", "between", "with", "say", "happen", "happened"}
_FILTER_KEYS = {"document_id", "chunk_id", "section", "page", "sheet", "row", "timestamp", "id"}


@dataclass(frozen=True)
class RetrievalFilters:
    """Exact source and metadata constraints extracted before retrieval."""

    source_filter: str | None = None
    metadata: dict[str, Any] | None = None
    identifiers: tuple[str, ...] = ()


def _tokens(value: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9][a-z0-9_-]+", value.lower()) if t not in _STOPWORDS and len(t) > 2}


def _identifier_candidates(question: str) -> tuple[str, ...]:
    quoted = re.findall(r"[`'\"]([^`'\"]{3,120})[`'\"]", question)
    patterned = re.findall(
        r"\b(?:document|audio|image|slack|teams):[A-Za-z0-9._:@/-]+|\b[A-Z]{2,10}-\d{1,8}\b|\b[0-9a-f]{12,64}\b|\b[0-9a-f]{8}-[0-9a-f-]{27,36}\b",
        question,
        flags=re.IGNORECASE,
    )
    values = []
    for value in [*quoted, *patterned]:
        cleaned = value.strip()
        if cleaned and cleaned.lower() not in {item.lower() for item in values}:
            values.append(cleaned)
    return tuple(values[:8])


def _parse_retrieval_filters(question: str, source_filter: str | None = None, metadata_filters: dict[str, Any] | None = None) -> RetrievalFilters:
    metadata = {key: value for key, value in (metadata_filters or {}).items() if key in _FILTER_KEYS and value not in (None, "")}
    for key in _FILTER_KEYS:
        match = re.search(rf"\b{re.escape(key)}\s*[:=]\s*([^\s,;]+)", question, flags=re.IGNORECASE)
        if match:
            metadata[key] = match.group(1).strip("'\"")
    section_match = re.search(r"\bsection\s+[`'\"]([^`'\"]+)[`'\"]", question, flags=re.IGNORECASE)
    if section_match:
        metadata["section"] = section_match.group(1).strip()
    return RetrievalFilters(source_filter=source_filter, metadata=metadata, identifiers=_identifier_candidates(question))


def _evidence_id(org: str, project: str, document: str, content: str, metadata: dict[str, Any]) -> str:
    location = "|".join(str(metadata.get(k, "")) for k in ("chunk_id", "page", "sheet", "row", "timestamp"))
    digest = hashlib.sha256(f"{org}|{project}|{document}|{location}|{content}".encode()).hexdigest()[:20]
    return f"ev_{digest}"


def _source_type(source: str, metadata: dict[str, Any]) -> str:
    if metadata.get("source_type"):
        return str(metadata["source_type"])
    return source.split(":", 1)[0] if ":" in source else "document"


def _from_chroma(item: dict[str, Any], org: str, project: str, retrieval_source: str = "vector") -> Evidence | None:
    meta = dict(item.get("metadata") or {})
    if meta.get("organization_id") != org or meta.get("project_id") != project:
        return None
    source = str(meta.get("source") or meta.get("source_filename") or "unknown")
    document_id = str(meta.get("document_id") or source)
    sources = set(meta.get("retrieval_sources", []))
    sources.add(retrieval_source)
    meta["retrieval_sources"] = sorted(sources)
    content = item.get("page_content", "")
    return Evidence(_evidence_id(org, project, document_id, content, meta), org, project, document_id, _source_type(source, meta), content, meta.get("relevance_score"), meta)


def _from_neo(record: dict[str, Any], org: str, project: str) -> Evidence | None:
    if record.get("organization_id", org) != org or record.get("project_id", project) != project:
        return None
    source = str(record.get("source") or "unknown")
    document_id = str(record.get("document_id") or record.get("source") or record.get("id") or "unknown")
    reasons = record.get("reasons") or []
    content = " | ".join(filter(None, [f"Decision: {record.get('decision', '')}", f"Topic: {record.get('topic', '')}", f"Reasons: {', '.join(reasons)}", f"People: {', '.join(record.get('people') or [])}", f"Alternatives: {', '.join(record.get('alternatives') or [])}", f"Impact: {record.get('impact', '')}"]))
    meta = {k: record[k] for k in ("id", "source", "timestamp", "page", "section", "chunk_id", "document_id") if record.get(k) is not None}
    if reasons:
        meta["reasons"] = reasons
    meta["retrieval_sources"] = ["fulltext"]
    return Evidence(_evidence_id(org, project, document_id, content, meta), org, project, document_id, _source_type(source, meta), content, record.get("score"), meta)


def _merge_duplicate(existing: Evidence, incoming: Evidence) -> Evidence:
    sources = sorted(set(existing.metadata.get("retrieval_sources", [])) | set(incoming.metadata.get("retrieval_sources", [])))
    score = max(existing.relevance_score or 0, incoming.relevance_score or 0) or None
    return replace(existing, relevance_score=score, metadata={**existing.metadata, **incoming.metadata, "retrieval_sources": sources})


def _hierarchy_key(item: Evidence) -> str:
    return "|".join(str(item.metadata.get(key) or "") for key in ("document_id", "source", "section", "sheet", "timestamp"))


def _rank_score(question: str, item: Evidence, filters: RetrievalFilters) -> float:
    haystack = f"{item.content} {json.dumps(item.metadata, default=str)}".lower()
    query_terms = _tokens(question)
    item_terms = _tokens(haystack)
    overlap = len(query_terms & item_terms) / max(len(query_terms), 1)
    score = overlap * 10.0
    if question.strip().lower() in haystack:
        score += 3.0
    for identifier in filters.identifiers:
        if identifier.lower() in haystack:
            score += 5.0
    for key, value in (filters.metadata or {}).items():
        if str(item.metadata.get(key, "")).lower() == str(value).lower():
            score += 4.0
    if item.relevance_score is not None:
        try:
            score += float(item.relevance_score)
        except (TypeError, ValueError):
            pass
    if len(item.metadata.get("retrieval_sources", [])) > 1:
        score += 2.0
    return score


def _with_rank(question: str, item: Evidence, filters: RetrievalFilters) -> Evidence:
    score = _rank_score(question, item, filters)
    return replace(item, metadata={**item.metadata, "rerank_score": round(score, 4), "hierarchy_key": _hierarchy_key(item)})


def _hierarchical_section_expansion(evidence: list[Evidence], organization_id: str, project_id: str, fetcher: Callable[..., list] | None) -> list[Evidence]:
    if not fetcher:
        return []
    expanded: list[Evidence] = []
    seen_filters: set[tuple[str, str]] = set()
    for item in evidence[:6]:
        section = item.metadata.get("section")
        document_id = item.document_id or item.metadata.get("document_id")
        if not section or not document_id:
            continue
        key = (str(document_id), str(section))
        if key in seen_filters:
            continue
        seen_filters.add(key)
        try:
            siblings = fetcher(organization_id, project_id, {"document_id": document_id, "section": section}, 3)
        except Exception as exc:
            logger.warning("Section expansion failed document=%s section=%s: %s", document_id, section, exc)
            continue
        for record in siblings:
            sibling = _from_chroma(record, organization_id, project_id, retrieval_source="section")
            if sibling:
                expanded.append(sibling)
    return expanded


def _hierarchical_select(evidence: list[Evidence], limit: int = 10) -> list[Evidence]:
    selected: list[Evidence] = []
    selected_ids: set[str] = set()
    used_groups: set[str] = set()
    for item in evidence:
        group = item.metadata.get("hierarchy_key") or _hierarchy_key(item)
        if group and group not in used_groups:
            selected.append(item)
            selected_ids.add(item.evidence_id)
            used_groups.add(group)
        if len(selected) >= limit:
            return selected
    for item in evidence:
        if item.evidence_id not in selected_ids:
            selected.append(item)
            selected_ids.add(item.evidence_id)
        if len(selected) >= limit:
            break
    return selected


def retrieve_evidence(
    question: str,
    organization_id: str,
    project_id: str,
    source_filter: str | None = None,
    neo_retriever: Callable[..., list] = neo_search,
    chroma_retriever: Callable[..., list] = chroma_search,
    metadata_filters: dict[str, Any] | None = None,
    section_fetcher: Callable[..., list] | None = None,
) -> list[Evidence]:
    """Run hybrid vector/full-text retrieval under the request tenant scope."""
    store.metric("retrieval_started", organization_id=organization_id, project_id=project_id)
    filters = _parse_retrieval_filters(question, source_filter, metadata_filters)
    evidence: list[Evidence] = []
    for record in neo_retriever(query=question, organization_id=organization_id, project_id=project_id, limit=8, source_filter=filters.source_filter, metadata_filters=filters.metadata):
        item = _from_neo(record, organization_id, project_id)
        if item:
            evidence.append(item)
    for record in chroma_retriever(query=question, organization_id=organization_id, project_id=project_id, k=12, source_filter=filters.source_filter, metadata_filters=filters.metadata):
        item = _from_chroma(record, organization_id, project_id)
        if item:
            evidence.append(item)
    fetcher = section_fetcher if section_fetcher is not None else (vector_store.get_by_metadata if chroma_retriever is chroma_search else None)
    evidence.extend(_hierarchical_section_expansion(evidence, organization_id, project_id, fetcher))
    unique: dict[str, Evidence] = {}
    for item in evidence:
        unique[item.evidence_id] = _merge_duplicate(unique[item.evidence_id], item) if item.evidence_id in unique else item
    ranked = sorted((_with_rank(question, item, filters) for item in unique.values()), key=lambda item: item.metadata.get("rerank_score", 0), reverse=True)
    selected = _hierarchical_select(ranked)
    store.metric("retrieval_completed", organization_id=organization_id, project_id=project_id, result_count=len(selected), hybrid=True)
    return selected


def _relevant(question: str, evidence: list[Evidence]) -> list[Evidence]:
    query_terms = _tokens(question)
    return [item for item in evidence if query_terms & _tokens(item.content + " " + json.dumps(item.metadata, default=str)) or item.metadata.get("rerank_score", 0) >= 5]


def _detect_conflicts(question: str, evidence: list[Evidence]) -> list[dict[str, Any]]:
    normalized = question.lower()
    if re.search(r"\bwhen\b|what date|what month", normalized):
        by_value: dict[str, list[str]] = {}
        for item in evidence:
            text = (item.content + " " + json.dumps(item.metadata, default=str)).lower()
            for value in re.findall(r"\b(?:20\d{2}[-/]\d{1,2}[-/]\d{1,2}|(?:january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+20\d{2})?)\b", text):
                by_value.setdefault(value, []).append(item.evidence_id)
        if len(by_value) > 1:
            return [{"type": "temporal", "values": [{"value": value, "evidence_ids": ids} for value, ids in sorted(by_value.items())]}]
    if re.search(r"\bwhy\b|reason", normalized):
        by_reason: dict[str, list[str]] = {}
        for item in evidence:
            for reason in item.metadata.get("reasons", []):
                cleaned = str(reason).strip().lower()
                if cleaned:
                    by_reason.setdefault(cleaned, []).append(item.evidence_id)
        if len(by_reason) > 1:
            return [{"type": "reason", "values": [{"value": value, "evidence_ids": ids} for value, ids in sorted(by_reason.items())]}]
    return []


def _conflicts(question: str, evidence: list[Evidence]) -> bool:
    return bool(_detect_conflicts(question, evidence))


def _evidence_span(question: str, item: Evidence, max_chars: int = 900) -> tuple[str, dict[str, Any]]:
    content = item.content or ""
    if len(content) <= max_chars:
        return content, {"start": 0, "end": len(content), "compressed": False}
    lower = content.lower()
    hits = [lower.find(term) for term in sorted(_tokens(question), key=len, reverse=True) if lower.find(term) >= 0]
    center = min(hits) if hits else 0
    start = max(0, center - max_chars // 3)
    end = min(len(content), start + max_chars)
    while start > 0 and content[start] not in ".\n ":
        start -= 1
    while end < len(content) and content[end - 1] not in ".\n ":
        end += 1
    return content[start:end].strip(), {"start": start, "end": end, "compressed": True}


def _compressed_context(question: str, evidence: list[Evidence]) -> tuple[str, list[Evidence]]:
    compressed: list[Evidence] = []
    blocks = []
    for item in evidence:
        span, span_meta = _evidence_span(question, item)
        metadata = {**item.metadata, "evidence_span": span_meta}
        compressed_item = replace(item, content=span, metadata=metadata)
        compressed.append(compressed_item)
        blocks.append(f"[{item.evidence_id}] {span}\nMetadata: {json.dumps(metadata, default=str)}")
    return "\n\n".join(blocks), compressed


def _parse_json(content: Any) -> dict[str, Any]:
    text = content if isinstance(content, str) else str(content)
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    return json.loads(text)


def run_grounded_query(question: str, source_filter: str | None, provider: str, project_id: str, organization_id: str) -> dict[str, Any]:
    evidence = retrieve_evidence(question, organization_id, project_id, source_filter)
    relevant = _relevant(question, evidence)
    conflicts = _detect_conflicts(question, relevant)
    status = CONFLICTING_EVIDENCE if conflicts else (ANSWERABLE if relevant else INSUFFICIENT_EVIDENCE)
    base = {
        "status": status,
        "claims": [],
        "evidence": [item.to_dict() for item in relevant],
        "source_trace": [{"evidence_id": item.evidence_id, "source": item.metadata.get("source", item.document_id), "metadata": item.metadata} for item in relevant],
        "agent_used": "QUERY",
        "reasoning": f"Hybrid retrieval found {len(relevant)} relevant evidence item(s).",
    }
    if conflicts:
        base["conflicts"] = conflicts
    if status != ANSWERABLE:
        base["answer"] = "I don't have enough grounded evidence to answer that question." if status == INSUFFICIENT_EVIDENCE else "The available sources conflict, so I can't give a single grounded answer."
        return base

    context, compressed = _compressed_context(question, relevant)
    prompt = f"Question: {question}\nEvidence:\n{context}\n\nReturn JSON only: {{\"status\": \"answerable\", \"claims\": [{{\"text\": \"...\", \"evidence_ids\": [\"ev_...\"]}}]}}. Every claim must cite one or more evidence IDs. Do not use knowledge outside the evidence."
    response = get_llm(provider, temperature=0, is_json=True).invoke([SystemMessage(content="Answer only from the supplied evidence. Produce grounded structured claims."), HumanMessage(content=prompt)])
    try:
        payload = _parse_json(response.content)
        valid_ids = {item.evidence_id for item in compressed}
        claims = [claim for claim in payload.get("claims", []) if claim.get("text") and set(claim.get("evidence_ids", [])) <= valid_ids and claim.get("evidence_ids")]
    except (ValueError, TypeError, json.JSONDecodeError):
        claims = []
    if not claims:
        base["status"] = INSUFFICIENT_EVIDENCE
        base["answer"] = "I don't have enough grounded evidence to answer that question."
        return base
    base["claims"] = claims
    base["answer"] = " ".join(claim["text"] for claim in claims)
    return base
