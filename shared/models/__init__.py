"""ReelForge AI — SQLAlchemy ORM Models.

All tables use UUID v4 primary keys and UTC timestamps.
JSONB columns for flexible metadata storage.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return uuid.uuid4()


# ── Enums ──

import enum


class UserTier(str, enum.Enum):
    FREE = "free"
    CREATOR = "creator"
    PRO = "pro"
    STUDIO = "studio"
    ENTERPRISE = "enterprise"


class MediaType(str, enum.Enum):
    VIDEO = "video"
    PHOTO = "photo"


class MediaStatus(str, enum.Enum):
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class JobMode(str, enum.Enum):
    CLONE = "clone"
    AUTO = "auto"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    INGESTING = "ingesting"
    ANALYSING = "analysing"
    EXTRACTING_DNA = "extracting_dna"
    GENERATING_BLUEPRINT = "generating_blueprint"
    ASSEMBLING = "assembling"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Models ──


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)
    locale = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")
    tier = Column(Enum(UserTier), default=UserTier.FREE, nullable=False)
    credits_remaining = Column(Integer, default=3, nullable=False)
    stripe_customer_id = Column(String(255), nullable=True)
    supabase_uid = Column(String(255), unique=True, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    media_items = relationship("MediaItem", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    reels = relationship("Reel", back_populates="user", cascade="all, delete-orphan")
    dna_templates = relationship("StyleDNATemplate", back_populates="user")


class MediaItem(Base):
    __tablename__ = "media_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(Enum(MediaType), nullable=False)
    filename = Column(String(512), nullable=False)
    r2_key = Column(Text, nullable=True)
    r2_thumb_key = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    status = Column(Enum(MediaStatus), default=MediaStatus.UPLOADING, nullable=False)
    mood_tags = Column(ARRAY(Text), default=list)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="media_items")
    segments = relationship("MediaSegment", back_populates="media_item", cascade="all, delete-orphan")


class MediaSegment(Base):
    __tablename__ = "media_segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    media_item_id = Column(UUID(as_uuid=True), ForeignKey("media_items.id", ondelete="CASCADE"), nullable=False, index=True)
    start_ms = Column(Integer, nullable=False)
    end_ms = Column(Integer, nullable=False)
    composite_score = Column(Float, nullable=True)
    quality_scores = Column(JSONB, default=dict)
    mood_tag = Column(String(50), nullable=True)
    face_detected = Column(Boolean, default=False)
    keyframe_r2_key = Column(Text, nullable=True)
    camera_motion = Column(String(50), nullable=True)
    color_temp = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    media_item = relationship("MediaItem", back_populates="segments")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    mode = Column(Enum(JobMode), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False)
    progress = Column(Integer, default=0)
    inspiration_media_id = Column(UUID(as_uuid=True), ForeignKey("media_items.id"), nullable=True)
    style_dna = Column(JSONB, nullable=True)
    trend_profile_id = Column(UUID(as_uuid=True), ForeignKey("trend_profiles.id"), nullable=True)
    blueprint = Column(JSONB, nullable=True)
    captions = Column(JSONB, nullable=True)
    media_ids = Column(ARRAY(UUID(as_uuid=True)), default=list)
    niche = Column(String(100), nullable=True)
    region = Column(String(10), nullable=True)
    style_preference = Column(String(100), nullable=True)
    error_stage = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    beat_grid = Column(JSONB, nullable=True)
    audio_analysis = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="jobs")
    reel = relationship("Reel", back_populates="job", uselist=False)
    inspiration_media = relationship("MediaItem", foreign_keys=[inspiration_media_id])
    trend_profile = relationship("TrendProfile", foreign_keys=[trend_profile_id])


class Reel(Base):
    __tablename__ = "reels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    r2_key = Column(Text, nullable=True)
    r2_square_key = Column(Text, nullable=True)
    r2_landscape_key = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    thumbnail_r2_key = Column(Text, nullable=True)
    share_token = Column(String(64), unique=True, nullable=True)
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    captions = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    job = relationship("Job", back_populates="reel")
    user = relationship("User", back_populates="reels")


class TrendProfile(Base):
    __tablename__ = "trend_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    niche = Column(String(100), nullable=False, index=True)
    trend_name = Column(String(255), nullable=False)
    region = Column(String(10), nullable=False, index=True)
    bpm_min = Column(Integer, nullable=True)
    bpm_max = Column(Integer, nullable=True)
    color_palette = Column(ARRAY(Text), default=list)
    transition_style = Column(String(50), nullable=True)
    text_style = Column(String(50), nullable=True)
    energy_level = Column(Integer, nullable=True)
    virality_score = Column(Float, nullable=True)
    estimated_virality_days = Column(Integer, nullable=True)
    audio_description = Column(Text, nullable=True)
    visual_description = Column(Text, nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    raw_signals = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class StyleDNATemplate(Base):
    __tablename__ = "style_dna_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    is_public = Column(Boolean, default=False)
    cut_pace = Column(String(20), nullable=True)
    color_grade = Column(String(50), nullable=True)
    transition_type = Column(String(50), nullable=True)
    text_energy = Column(String(50), nullable=True)
    bpm = Column(Integer, nullable=True)
    visual_motion = Column(String(50), nullable=True)
    color_temperature = Column(String(20), nullable=True)
    full_dna = Column(JSONB, default=dict)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="dna_templates")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
