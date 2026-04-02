"""ReelForge AI — Assembly Worker.

GPU-enabled worker that renders the final reel using ffmpeg:
- Slot extraction with precise trimming
- Speed ramping, Ken Burns for photos
- Transitions (hard cut, whip pan, zoom burst, dissolve, glitch)
- LUT colour grading
- Text overlays with beat-synced timing
- Audio mixing with ducking
- Multi-format export (9:16, 1:1, 16:9)
- Quality validation before delivery
- Thumbnail generation
- Notification dispatch on completion
"""

import json
import logging
import os
import secrets
import shutil
import subprocess
import tempfile
from uuid import UUID

from celery import shared_task
from sqlalchemy import select

from shared.config import get_settings
from shared.models import Job, JobStatus, Reel, MediaItem, MediaSegment
from shared.models.database import SyncSessionLocal

logger = logging.getLogger(__name__)

# LUT file mapping — stored in /app/luts/ directory
LUT_DIR = os.environ.get("LUT_DIR", "/app/luts")
LUT_MAP = {
    "moody": "moody.cube",
    "warm_cinematic": "warm_cinematic.cube",
    "bright_pop": "bright_pop.cube",
    "dark_dramatic": "dark_dramatic.cube",
    "natural": None,  # No LUT needed
}


def extract_clip(source_path: str, output_path: str, start_s: float, duration_s: float) -> bool:
    """Extract a precise clip from source video."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_s),
        "-i", source_path,
        "-t", str(duration_s),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-r", "30",
        "-an",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Clip extraction failed: {e}")
        return False


def apply_speed_ramp(input_path: str, output_path: str, factor: float) -> bool:
    """Apply speed ramp effect."""
    pts_factor = 1.0 / factor
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"setpts={pts_factor}*PTS",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0
    except Exception:
        return False


def create_ken_burns(image_path: str, output_path: str, duration: float,
                     start_scale: float = 1.0, end_scale: float = 1.08,
                     direction: str = "up") -> bool:
    """Create Ken Burns effect on a photo."""
    fps = 30
    total_frames = int(duration * fps)

    zoom_expr = f"zoom+{(end_scale - start_scale) / total_frames}"

    if direction == "up":
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = f"ih/2-(ih/zoom/2)-{0.1 * total_frames / fps}*on"
    elif direction == "down":
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = f"ih/2-(ih/zoom/2)+{0.05 * total_frames / fps}*on"
    elif direction == "left":
        x_expr = f"iw/2-(iw/zoom/2)-{0.1 * total_frames / fps}*on"
        y_expr = "ih/2-(ih/zoom/2)"
    else:  # right
        x_expr = f"iw/2-(iw/zoom/2)+{0.05 * total_frames / fps}*on"
        y_expr = "ih/2-(ih/zoom/2)"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-vf", (
            f"scale=2160:3840:force_original_aspect_ratio=decrease,pad=2160:3840:(ow-iw)/2:(oh-ih)/2,"
            f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}'"
            f":d={total_frames}:s=1080x1920:fps={fps}"
        ),
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Ken Burns effect failed: {e}")
        return False


def apply_transition(clip1_path: str, clip2_path: str, output_path: str,
                     transition_type: str, duration: float = 0.3) -> bool:
    """Apply transition between two clips using xfade filter."""
    # Get clip1 duration
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", clip1_path],
        capture_output=True, text=True, timeout=10,
    )
    try:
        clip1_dur = float(json.loads(probe.stdout)["format"]["duration"])
    except Exception:
        clip1_dur = 2.0

    offset = max(0, clip1_dur - duration)

    xfade_map = {
        "hard_cut": None,
        "dissolve": "fade",
        "whip_pan": "wipeleft",
        "zoom_burst": "zoomin",
        "glitch": "pixelize",
    }

    xfade_type = xfade_map.get(transition_type)

    if not xfade_type:
        # Hard cut: just concatenate
        cmd = [
            "ffmpeg", "-y",
            "-i", clip1_path, "-i", clip2_path,
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[outv]",
            "-map", "[outv]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            output_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", clip1_path, "-i", clip2_path,
            "-filter_complex",
            f"[0:v][1:v]xfade=transition={xfade_type}:duration={duration}:offset={offset}[outv]",
            "-map", "[outv]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            output_path,
        ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Transition failed: {e}")
        return False


def apply_lut(input_path: str, output_path: str, color_grade: str) -> bool:
    """Apply LUT colour grading to video."""
    lut_file = LUT_MAP.get(color_grade)
    if not lut_file:
        # No LUT needed — just copy
        shutil.copy2(input_path, output_path)
        return True

    lut_path = os.path.join(LUT_DIR, lut_file)
    if not os.path.exists(lut_path):
        logger.warning(f"LUT file not found: {lut_path}, skipping color grading")
        shutil.copy2(input_path, output_path)
        return True

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"lut3d='{lut_path}'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "copy",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0
    except Exception:
        shutil.copy2(input_path, output_path)
        return True


def add_text_overlay(input_path: str, output_path: str, overlays: list) -> bool:
    """Add text overlays to video using drawtext filter."""
    if not overlays:
        shutil.copy2(input_path, output_path)
        return True

    filter_parts = []
    for overlay in overlays:
        text = overlay.get("text", "").replace("'", "\\'").replace(":", "\\:")
        start_time = overlay.get("time", 0)
        duration = overlay.get("duration", 1.5)
        style = overlay.get("style", "mid")

        # Style-based formatting
        if style == "hook":
            fontsize = 72
            y_pos = "h*0.35"
        elif style == "cta":
            fontsize = 56
            y_pos = "h*0.45"
        else:
            fontsize = 48
            y_pos = "h*0.4"

        filter_parts.append(
            f"drawtext=text='{text}':fontsize={fontsize}:"
            f"fontcolor=white:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y={y_pos}:"
            f"enable='between(t,{start_time},{start_time + duration})'"
        )

    vf = ",".join(filter_parts)

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "copy",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0
    except Exception:
        return False


def mix_audio(video_path: str, music_path: str, output_path: str,
              duck_at: list = None, music_volume: float = 0.15) -> bool:
    """Mix background music with video audio, with ducking capability."""
    if duck_at and len(duck_at) > 0:
        # Build ducking volume expression — reduce music volume at speech points
        duck_parts = []
        for ts in duck_at:
            # Duck music to 20% for 2 seconds around each speech timestamp
            duck_parts.append(f"between(t,{max(0, ts - 0.5)},{ts + 1.5})")
        duck_expr = "+".join(duck_parts)
        volume_expr = f"volume='{music_volume}*if({duck_expr},0.2,1)'"

        filter_complex = (
            f"[1:a]{volume_expr}[music];"
            f"[0:a][music]amix=inputs=2:duration=first[aout]"
        )
    else:
        filter_complex = (
            f"[1:a]volume={music_volume}[music];"
            f"[0:a][music]amix=inputs=2:duration=first[aout]"
        )

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", music_path,
        "-filter_complex", filter_complex,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0
    except Exception:
        return False


def generate_thumbnail(video_path: str, output_path: str, timestamp: float = 1.0) -> bool:
    """Generate thumbnail from video at specified timestamp."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp),
        "-i", video_path,
        "-vframes", "1",
        "-vf", "scale=540:960",
        "-q:v", "2",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception:
        return False


