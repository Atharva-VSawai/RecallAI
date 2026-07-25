from fastapi import APIRouter, Depends
from application.services.project_service import ProjectContext
from api.dependencies import require_project_permission

router = APIRouter(prefix="/graph", tags=["graph"])

@router.get("/data")
def graph_data(project: ProjectContext = Depends(require_project_permission("knowledge:read"))):
    from db.neo import _driver
    with _driver.session() as session:
        records = session.run(
            """
            MATCH (d:Decision {project_id: $project_id})
            OPTIONAL MATCH (d)-[:MADE_BY]->(p:Person)
            OPTIONAL MATCH (d)-[:BASED_ON]->(r:Reason)
            OPTIONAL MATCH (d)-[:ALTERNATIVE]->(a:Alternative)
            RETURN d,p,r,a
            """,
            project_id=project.project_id,
        ).data()
    nodes, edges = {}, set()
    for record in records:
        decision = record["d"]
        if not decision or not decision.get("id"):
            continue
        source, decision_id = decision.get("source", "unknown"), decision["id"]
        nodes.setdefault(decision_id, {"id": decision_id, "label": (decision.get("action") or "")[:60], "type": "Decision", "source": source, "subject": decision.get("subject", ""), "impact": decision.get("impact", "")})
        for key, name, node_type, relation in (("p", "name", "Person", "MADE_BY"), ("r", "text", "Reason", "BASED_ON"), ("a", "text", "Alternative", "ALTERNATIVE")):
            node = record[key]
            if node and node.get(name):
                node_id = f"{node[name]}@{source}"
                nodes.setdefault(node_id, {"id": node_id, "label": str(node[name])[:60], "type": node_type, "source": source})
                edges.add((decision_id, node_id, relation))
    return {"nodes": list(nodes.values()), "edges": [{"source": source, "target": target, "type": relation} for source, target, relation in edges]}
