"""Initial schema — All ReelForge tables

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    # Users
    op.create_table('users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.Text, nullable=True),
        sa.Column('locale', sa.String(10), server_default='en'),
        sa.Column('timezone', sa.String(50), server_default='UTC'),
        sa.Column('tier', sa.String(20), server_default='free', nullable=False),
        sa.Column('credits_remaining', sa.Integer, server_default='3', nullable=False),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('supabase_uid', sa.String(255), unique=True, nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Media Items
    op.create_table('media_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('type', sa.String(10), nullable=False),
        sa.Column('filename', sa.String(512), nullable=False),
        sa.Column('r2_key', sa.Text, nullable=True),
        sa.Column('r2_thumb_key', sa.Text, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('width', sa.Integer, nullable=True),
        sa.Column('height', sa.Integer, nullable=True),
        sa.Column('size_bytes', sa.BigInteger, nullable=True),
        sa.Column('status', sa.String(20), server_default='uploading', nullable=False),
        sa.Column('mood_tags', ARRAY(sa.Text), server_default='{}'),
        sa.Column('metadata', JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Media Segments
    op.create_table('media_segments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('media_item_id', UUID(as_uuid=True), sa.ForeignKey('media_items.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('start_ms', sa.Integer, nullable=False),
        sa.Column('end_ms', sa.Integer, nullable=False),
        sa.Column('composite_score', sa.Float, nullable=True),
        sa.Column('quality_scores', JSONB, server_default='{}'),
        sa.Column('mood_tag', sa.String(50), nullable=True),
        sa.Column('face_detected', sa.Boolean, server_default='false'),
        sa.Column('keyframe_r2_key', sa.Text, nullable=True),
        sa.Column('camera_motion', sa.String(50), nullable=True),
        sa.Column('color_temp', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Trend Profiles
    op.create_table('trend_profiles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('niche', sa.String(100), nullable=False, index=True),
        sa.Column('trend_name', sa.String(255), nullable=False),
        sa.Column('region', sa.String(10), nullable=False, index=True),
        sa.Column('bpm_min', sa.Integer, nullable=True),
        sa.Column('bpm_max', sa.Integer, nullable=True),
        sa.Column('color_palette', ARRAY(sa.Text), server_default='{}'),
        sa.Column('transition_style', sa.String(50), nullable=True),
        sa.Column('text_style', sa.String(50), nullable=True),
        sa.Column('energy_level', sa.Integer, nullable=True),
        sa.Column('virality_score', sa.Float, nullable=True),
        sa.Column('estimated_virality_days', sa.Integer, nullable=True),
        sa.Column('audio_description', sa.Text, nullable=True),
        sa.Column('visual_description', sa.Text, nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('raw_signals', JSONB, server_default='{}'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Jobs
    op.create_table('jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('mode', sa.String(10), nullable=False),
        sa.Column('status', sa.String(30), server_default='queued', nullable=False),
        sa.Column('progress', sa.Integer, server_default='0'),
        sa.Column('inspiration_media_id', UUID(as_uuid=True), sa.ForeignKey('media_items.id'), nullable=True),
        sa.Column('style_dna', JSONB, nullable=True),
        sa.Column('trend_profile_id', UUID(as_uuid=True), sa.ForeignKey('trend_profiles.id'), nullable=True),
        sa.Column('blueprint', JSONB, nullable=True),
        sa.Column('captions', JSONB, nullable=True),
        sa.Column('media_ids', ARRAY(UUID(as_uuid=True)), server_default='{}'),
        sa.Column('niche', sa.String(100), nullable=True),
        sa.Column('region', sa.String(10), nullable=True),
        sa.Column('style_preference', sa.String(100), nullable=True),
        sa.Column('error_stage', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('beat_grid', JSONB, nullable=True),
        sa.Column('audio_analysis', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Reels
    op.create_table('reels',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('job_id', UUID(as_uuid=True), sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('r2_key', sa.Text, nullable=True),
        sa.Column('r2_square_key', sa.Text, nullable=True),
        sa.Column('r2_landscape_key', sa.Text, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('thumbnail_r2_key', sa.Text, nullable=True),
        sa.Column('share_token', sa.String(64), unique=True, nullable=True),
        sa.Column('view_count', sa.Integer, server_default='0'),
        sa.Column('download_count', sa.Integer, server_default='0'),
        sa.Column('captions', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Style DNA Templates
    op.create_table('style_dna_templates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('is_public', sa.Boolean, server_default='false'),
        sa.Column('cut_pace', sa.String(20), nullable=True),
        sa.Column('color_grade', sa.String(50), nullable=True),
        sa.Column('transition_type', sa.String(50), nullable=True),
        sa.Column('text_energy', sa.String(50), nullable=True),
        sa.Column('bpm', sa.Integer, nullable=True),
        sa.Column('visual_motion', sa.String(50), nullable=True),
        sa.Column('color_temperature', sa.String(20), nullable=True),
        sa.Column('full_dna', JSONB, server_default='{}'),
        sa.Column('usage_count', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # Audit Logs
    op.create_table('audit_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=True),
        sa.Column('entity_id', UUID(as_uuid=True), nullable=True),
        sa.Column('metadata', JSONB, server_default='{}'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('style_dna_templates')
    op.drop_table('reels')
    op.drop_table('jobs')
    op.drop_table('trend_profiles')
    op.drop_table('media_segments')
    op.drop_table('media_items')
    op.drop_table('users')