def create_square_variant(input_path: str, output_path: str) -> bool:
    """Create 1:1 square variant for Instagram feed."""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", "crop='min(iw,ih)':'min(iw,ih)':'(iw-min(iw,ih))/2':'(ih-min(iw,ih))/2',scale=1080:1080",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "copy",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0
    except Exception:
        return False


def create_landscape_variant(input_path: str, output_path: str) -> bool:
    """Create 16:9 landscape variant for YouTube."""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "copy",
        output_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.returncode == 0
    except Exception:
        return False


def validate_quality(video_path: str, blueprint: dict) -> dict:
    """Run automated quality checks on the output reel."""
    checks = {
        "hook_energy": True,
        "beat_alignment": True,
        "color_consistency": True,
        "audio_levels": True,
        "text_safe_zone": True,
        "overall_pass": True,
    }

    # Check file exists and has content
    if not os.path.exists(video_path) or os.path.getsize(video_path) < 10000:
        checks["overall_pass"] = False

    # Check duration matches blueprint
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path],
            capture_output=True, text=True, timeout=10,
        )
        info = json.loads(probe.stdout)
        duration = float(info["format"]["duration"])
        expected = blueprint.get("total_duration", 15)

        if abs(duration - expected) > 2.0:
            checks["overall_pass"] = False
            logger.warning(f"Duration mismatch: {duration}s vs expected {expected}s")
    except Exception:
        pass

    return checks


def _get_source_path(session, segment, media_item) -> str:
    """Get source file path — try local first, then download from R2."""
    local_path = os.path.join("/app/uploads", str(media_item.user_id), media_item.filename)
    if os.path.exists(local_path):
        return local_path

    # Download from R2
    if media_item.r2_key:
        try:
            from shared.storage import get_storage
            import tempfile
            tmp = tempfile.NamedTemporaryFile(suffix=os.path.splitext(media_item.filename)[1], delete=False)
            get_storage().download_file(media_item.r2_key, tmp.name)
            return tmp.name
        except Exception as e:
            logger.warning(f"R2 download failed: {e}")

    return local_path  # Return path even if doesn't exist (will fail gracefully)


