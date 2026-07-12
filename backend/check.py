from dotenv import load_dotenv; load_dotenv()
from core.config import settings
from neo4j import GraphDatabase

driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_username, settings.neo4j_password))
with driver.session() as s:
    print("=== NODES ===")
    for r in s.run("MATCH (n) RETURN labels(n) as l, count(n) as c").data():
        print(r)

    print("\n=== RELATIONSHIPS ===")
    for r in s.run("MATCH ()-[r]->() RETURN type(r) as t, count(r) as c").data():
        print(r)

    print("\n=== SAMPLE DECISIONS ===")
    for r in s.run("MATCH (d:Decision) RETURN d.action as action, d.subject as subject, d.id as id LIMIT 3").data():
        print(r)

print("\n=== NEO STORE TEST ===")
try:
    from db.neo import neo_store
    did = neo_store(
        subject="tech",
        action="Test decision",
        reason="Test reason",
        source="test",
        people=["Alice"],
        impact="Test impact",
        alternatives=["Option A"],
        timestamp="2024",
    )
    print("Stored decision_id:", did)
except Exception as e:
    print("ERROR:", e)

print("\n=== SEARCH TEST ===")
from db.neo import neo_search
print(neo_search("test"))
