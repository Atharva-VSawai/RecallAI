import uuid
import time
import logging
import re
import hashlib
from threading import Lock
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired, TransientError
from core.config import settings

logger = logging.getLogger(__name__)

_driver_instance = None
_driver_lock = Lock()


class _DriverProxy:
    """Stable object used by legacy modules while the real driver is startup-owned."""
    def _get(self):
        return get_driver()

    def session(self, *args, **kwargs):
        return self._get().session(*args, **kwargs)

    def verify_connectivity(self):
        return self._get().verify_connectivity()

    def close(self):
        return close_driver()


_driver = _DriverProxy()


def init_driver():
    global _driver_instance
    with _driver_lock:
        if _driver_instance is None:
            logger.info("neo4j.driver.initializing uri=%s", settings.neo4j_uri)
            _driver_instance = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_username, settings.neo4j_password),
                max_connection_lifetime=1800,
                max_connection_pool_size=50,
                connection_acquisition_timeout=15,
                connection_timeout=10,
                liveness_check_timeout=30,
            )
    return _driver_instance


def get_driver():
    return _driver_instance or init_driver()


def close_driver():
    global _driver_instance
    with _driver_lock:
        if _driver_instance is not None:
            logger.info("neo4j.driver.closing")
            _driver_instance.close()
            _driver_instance = None


def execute_with_retry(operation, *, operation_name: str, max_attempts: int = 4):
    """Run one complete session operation, retrying only transient Neo4j failures."""
    delay = 0.25
    transient_errors = (ServiceUnavailable, SessionExpired, TransientError)
    for attempt in range(1, max_attempts + 1):
        started = time.monotonic()
        try:
            logger.info("neo4j.query.start operation=%s attempt=%d", operation_name, attempt)
            logger.info("neo4j.connection.acquire.start operation=%s attempt=%d", operation_name, attempt)
            with get_driver().session() as session:
                logger.info("neo4j.connection.acquire.success operation=%s attempt=%d", operation_name, attempt)
                logger.info("neo4j.session.created operation=%s attempt=%d", operation_name, attempt)
                result = operation(session)
            logger.info("neo4j.query.success operation=%s attempt=%d duration_ms=%d", operation_name, attempt, (time.monotonic() - started) * 1000)
            return result
        except transient_errors as exc:
            if attempt == max_attempts:
                logger.exception("neo4j.query.failed operation=%s attempts=%d", operation_name, attempt)
                raise
            logger.warning("neo4j.query.retry operation=%s attempt=%d next_delay_s=%.2f error=%s", operation_name, attempt, delay, type(exc).__name__)
            time.sleep(delay)
            delay = min(delay * 2, 4.0)
        except Exception:
            logger.exception("neo4j.query.failed operation=%s attempt=%d", operation_name, attempt)
            raise


_FULLTEXT_INDEXES = (
    "CREATE FULLTEXT INDEX decision_search IF NOT EXISTS FOR (d:Decision) ON EACH [d.action, d.subject, d.impact]",
    "CREATE FULLTEXT INDEX meeting_knowledge_search IF NOT EXISTS FOR (k:MeetingKnowledge) ON EACH [k.title, k.details, k.category, k.technology]",
    "CREATE FULLTEXT INDEX person_search IF NOT EXISTS FOR (p:Person) ON EACH [p.name]",
    "CREATE FULLTEXT INDEX reason_search IF NOT EXISTS FOR (r:Reason) ON EACH [r.text]",
)


def ensure_search_indexes() -> None:
    """Apply the idempotent Neo4j full-text migration at application startup."""
    with get_driver().session() as session:
        for statement in _FULLTEXT_INDEXES:
            session.run(statement).consume()
    logger.info("neo4j.fulltext_indexes.ready count=%d", len(_FULLTEXT_INDEXES))


def _fulltext_query(value: str) -> str:
    """Turn user text into a bounded, safe Lucene OR query."""
    terms = re.findall(r"[\w-]+", value.lower(), flags=re.UNICODE)[:12]
    return " OR ".join(f'"{term}"' for term in terms)


