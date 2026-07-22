"""
Folder management router.
"""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from packages.database.connection import get_db
from packages.database.models import User, Folder, Project
from app.security.dependencies import get_current_user
from app.schemas import (
    FolderCreateRequest,
    FolderUpdateRequest,
    FolderResponse,
    MessageDetail,
)

router = APIRouter(tags=["Folders"])


@router.post(
    "/projects/{project_id}/folders",
    response_model=FolderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a folder",
)
async def create_folder(
    project_id: UUID,
    body: FolderCreateRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> FolderResponse:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    folder = Folder(
        id=uuid4(),
        project_id=project.id,
        name=body.name,
        color=body.color,
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return FolderResponse.model_validate(folder)


@router.get(
    "/projects/{project_id}/folders",
    response_model=list[FolderResponse],
    summary="List folders in a project",
)
async def list_folders(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[FolderResponse]:
    folders = (
        db.query(Folder)
        .filter(Folder.project_id == project_id)
        .order_by(Folder.is_pinned.desc(), Folder.created_at.desc())
        .all()
    )
    return [FolderResponse.model_validate(f) for f in folders]


@router.patch(
    "/folders/{folder_id}",
    response_model=FolderResponse,
    summary="Update a folder",
)
async def update_folder(
    folder_id: UUID,
    body: FolderUpdateRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> FolderResponse:
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(folder, field, value)

    db.commit()
    db.refresh(folder)
    return FolderResponse.model_validate(folder)


@router.delete(
    "/folders/{folder_id}",
    response_model=MessageDetail,
    summary="Delete a folder",
)
async def delete_folder(
    folder_id: UUID,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> MessageDetail:
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    db.delete(folder)
    db.commit()
    return MessageDetail(message="Folder deleted successfully")
