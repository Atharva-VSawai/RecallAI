from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    try:
        from db.neo import _driver
        _driver.verify_connectivity()
    except Exception:
        return {"status": "degraded", "api": "running", "neo4j": "unavailable"}
    return {"status": "running", "api": "running", "neo4j": "running"}