def neo_store(
    subject: str,
    action: str,
    reason: str,
    source: str,
    project_id: str,
    organization_id: str,
    people: list = None,
    impact: str = "",
    alternatives: list = None,
    timestamp: str = "",
) -> str:
    if not project_id or not organization_id:
        raise ValueError("organization_id and project_id are required")
    normalized = "|".join([
        organization_id, project_id, subject.strip().lower(),
        action.strip().lower(), reason.strip().lower(), impact.strip().lower(),
        timestamp.strip(), "\x1f".join(sorted(people or [])), "\x1f".join(sorted(alternatives or [])),
    ])
    decision_id = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            with _driver.session() as session:
                session.run(
                    """
                    MERGE (org:Organization {id: $organization_id})
                    MERGE (project:Project {id: $project_id, organization_id: $organization_id})
                    ON CREATE SET project.name = $project_id,
                                  project.slug = $project_id,
                                  project.organization_id = $organization_id,
                                  project.status = 'ACTIVE'
                    SET project.organization_id = coalesce(project.organization_id, $organization_id)
                    MERGE (d:Decision {id: $decision_id})
                    SET d.action    = $action,
                        d.subject   = $subject,
                        d.impact    = $impact,
                        d.source    = coalesce(d.source, $source),
                        d.sources   = CASE WHEN d.sources IS NULL OR NOT $source IN d.sources THEN coalesce(d.sources, []) + $source ELSE d.sources END,
                        d.timestamp = $timestamp,
                        d.project_id = $project_id,
                        d.organization_id = $organization_id
                    MERGE (d)-[:BELONGS_TO]->(project)
                    WITH d, project
                    FOREACH (person IN $people |
                        MERGE (p:Person {name: person, project_id: $project_id, organization_id: $organization_id})
                        MERGE (d)-[:MADE_BY]->(p)
                    )
                    WITH d
                    FOREACH (alt IN $alternatives |
                        MERGE (a:Alternative {text: alt, project_id: $project_id, organization_id: $organization_id})
                        MERGE (d)-[:ALTERNATIVE]->(a)
                    )
                    WITH d
                    FOREACH (r IN CASE WHEN $reason <> '' THEN [$reason] ELSE [] END |
                        MERGE (rn:Reason {text: r, project_id: $project_id, organization_id: $organization_id})
                        MERGE (d)-[:BASED_ON]->(rn)
                    )
                    WITH d
                    MERGE (doc:Document {source: $source, project_id: $project_id, organization_id: $organization_id})
                    MERGE (doc)-[:SUPPORTS]->(d)
                    """,
                    action=action, decision_id=decision_id,
                    subject=subject, impact=impact,
                    source=source, timestamp=timestamp,
                    people=people or [],
                    alternatives=alternatives or [],
                    reason=reason or "",
                    project_id=project_id,
                    organization_id=organization_id,
                )
            logger.info(f"[NEO4J] Stored decision: {decision_id}")
            return decision_id
        except Exception as e:
            logger.warning(f"[NEO4J] Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error(f"[NEO4J] Failed to store after {max_retries} attempts")
                raise


def neo_store_meeting_knowledge(meeting_id: str, source: str, item: dict, project_id: str, organization_id: str) -> str:
    """Persist rich meeting entities while retaining the existing Decision model."""
    if not project_id or not organization_id:
        raise ValueError("organization_id and project_id are required")
    key = "|".join([organization_id, project_id, meeting_id, item.get("category", "other"), item.get("title", ""), item.get("details", "")])
    knowledge_id = hashlib.sha256(key.encode("utf-8")).hexdigest()
    with _driver.session() as session:
        session.run(
            """
            MERGE (p:Project {id: $project_id, organization_id: $organization_id})
            MERGE (m:Meeting {id: $meeting_id, project_id: $project_id})
            SET m.source = $source, m.organization_id = $organization_id
            MERGE (k:MeetingKnowledge {id: $knowledge_id})
            SET k.category = $category, k.title = $title, k.details = $details,
                k.deadline = $deadline, k.technology = $technology, k.source = $source,
                k.project_id = $project_id, k.organization_id = $organization_id
            MERGE (m)-[:HAS_KNOWLEDGE]->(k)
            MERGE (m)-[:BELONGS_TO]->(p)
            FOREACH (person IN $people |
                MERGE (person_node:Person {name: person, project_id: $project_id, organization_id: $organization_id})
                MERGE (k)-[:INVOLVES]->(person_node))
            RETURN k.id as id
            """,
            project_id=project_id, meeting_id=meeting_id, source=source,
            knowledge_id=knowledge_id, category=item.get("category", "other"), title=item.get("title", ""),
            details=item.get("details", ""), deadline=item.get("deadline"), technology=item.get("technology"),
            people=item.get("people") or [], organization_id=organization_id,
        )
    return knowledge_id


def _search_decision_fulltext(session, fulltext_query: str, limit: int, source_filter: str | None, project_id: str, organization_id: str, metadata_filters: dict | None = None) -> list:
    filters = metadata_filters or {}
    return session.run(
        """
        CALL () {
            CALL db.index.fulltext.queryNodes('decision_search', $fulltext_query, {limit: $candidate_limit})
            YIELD node, score
            RETURN node AS d, score
            UNION
            CALL db.index.fulltext.queryNodes('person_search', $fulltext_query, {limit: $candidate_limit})
            YIELD node AS person, score
            MATCH (d:Decision)-[:MADE_BY]->(person)
            RETURN d, score
            UNION
            CALL db.index.fulltext.queryNodes('reason_search', $fulltext_query, {limit: $candidate_limit})
            YIELD node AS reason, score
            MATCH (d:Decision)-[:BASED_ON]->(reason)
            RETURN d, score
        }
        WITH d, max(score) AS score
        WHERE d.project_id = $project_id
          AND d.organization_id = $organization_id
          AND ($source_filter IS NULL OR d.source = $source_filter)
          AND ($document_id IS NULL OR d.id = $document_id OR d.source = $document_id)
          AND ($chunk_id IS NULL OR d.chunk_id = $chunk_id)
          AND ($section IS NULL OR d.section = $section)
          AND ($page IS NULL OR d.page = $page)
        OPTIONAL MATCH (d)-[:BASED_ON]->(r:Reason)
        OPTIONAL MATCH (d)-[:MADE_BY]->(p:Person)
        OPTIONAL MATCH (d)-[:ALTERNATIVE]->(a:Alternative)
        WITH d, score,
             collect(DISTINCT r.text) as reasons,
             collect(DISTINCT p.name) as people,
             collect(DISTINCT a.text) as alternatives
        RETURN d.id as id, d.action as decision, d.subject as topic,
               d.impact as impact, d.source as source, d.timestamp as timestamp,
               reasons, people, alternatives
        ORDER BY score DESC, d.timestamp DESC
        LIMIT $limit
        """,
        fulltext_query=fulltext_query,
        candidate_limit=max(limit * 10, 50),
        limit=limit,
        source_filter=source_filter,
        project_id=project_id,
        organization_id=organization_id,
        document_id=filters.get("document_id") or filters.get("id"),
        chunk_id=filters.get("chunk_id"),
        section=filters.get("section"),
        page=filters.get("page"),
    ).data()


def _search_meeting_fulltext(session, fulltext_query: str, limit: int, source_filter: str | None, project_id: str, organization_id: str, metadata_filters: dict | None = None) -> list:
    filters = metadata_filters or {}
    return session.run(
        """
        CALL db.index.fulltext.queryNodes('meeting_knowledge_search', $fulltext_query, {limit: $candidate_limit})
        YIELD node AS k, score
        WHERE k.project_id = $project_id
          AND k.organization_id = $organization_id
          AND ($source_filter IS NULL OR k.source = $source_filter)
          AND ($document_id IS NULL OR k.id = $document_id OR k.source = $document_id)
          AND ($chunk_id IS NULL OR k.chunk_id = $chunk_id)
          AND ($section IS NULL OR k.section = $section)
          AND ($page IS NULL OR k.page = $page)
        OPTIONAL MATCH (k)-[:INVOLVES]->(p:Person)
        RETURN k.id as id, k.title as decision, k.category as topic,
               k.details as impact, k.source as source, '' as timestamp,
               [] as reasons, collect(DISTINCT p.name) as people, [] as alternatives,
               score
        ORDER BY score DESC
        LIMIT $limit
        """,
        fulltext_query=fulltext_query,
        candidate_limit=max(limit * 10, 50),
        limit=limit,
        source_filter=source_filter,
        project_id=project_id,
        organization_id=organization_id,
        document_id=filters.get("document_id") or filters.get("id"),
        chunk_id=filters.get("chunk_id"),
        section=filters.get("section"),
        page=filters.get("page"),
    ).data()


def _fulltext_search(query: str, limit: int, source_filter: str | None, project_id: str | None, organization_id: str | None, metadata_filters: dict | None = None) -> list:
    # Require tenant scope to avoid returning cross-project data.
    if not project_id or not organization_id:
        logger.warning("[NEO] _fulltext_search called without project_id or organization_id — returning empty")
        return []
    lucene_query = _fulltext_query(query)
    if not lucene_query:
        return []
    with _driver.session() as session:
        decisions = _search_decision_fulltext(session, lucene_query, limit, source_filter, project_id, organization_id, metadata_filters)
        knowledge = _search_meeting_fulltext(session, lucene_query, limit, source_filter, project_id, organization_id, metadata_filters)
    return decisions + knowledge


def neo_impact_search(topic: str, organization_id: str | None = None, project_id: str | None = None, limit: int = 10, source_filter: str | None = None) -> list:
    """Find impact candidates via Neo4j full-text indexes, never a graph scan."""
    return _fulltext_search(topic, limit, source_filter, project_id, organization_id)


def neo_search(query: str, organization_id: str | None = None, project_id: str | None = None, limit: int = 5, source_filter: str | None = None, metadata_filters: dict | None = None) -> list:
    return _fulltext_search(query, limit, source_filter, project_id, organization_id, metadata_filters)
