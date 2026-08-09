from fastapi import APIRouter, Depends, Query
from application.services.project_service import ProjectContext
from api.dependencies import require_project_permission
from db.neo import execute_with_retry

router = APIRouter(prefix="/graph", tags=["graph"])

@router.get("/data")
def graph_data(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    project: ProjectContext = Depends(require_project_permission("knowledge:read")),
):
    def query(session):
        total = session.run(
            """
            MATCH (d:Decision {project_id: $project_id, organization_id: $organization_id})
            RETURN count(d) AS total_decisions
            """,
            project_id=project.project_id,
            organization_id=project.organization_id,
        ).single()["total_decisions"]
        records = session.run(
            """
            MATCH (d:Decision {project_id: $project_id, organization_id: $organization_id})
            WITH d
            ORDER BY coalesce(d.timestamp, '') DESC, d.id ASC
            SKIP $offset
            LIMIT $limit
            CALL {
                WITH d
                OPTIONAL MATCH (d)-[:MADE_BY]->(p:Person)
                WITH collect(DISTINCT p) AS people
                RETURN people[0..$relation_limit] AS people
            }
            CALL {
                WITH d
                OPTIONAL MATCH (d)-[:BASED_ON]->(r:Reason)
                WITH collect(DISTINCT r) AS reasons
                RETURN reasons[0..$relation_limit] AS reasons
            }
            CALL {
                WITH d
                OPTIONAL MATCH (d)-[:ALTERNATIVE]->(a:Alternative)
                WITH collect(DISTINCT a) AS alternatives
                RETURN alternatives[0..$relation_limit] AS alternatives
            }
            RETURN d,people,reasons,alternatives
            """,
            project_id=project.project_id,
            organization_id=project.organization_id,
            limit=limit,
            offset=offset,
            relation_limit=2,
        ).data()
        return total, records

    total_decisions, records = execute_with_retry(query, operation_name=f"graph_data project={project.project_id} offset={offset} limit={limit}")
    nodes, edges = {}, set()
    for record in records:
        decision = record["d"]
        if not decision or not decision.get("id"):
            continue
        source, decision_id = decision.get("source", "unknown"), decision["id"]
        nodes.setdefault(decision_id, {"id": decision_id, "label": (decision.get("action") or "")[:60], "type": "Decision", "source": source, "subject": decision.get("subject", ""), "impact": decision.get("impact", "")})
        for key, name, node_type, relation in (("people", "name", "Person", "MADE_BY"), ("reasons", "text", "Reason", "BASED_ON"), ("alternatives", "text", "Alternative", "ALTERNATIVE")):
            for node in record[key] or []:
                if node and node.get(name):
                    node_id = f"{node[name]}@{source}"
                    nodes.setdefault(node_id, {"id": node_id, "label": str(node[name])[:60], "type": node_type, "source": source})
                    edges.add((decision_id, node_id, relation))
    returned_decisions = sum(1 for node in nodes.values() if node["type"] == "Decision")
    return {
        "nodes": list(nodes.values()),
        "edges": [{"source": source, "target": target, "type": relation} for source, target, relation in edges],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "returned_decisions": returned_decisions,
            "total_decisions": total_decisions,
            "has_more": offset + returned_decisions < total_decisions,
        },
    }
