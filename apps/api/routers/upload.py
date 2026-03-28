"""ReelForge API — Upload router with resumable upload support."""

import os
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import User, MediaItem, MediaType, MediaStatus
from shared.schemas import UploadInitiateRequest, UploadInitiateResponse, MediaItemResponse
from apps.api.services.auth import get_current_user, get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed file types
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
ALLOWED_TYPES = ALLOWED_VIDEO_TYPES | ALLOWED_IMAGE_TYPES

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")


@router.post("/upload/initiate", response_model=UploadInitiateResponse)
async def initiate_upload(
    request: UploadInitiateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate a resumable upload session.

    Returns a media_item_id and upload URL for the tus protocol.
    """
    if request.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {request.content_type}. Allowed: mp4, mov, jpg, png, webp, heic",
        )

    # Determine media type
    media_type = MediaType.VIDEO if request.content_type in ALLOWED_VIDEO_TYPES else MediaType.PHOTO

    # Create media item record
    media_item = MediaItem(
        user_id=user.id,
        type=media_type,
        filename=request.filename,
        size_bytes=request.file_size,
        status=MediaStatus.UPLOADING,
    )
    db.add(media_item)
    await db.commit()
    await db.refresh(media_item)

    upload_id = str(uuid.uuid4())
    upload_url = f"/api/v1/upload/{upload_id}"

    logger.info(f"Upload initiated: {media_item.id} ({request.filename}, {request.content_type})")

    return UploadInitiateResponse(
        upload_id=upload_id,
        media_item_id=media_item.id,
        upload_url=upload_url,
    )


@router.post("/upload/direct", response_model=MediaItemResponse)
async def direct_upload(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Direct file upload (non-resumable, for smaller files).

    For large files, use the tus resumable upload protocol via /upload/initiate.
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}",
        )

    media_type = MediaType.VIDEO if file.content_type in ALLOWED_VIDEO_TYPES else MediaType.PHOTO

    # Save file locally
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "upload")[1] or (".mp4" if media_type == MediaType.VIDEO else ".jpg")
    local_filename = f"{file_id}{ext}"
    local_path = os.path.join(UPLOAD_DIR, str(user.id), local_filename)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    content = await file.read()
    with open(local_path, "wb") as f:
        f.write(content)

    # Create media item
    media_item = MediaItem(
        user_id=user.id,
        type=media_type,
        filename=file.filename or local_filename,
        size_bytes=len(content),
        status=MediaStatus.UPLOADED,
        r2_key=f"uploads/{user.id}/{local_filename}",
    )
    db.add(media_item)
    await db.commit()
    await db.refresh(media_item)

    logger.info(f"Direct upload complete: {media_item.id} ({file.filename})")

    return MediaItemResponse(
        id=media_item.id,
        type=media_item.type.value,
        filename=media_item.filename,
        size_bytes=media_item.size_bytes,
        status=media_item.status.value,
        created_at=media_item.created_at,
    )
