from fastapi import APIRouter, Depends

from api.dependencies import get_current_user, get_project_context
from application.services.auth_service import AuthenticatedUser
from application.services.project_service import ProjectContext, ProjectService
from schemas.requests import CreateProjectRequest

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
def list_projects(user: AuthenticatedUser = Depends(get_current_user)):
    return {"status": "success", "projects": ProjectService().list_projects(user)}


@router.get("/active")
def active_project(project: ProjectContext = Depends(get_project_context)):
    return {"status": "success", "project": project.__dict__}


@router.post("")
def create_project(request: CreateProjectRequest, user: AuthenticatedUser = Depends(get_current_user)):
    return {"status": "success", "project": ProjectService().create_project(request.name, user)}


@router.delete("/{project_id}")
def delete_project(project_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    return {"status": "success", **ProjectService().delete_project(project_id, user)}
