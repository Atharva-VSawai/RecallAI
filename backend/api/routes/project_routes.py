from fastapi import APIRouter, Depends

from api.dependencies import get_current_user, get_project_context, require_project_permission
from application.services.auth_service import AuthenticatedUser
from application.services.project_service import ProjectContext, ProjectService
from schemas.requests import CreateProjectRequest, MemberRoleRequest, UpdateProjectRequest
from domain.exceptions import ValidationError

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


@router.post("/init")
def init_default_project(user: AuthenticatedUser = Depends(get_current_user)):
    ProjectService().ensure_default_project(user)
    return {"status": "success"}


@router.delete("/{project_id}")
def delete_project(project_id: str, user: AuthenticatedUser = Depends(get_current_user)):
    return {"status": "success", **ProjectService().delete_project(project_id, user)}


@router.patch("/{project_id}")
def update_project(project_id: str, request: UpdateProjectRequest, user: AuthenticatedUser = Depends(get_current_user)):
    return {"status": "success", "project": ProjectService().update_project(project_id, request.name, user)}


@router.get("/{project_id}/members")
def list_members(project_id: str, project: ProjectContext = Depends(require_project_permission("project:manage"))):
    if project_id != project.project_id:
        raise ValidationError("Project context does not match the requested project")
    return {"status": "success", "members": ProjectService().list_members(project)}


@router.patch("/{project_id}/members/{member_id}")
def update_member(project_id: str, member_id: str, request: MemberRoleRequest, project: ProjectContext = Depends(require_project_permission("project:manage"))):
    if project_id != project.project_id or member_id != request.user_id:
        raise ValidationError("Project context does not match the requested member")
    return {"status": "success", "member": ProjectService().update_member_role(project, member_id, request.role)}


@router.get("/organization/summary")
def organization_summary(user: AuthenticatedUser = Depends(get_current_user)):
    return {"status": "success", "organization": ProjectService().organization_summary(user)}
