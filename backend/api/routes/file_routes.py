from fastapi import APIRouter, Depends, Query
from application.services.project_service import ProjectContext
from api.dependencies import require_project_permission

router = APIRouter(prefix="/files", tags=["files"])

@router.get("/list")
def list_files(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    project: ProjectContext = Depends(require_project_permission("knowledge:read"))
):
    from db.file_registry import list_all_files, count_files
    files = list_all_files(project.project_id, project.organization_id, page, page_size)
    total = count_files(project.project_id, project.organization_id)
    return {"status": "success", "page": page, "page_size": page_size, "total": total, "has_more": page * page_size < total, "files": files}

@router.get("/check/{source}")
def check_file(source: str, project: ProjectContext = Depends(require_project_permission("knowledge:read"))):
    from db.file_registry import get_file_by_source
    result = get_file_by_source(source, project.project_id, project.organization_id)
    return {"exists": bool(result), **({"file": result} if result else {})}

@router.delete("/{source:path}")
def delete_file(source: str, project: ProjectContext = Depends(require_project_permission("knowledge:delete"))):
    from db.chroma import chroma_delete_by_source
    from db.file_registry import delete_file_by_source
    # Graph cleanup
    neo4j_res = delete_file_by_source(source, project.project_id, project.organization_id)
    # Vector cleanup
    chroma_res = chroma_delete_by_source(source, project.project_id, project.organization_id)
    if chroma_res.get("status") != "success":
        return {"status": "partial_cleanup", "neo4j": neo4j_res, "chroma": chroma_res}
    return {"status": "success", "neo4j": neo4j_res, "chroma": chroma_res}
