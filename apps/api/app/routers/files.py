"""
File metadata router.
Handles upload metadata registration and file history.
Actual file processing is deferred to future modules.
"""

import os
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile, status
from sqlalchemy.orm import Session as DBSession

from packages.database.connection import get_db
from packages.database.models import User, File
from app.security.dependencies import get_current_user
from app.config import get_settings
from app.schemas import FileResponse, MessageDetail

settings = get_settings()
router = APIRouter(prefix="/files", tags=["Files"])


@router.post(
    "/upload",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file",
)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    chat_id: UUID | None = None,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> FileResponse:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a filename",
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    if file_size > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {settings.max_upload_size_bytes // (1024 * 1024)}MB",
        )

    # Save file to disk
    upload_dir = os.path.join(settings.upload_directory, str(user.id))
    os.makedirs(upload_dir, exist_ok=True)

    file_id = uuid4()
    file_ext = os.path.splitext(file.filename)[1]
    disk_filename = f"{file_id}{file_ext}"
    file_path = os.path.join(upload_dir, disk_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    # Register metadata in database
    file_record = File(
        id=file_id,
        user_id=user.id,
        chat_id=chat_id,
        name=file.filename,
        size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        path=file_path,
        status="completed",
        progress=100,
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    return FileResponse.model_validate(file_record)


@router.get(
    "",
    response_model=list[FileResponse],
    summary="List uploaded files",
)
async def list_files(
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> list[FileResponse]:
    files = (
        db.query(File)
        .filter(File.user_id == user.id)
        .order_by(File.created_at.desc())
        .limit(100)
        .all()
    )
    return [FileResponse.model_validate(f) for f in files]


@router.delete(
    "/{file_id}",
    response_model=MessageDetail,
    summary="Delete a file",
)
async def delete_file(
    file_id: UUID,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> MessageDetail:
    file_record = (
        db.query(File)
        .filter(File.id == file_id, File.user_id == user.id)
        .first()
    )
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Delete from disk if exists
    if os.path.exists(file_record.path):
        os.remove(file_record.path)

    db.delete(file_record)
    db.commit()

    return MessageDetail(message="File deleted successfully")
