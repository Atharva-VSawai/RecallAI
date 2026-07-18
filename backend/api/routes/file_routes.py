from fastapi import APIRouter, Depends
from application.services.auth_service import AuthenticatedUser
from api.dependencies import get_current_user

router = APIRouter(prefix="/files", tags=["files"])

@router.get("/list")
def list_files(_: AuthenticatedUser = Depends(get_current_user)):
    from db.file_registry import list_all_files
    return {"status": "success", "files": list_all_files()}

@router.get("/check/{source}")
def check_file(source: str, _: AuthenticatedUser = Depends(get_current_user)):
    from db.file_registry import get_file_by_source
    result = get_file_by_source(source)
    return {"exists": bool(result), **({"file": result} if result else {})}

@router.delete("/{source:path}")
def delete_file(source: str, _: AuthenticatedUser = Depends(get_current_user)):
    from db.chroma import chroma_delete_by_source
    from db.file_registry import delete_file_by_source
    return {"status": "success", "neo4j": delete_file_by_source(source), "chroma": chroma_delete_by_source(source)}
