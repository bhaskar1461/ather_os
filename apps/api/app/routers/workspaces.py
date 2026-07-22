"""
Workspace and Project management router.
"""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from packages.database.connection import get_db
from packages.database.models import User, Workspace, Project
from app.security.dependencies import get_current_user
from app.schemas import (
    WorkspaceCreateRequest,
    WorkspaceResponse,
    ProjectCreateRequest,
    ProjectResponse,
    MessageDetail,
)

router = APIRouter(tags=["Workspaces"])


# ── Workspaces ────────────────────────────────────────────────────────────────

@router.post(
    "/workspaces",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
)
async def create_workspace(
    body: WorkspaceCreateRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> WorkspaceResponse:
    workspace = Workspace(
        id=uuid4(),
        owner_id=user.id,
        name=body.name,
        description=body.description,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return WorkspaceResponse.model_validate(workspace)


@router.get(
    "/workspaces",
    response_model=list[WorkspaceResponse],
    summary="List all workspaces for the current user",
)
async def list_workspaces(
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[WorkspaceResponse]:
    workspaces = (
        db.query(Workspace)
        .filter(Workspace.owner_id == user.id)
        .order_by(Workspace.created_at.desc())
        .all()
    )
    if not workspaces:
        ws_id = uuid4()
        default_ws = Workspace(
            id=ws_id,
            owner_id=user.id,
            name="My Workspace",
            description="Default workspace created automatically.",
        )
        db.add(default_ws)
        
        default_proj = Project(
            id=uuid4(),
            workspace_id=ws_id,
            name="Default Project",
            description="Default project created automatically.",
        )
        db.add(default_proj)
        
        db.commit()
        db.refresh(default_ws)
        workspaces = [default_ws]

    return [WorkspaceResponse.model_validate(w) for w in workspaces]


@router.get(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Get a specific workspace",
)
async def get_workspace(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> WorkspaceResponse:
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.owner_id == user.id)
        .first()
    )
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return WorkspaceResponse.model_validate(workspace)


@router.delete(
    "/workspaces/{workspace_id}",
    response_model=MessageDetail,
    summary="Delete a workspace and all its contents",
)
async def delete_workspace(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> MessageDetail:
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.owner_id == user.id)
        .first()
    )
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    db.delete(workspace)
    db.commit()
    return MessageDetail(message="Workspace deleted successfully")


# ── Projects ──────────────────────────────────────────────────────────────────

@router.post(
    "/workspaces/{workspace_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project within a workspace",
)
async def create_project(
    workspace_id: UUID,
    body: ProjectCreateRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> ProjectResponse:
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.owner_id == user.id)
        .first()
    )
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    project = Project(
        id=uuid4(),
        workspace_id=workspace.id,
        name=body.name,
        description=body.description,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.get(
    "/workspaces/{workspace_id}/projects",
    response_model=list[ProjectResponse],
    summary="List projects in a workspace",
)
async def list_projects(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[ProjectResponse]:
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.owner_id == user.id)
        .first()
    )
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    projects = (
        db.query(Project)
        .filter(Project.workspace_id == workspace_id)
        .order_by(Project.created_at.desc())
        .all()
    )
    if not projects:
        default_proj = Project(
            id=uuid4(),
            workspace_id=workspace.id,
            name="Default Project",
            description="Default project created automatically.",
        )
        db.add(default_proj)
        db.commit()
        db.refresh(default_proj)
        projects = [default_proj]

    return [ProjectResponse.model_validate(p) for p in projects]


@router.delete(
    "/workspaces/{workspace_id}/projects/{project_id}",
    response_model=MessageDetail,
    summary="Delete a project",
)
async def delete_project(
    workspace_id: UUID,
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> MessageDetail:
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.owner_id == user.id)
        .first()
    )
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.workspace_id == workspace_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    db.delete(project)
    db.commit()
    return MessageDetail(message="Project deleted successfully")
