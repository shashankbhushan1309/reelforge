"""Pydantic request/response schemas."""

from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr, Field




class UserResponse(BaseModel):
    id: UUID
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    locale: str = "en"
    timezone: str = "UTC"
    tier: str = "free"
    credits_remaining: int = 3
    created_at: datetime

    class Config:
        from_attributes = True




class UploadInitiateRequest(BaseModel):
    filename: str
    file_size: int
    content_type: str


class UploadInitiateResponse(BaseModel):
    media_id: str
    upload_url: str




class CloneJobRequest(BaseModel):
    inspiration_media_id: UUID
    user_media_ids: list[UUID]


class AutoJobRequest(BaseModel):
    media_ids: list[UUID]
    niche: Optional[str] = None
    style_preference: Optional[str] = None
    region: Optional[str] = None


class JobResponse(BaseModel):
    id: UUID
    mode: str
    status: str
    progress: int = 0
    error_stage: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobDetailResponse(JobResponse):
    reel_id: Optional[UUID] = None
    style_dna: Optional[dict] = None
    blueprint: Optional[dict] = None
    captions: Optional[dict] = None


class BlueprintSlot(BaseModel):
    slot_id: int
    start: float
    end: float
    type: str
    media_id: Optional[str] = None
    trim_start: Optional[float] = None
    trim_end: Optional[float] = None
    transition_out: str = "hard_cut"
    ken_burns: Optional[dict] = None
    speed_ramp: Optional[dict] = None
    mood_role: str = "build"


class BlueprintResponse(BaseModel):
    total_duration: float
    slots: list[BlueprintSlot]
    color_grade: str
    text_overlays: list[dict] = []
    creative_rationale: str = ""




class ReelResponse(BaseModel):
    id: UUID
    job_id: UUID
    r2_key: Optional[str] = None
    r2_square_key: Optional[str] = None
    r2_landscape_key: Optional[str] = None
    duration_ms: Optional[int] = None
    thumbnail_url: Optional[str] = None
    share_token: Optional[str] = None
    view_count: int = 0
    download_count: int = 0
    captions: Optional[dict] = None
    download_url: Optional[str] = None
    square_download_url: Optional[str] = None
    landscape_download_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RegenerateRequest(BaseModel):
    regeneration_number: int = 1




class MediaItemResponse(BaseModel):
    id: UUID
    type: str
    filename: str
    duration_ms: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: Optional[int] = None
    status: str
    mood_tags: list[str] = []
    thumbnail_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MediaSegmentResponse(BaseModel):
    id: UUID
    media_item_id: UUID
    start_ms: int
    end_ms: int
    composite_score: Optional[float] = None
    quality_scores: dict = {}
    mood_tag: Optional[str] = None
    face_detected: bool = False
    camera_motion: Optional[str] = None
    color_temp: Optional[str] = None

    class Config:
        from_attributes = True




class TrendProfileResponse(BaseModel):
    id: UUID
    niche: str
    trend_name: str
    region: str
    bpm_min: Optional[int] = None
    bpm_max: Optional[int] = None
    color_palette: list[str] = []
    transition_style: Optional[str] = None
    text_style: Optional[str] = None
    energy_level: Optional[int] = None
    virality_score: Optional[float] = None
    estimated_virality_days: Optional[int] = None
    audio_description: Optional[str] = None
    visual_description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True




class StyleDNATemplateCreate(BaseModel):
    name: str
    job_id: Optional[UUID] = None
    is_public: bool = False


class StyleDNATemplateResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    name: str
    is_public: bool
    cut_pace: Optional[str] = None
    color_grade: Optional[str] = None
    transition_type: Optional[str] = None
    text_energy: Optional[str] = None
    bpm: Optional[int] = None
    visual_motion: Optional[str] = None
    color_temperature: Optional[str] = None
    usage_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True




class PaginatedResponse(BaseModel):
    items: list = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    pages: int = 1




class ShotInstruction(BaseModel):
    shot_number: int
    duration_seconds: int
    title: str
    what_to_film: str
    how_to_film_it: str
    why_it_matters: str
    common_mistake: str
    type: str = "video"


class ShotDirectorResponse(BaseModel):
    shots: list[ShotInstruction]
