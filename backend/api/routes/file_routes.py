from fastapi import APIRouter, Depends
from application.services.project_service import ProjectContext
from api.dependencies import require_project_permission

router = APIRouter(prefix="/files", tags=["files"])

@router.get("/list")
def list_files(project: ProjectContext = Depends(require_project_permission("knowledge:read"))):
    from db.file_registry import list_all_files
    return {"status": "success", "files": list_all_files(project.project_id)}

@router.get("/check/{source}")
def check_file(source: str, project: ProjectContext = Depends(require_project_permission("knowledge:read"))):
    from db.file_registry import get_file_by_source
    result = get_file_by_source(source, project.project_id)
    return {"exists": bool(result), **({"file": result} if result else {})}

@router.delete("/{source:path}")
def delete_file(source: str, project: ProjectContext = Depends(require_project_permission("knowledge:delete"))):
    from db.chroma import chroma_delete_by_source
    from db.file_registry import delete_file_by_source
    return {"status": "success", "neo4j": delete_file_by_source(source, project.project_id), "chroma": chroma_delete_by_source(source, project.project_id)}
