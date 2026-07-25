import uuid
import time
import logging
from neo4j import GraphDatabase
from core.config import settings

logger = logging.getLogger(__name__)

_driver = GraphDatabase.driver(
    settings.neo4j_uri,
    auth=(settings.neo4j_username, settings.neo4j_password),
    max_connection_lifetime=3600,
    max_connection_pool_size=50,
    connection_acquisition_timeout=120,
)


def neo_store(
    subject: str,
    action: str,
    reason: str,
    source: str,
    people: list = None,
    impact: str = "",
    alternatives: list = None,
    timestamp: str = "",
    project_id: str | None = None,
    organization_id: str = "default",
) -> str:
    decision_id = str(uuid.uuid4())
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            with _driver.session() as session:
                session.run(
                    """
                    MERGE (org:Organization {id: $organization_id})
                    MERGE (project:Project {id: $project_id})
                    ON CREATE SET project.name = $project_id,
                                  project.slug = $project_id,
                                  project.organization_id = $organization_id,
                                  project.status = 'ACTIVE'
                    SET project.organization_id = coalesce(project.organization_id, $organization_id)
                    CREATE (d:Decision {id: $decision_id})
                    SET d.action    = $action,
                        d.subject   = $subject,
                        d.impact    = $impact,
                        d.source    = $source,
                        d.timestamp = $timestamp,
                        d.project_id = $project_id,
                        d.organization_id = $organization_id
                    MERGE (d)-[:BELONGS_TO]->(project)
                    WITH d, project
                    FOREACH (person IN $people |
                        MERGE (p:Person {name: person, project_id: $project_id})
                        MERGE (d)-[:MADE_BY]->(p)
                    )
                    WITH d
                    FOREACH (alt IN $alternatives |
                        MERGE (a:Alternative {text: alt, project_id: $project_id})
                        MERGE (d)-[:ALTERNATIVE]->(a)
                    )
                    WITH d
                    FOREACH (r IN CASE WHEN $reason <> '' THEN [$reason] ELSE [] END |
                        MERGE (rn:Reason {text: r, project_id: $project_id})
                        MERGE (d)-[:BASED_ON]->(rn)
                    )
                    """,
                    action=action, decision_id=decision_id,
                    subject=subject, impact=impact,
                    source=source, timestamp=timestamp,
                    people=people or [],
                    alternatives=alternatives or [],
                    reason=reason or "",
                    project_id=project_id or "main-workspace",
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


def neo_impact_search(topic: str, limit: int = 10, source_filter: str = None, project_id: str | None = None) -> list:
    """Find all decisions related to a topic and their downstream impacts."""
    with _driver.session() as session:
        result = session.run(
            """
            MATCH (d:Decision)
            OPTIONAL MATCH (d)-[:BASED_ON]->(r:Reason)
            OPTIONAL MATCH (d)-[:MADE_BY]->(p:Person)
            OPTIONAL MATCH (d)-[:ALTERNATIVE]->(a:Alternative)
            WITH d,
                 collect(DISTINCT r.text) as reasons,
                 collect(DISTINCT p.name) as people,
                 collect(DISTINCT a.text) as alternatives
            WHERE ($project_id IS NULL OR d.project_id = $project_id)
              AND ($source_filter IS NULL OR d.source = $source_filter)
              AND any(word IN split(toLower($topic), ' ')
                WHERE toLower(d.action)  CONTAINS word
                   OR toLower(d.subject) CONTAINS word
                   OR any(rr IN reasons WHERE toLower(rr) CONTAINS word)
            )
            RETURN d.id as id, d.action as decision, d.subject as topic,
                   d.impact as impact, d.source as source,
                   reasons, people, alternatives
            LIMIT $limit
            """,
            topic=topic, limit=limit, source_filter=source_filter, project_id=project_id,
        )
        return result.data()


def neo_search(query: str, limit: int = 5, source_filter: str = None, project_id: str | None = None) -> list:
    with _driver.session() as session:
        result = session.run(
            """
            MATCH (d:Decision)
            OPTIONAL MATCH (d)-[:BASED_ON]->(r:Reason)
            OPTIONAL MATCH (d)-[:MADE_BY]->(p:Person)
            OPTIONAL MATCH (d)-[:ALTERNATIVE]->(a:Alternative)
            WITH d,
                 collect(DISTINCT r.text) as reasons,
                 collect(DISTINCT p.name) as people,
                 collect(DISTINCT a.text) as alternatives
            WHERE ($project_id IS NULL OR d.project_id = $project_id)
              AND ($source_filter IS NULL OR d.source = $source_filter)
              AND any(word IN split(toLower($q), ' ')
                WHERE toLower(d.action)  CONTAINS word
                   OR toLower(d.subject) CONTAINS word
                   OR any(rr IN reasons WHERE toLower(rr) CONTAINS word)
                   OR any(pp IN people  WHERE toLower(pp) CONTAINS word)
            )
            RETURN d.id as id, d.action as decision, d.subject as topic,
                   d.impact as impact, d.source as source, d.timestamp as timestamp,
                   reasons, people, alternatives
            LIMIT $limit
            """,
            q=query, limit=limit, source_filter=source_filter, project_id=project_id,
        )
        return result.data()