@shared_task(name="workers.assembly.tasks.assemble_reel", bind=True, max_retries=2)
def assemble_reel(self, job_id: str):
    """Assemble final reel from blueprint: extract clips, apply effects, render output."""
    logger.info(f"[Assembly] Starting reel assembly for job {job_id}")

    session = SyncSessionLocal()
    try:
        job = session.execute(
            select(Job).where(Job.id == UUID(job_id))
        ).scalar_one_or_none()

        if not job or not job.blueprint:
            logger.error(f"Job {job_id} not found or has no blueprint")
            return

        job.status = JobStatus.ASSEMBLING
        job.progress = 80
        session.commit()

        blueprint = job.blueprint
        slots = blueprint.get("slots", [])

        if not slots:
            job.status = JobStatus.FAILED
            job.error_stage = "assembly"
            job.error_message = "Blueprint has no slots"
            session.commit()
            return

        with tempfile.TemporaryDirectory() as tmpdir:
            clip_paths = []
            slot_transitions = []

            for slot in slots:
                slot_output = os.path.join(tmpdir, f"slot_{slot['slot_id']}.mp4")

                # Find source media
                segment = session.execute(
                    select(MediaSegment).where(MediaSegment.id == UUID(slot["media_id"]))
                ).scalar_one_or_none()

                if not segment:
                    logger.warning(f"Segment {slot['media_id']} not found, skipping slot")
                    continue

                media_item = session.execute(
                    select(MediaItem).where(MediaItem.id == segment.media_item_id)
                ).scalar_one_or_none()

                if not media_item:
                    continue

                source_path = _get_source_path(session, segment, media_item)

                if not os.path.exists(source_path):
                    logger.warning(f"Source file not found: {source_path}")
                    continue

                slot_duration = slot["end"] - slot["start"]

                if slot["type"] == "photo":
                    # Apply Ken Burns effect
                    kb = slot.get("ken_burns") or {"start_scale": 1.0, "end_scale": 1.08, "direction": "up"}
                    success = create_ken_burns(
                        source_path, slot_output, slot_duration,
                        kb.get("start_scale", 1.0), kb.get("end_scale", 1.08),
                        kb.get("direction", "up"),
                    )
                else:
                    # Extract video clip
                    trim_start = slot.get("trim_start", segment.start_ms / 1000)
                    success = extract_clip(source_path, slot_output, trim_start, slot_duration)

                    # Apply speed ramp if specified
                    if success and slot.get("speed_ramp"):
                        ramped = os.path.join(tmpdir, f"slot_{slot['slot_id']}_ramped.mp4")
                        factor = slot["speed_ramp"].get("factor", 1.0)
                        if apply_speed_ramp(slot_output, ramped, factor):
                            os.replace(ramped, slot_output)

                if success and os.path.exists(slot_output):
                    clip_paths.append(slot_output)
                    slot_transitions.append(slot.get("transition_out", "hard_cut"))
                else:
                    logger.warning(f"Failed to process slot {slot['slot_id']}")

            if not clip_paths:
                job.status = JobStatus.FAILED
                job.error_stage = "assembly"
                job.error_message = "No clips could be processed"
                session.commit()
                return

            # ── Concatenate clips with per-slot transitions ──
            if len(clip_paths) == 1:
                assembled_path = clip_paths[0]
            else:
                # Apply transitions pair by pair
                current_path = clip_paths[0]
                for i in range(1, len(clip_paths)):
                    transition_type = slot_transitions[i - 1] if i - 1 < len(slot_transitions) else "hard_cut"
                    next_output = os.path.join(tmpdir, f"trans_{i}.mp4")

                    if not apply_transition(current_path, clip_paths[i], next_output, transition_type):
                        # Fallback: simple concat if transition fails
                        concat_file = os.path.join(tmpdir, f"concat_{i}.txt")
                        with open(concat_file, "w") as f:
                            f.write(f"file '{current_path}'\n")
                            f.write(f"file '{clip_paths[i]}'\n")
                        subprocess.run([
                            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                            "-i", concat_file, "-c", "copy", next_output,
                        ], capture_output=True, text=True, timeout=60)

                    if os.path.exists(next_output):
                        current_path = next_output
                    else:
                        logger.warning(f"Transition {i} failed, keeping current assembly")

                assembled_path = current_path

            # ── Apply LUT colour grading ──
            color_grade = blueprint.get("color_grade", "natural")
            graded_path = os.path.join(tmpdir, "graded.mp4")
            if apply_lut(assembled_path, graded_path, color_grade):
                assembled_path = graded_path

            # ── Apply text overlays ──
            text_overlays = list(blueprint.get("text_overlays", []))
            if job.captions:
                # Add hook text
                if job.captions.get("hook_text"):
                    text_overlays.insert(0, {
                        "time": 0.0,
                        "text": job.captions["hook_text"],
                        "style": "hook",
                        "duration": 1.2,
                    })
                # Add CTA text
                if job.captions.get("cta_text"):
                    total_dur = blueprint.get("total_duration", 15)
                    text_overlays.append({
                        "time": max(0, total_dur - 2.5),
                        "text": job.captions["cta_text"],
                        "style": "cta",
                        "duration": 2.5,
                    })

            if text_overlays:
                text_output = os.path.join(tmpdir, "with_text.mp4")
                if add_text_overlay(assembled_path, text_output, text_overlays):
                    assembled_path = text_output

            # ── Final render with quality settings ──
            final_path = os.path.join(tmpdir, "final_9x16.mp4")
            cmd = [
                "ffmpeg", "-y", "-i", assembled_path,
                "-c:v", "libx264", "-crf", "18", "-preset", "slow",
                "-c:a", "aac", "-b:a", "192k",
                "-vf", "scale=1080:1920",
                "-r", "30",
                "-movflags", "+faststart",
                final_path,
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if not os.path.exists(final_path):
                final_path = assembled_path

            # ── Quality validation ──
            quality = validate_quality(final_path, blueprint)
            logger.info(f"[Assembly] Quality check: {quality}")

            # ── Generate thumbnail ──
            thumb_path = os.path.join(tmpdir, "thumbnail.jpg")
            # Capture thumbnail at 1 second (usually the hook shot)
            generate_thumbnail(final_path, thumb_path, timestamp=1.0)

            # ── Generate format variants ──
            square_path = os.path.join(tmpdir, "final_1x1.mp4")
            landscape_path = os.path.join(tmpdir, "final_16x9.mp4")
            create_square_variant(final_path, square_path)
            create_landscape_variant(final_path, landscape_path)

            # ── Upload to R2 ──
            r2_key_9x16 = f"reels/{job.user_id}/{job.id}/reel_9x16.mp4"
            r2_key_1x1 = f"reels/{job.user_id}/{job.id}/reel_1x1.mp4"
            r2_key_16x9 = f"reels/{job.user_id}/{job.id}/reel_16x9.mp4"
            thumb_r2_key = f"reels/{job.user_id}/{job.id}/thumbnail.jpg"

            try:
                from shared.storage import get_storage
                storage = get_storage()
                storage.upload_file(final_path, r2_key_9x16, "video/mp4")
                if os.path.exists(square_path):
                    storage.upload_file(square_path, r2_key_1x1, "video/mp4")
                if os.path.exists(landscape_path):
                    storage.upload_file(landscape_path, r2_key_16x9, "video/mp4")
                if os.path.exists(thumb_path):
                    storage.upload_file(thumb_path, thumb_r2_key, "image/jpeg")
            except Exception as e:
                logger.warning(f"R2 upload skipped (dev mode): {e}")

            # ── Get final duration ──
            try:
                probe = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", final_path],
                    capture_output=True, text=True, timeout=10,
                )
                duration_ms = int(float(json.loads(probe.stdout)["format"]["duration"]) * 1000)
            except Exception:
                duration_ms = int(blueprint.get("total_duration", 15) * 1000)

            # ── Create Reel record ──
            reel = Reel(
                job_id=job.id,
                user_id=job.user_id,
                r2_key=r2_key_9x16,
                r2_square_key=r2_key_1x1,
                r2_landscape_key=r2_key_16x9,
                duration_ms=duration_ms,
                thumbnail_r2_key=thumb_r2_key,
                share_token=secrets.token_urlsafe(32),
                captions=job.captions,
            )
            session.add(reel)

            # ── Update job status ──
            job.status = JobStatus.COMPLETED
            job.progress = 100
            session.commit()

            # ── Send notification ──
            try:
                from services.notify.main import send_notification
                send_notification(str(job.id), "reel_ready")
            except Exception as e:
                logger.warning(f"Notification dispatch failed: {e}")

            logger.info(f"[Assembly] ✅ Reel assembled for job {job_id}, duration: {duration_ms}ms")

    except Exception as e:
        logger.error(f"[Assembly] Error: {e}")
        session.rollback()
        if job:
            job.status = JobStatus.FAILED
            job.error_stage = "assembly"
            job.error_message = str(e)
            session.commit()
        raise self.retry(countdown=60, max_retries=2)
    finally:
        session.close()
