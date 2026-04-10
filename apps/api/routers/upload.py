"""Upload router — file upload initiation and direct upload."""

import logging
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.services.auth import get_current_user
from shared.config import get_settings
from shared.models import MediaItem, MediaType, MediaStatus, User
from shared.models.database import get_async_session as get_db
from shared.schemas import UploadInitiateRequest, UploadInitiateResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Supported file types
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm", "video/x-msvideo"}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
ALLOWED_TYPES = ALLOWED_VIDEO_TYPES | ALLOWED_IMAGE_TYPES

# Maximum file size: 1GB
MAX_FILE_SIZE = 1 * 1024 * 1024 * 1024  # 1GB in bytes


def _classify_media_type(content_type: str) -> MediaType:
    """Classify content type into MediaType enum."""
    if content_type in ALLOWED_VIDEO_TYPES:
        return MediaType.VIDEO
    return MediaType.PHOTO


@router.post("/upload/initiate", response_model=UploadInitiateResponse)
async def initiate_upload(
    request: UploadInitiateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate a resumable upload. Returns upload URL for tus client."""
    # Validate content type
    if request.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {request.content_type}. Allowed: MP4, MOV, WEBM, JPG, PNG, WEBP, HEIC",
        )

    # Validate file size
    if request.file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is 1GB ({MAX_FILE_SIZE} bytes).",
        )

    # Create MediaItem record
    media_type = _classify_media_type(request.content_type)
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

    # In production, return a pre-signed R2 URL or tus endpoint
    settings = get_settings()
    upload_url = f"/api/v1/upload/tus/{media_item.id}"

    logger.info(f"Upload initiated: {media_item.id} ({request.filename}, {request.file_size} bytes)")

    return UploadInitiateResponse(
        media_id=str(media_item.id),
        upload_url=upload_url,
    )


@router.post("/upload/direct")
async def direct_upload(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Direct file upload (non-resumable). For smaller files."""
    # Validate content type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}",
        )

    # Read file and check size
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 1GB.",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded.",
        )

    # Generate unique filename
    ext = os.path.splitext(file.filename or "file")[1] or ".bin"
    unique_filename = f"{uuid.uuid4().hex}{ext}"

    # Save to local uploads directory (in dev) or R2 (in prod)
    upload_dir = os.path.join("/app/uploads", str(user.id))
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, unique_filename)

    with open(filepath, "wb") as f:
        f.write(content)

    # Create MediaItem record in DB
    media_type = _classify_media_type(file.content_type)
    media_item = MediaItem(
        user_id=user.id,
        type=media_type,
        filename=unique_filename,
        size_bytes=file_size,
        status=MediaStatus.UPLOADED,
    )
    db.add(media_item)
    await db.commit()
    await db.refresh(media_item)

    # Upload to R2 in production
    r2_key = f"uploads/{user.id}/{media_item.id}/{unique_filename}"
    try:
        from shared.storage import get_storage
        storage = get_storage()
        storage.upload_file(filepath, r2_key, file.content_type)
        media_item.r2_key = r2_key
        await db.commit()
    except Exception as e:
        logger.warning(f"R2 upload skipped (dev mode): {e}")
        media_item.r2_key = r2_key
        await db.commit()

    logger.info(f"Direct upload complete: {media_item.id} ({file.filename}, {file_size} bytes)")

    return {
        "media_id": str(media_item.id),
        "filename": unique_filename,
        "type": media_type.value,
        "size_bytes": file_size,
        "status": media_item.status.value,
    }
