"""Style DNA extraction worker for Clone Mode."""

import json
import logging
import os
import subprocess
import tempfile
from uuid import UUID

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    cv2 = None
    np = None
from celery import shared_task
from sqlalchemy import select

from shared.config import get_settings
from shared.models import MediaItem, Job, JobStatus
from shared.models.database import SyncSessionLocal

logger = logging.getLogger(__name__)


def calculate_cut_pace(scene_count: int, duration_s: float) -> dict:
    """Calculate cut pace from scene count and duration."""
    if duration_s <= 0:
        return {"cuts_per_second": 0, "avg_cut_duration": 0, "label": "slow"}

    cuts_per_second = scene_count / duration_s
    avg_duration = duration_s / max(scene_count, 1)

    if avg_duration < 1.5:
        label = "fast"
    elif avg_duration < 3.0:
        label = "medium"
    else:
        label = "slow"

    return {
        "cuts_per_second": round(cuts_per_second, 3),
        "avg_cut_duration": round(avg_duration, 2),
        "scene_count": scene_count,
        "label": label,
    }


def analyze_color_histogram(video_path: str, num_samples: int = 10) -> dict:
    """Analyze dominant colors using k-means clustering on sampled frames."""
    try:
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        sample_indices = np.linspace(0, total_frames - 1, num_samples, dtype=int)

        all_colors = []
        for idx in sample_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ret, frame = cap.read()
            if ret:
                # Convert to RGB and reshape
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pixels = rgb.reshape(-1, 3).astype(np.float32)
                # Sample pixels for efficiency
                sample_size = min(1000, len(pixels))
                indices = np.random.choice(len(pixels), sample_size, replace=False)
                all_colors.append(pixels[indices])

        cap.release()

        if not all_colors:
            return {"color_grade": "natural", "dominant_colors": [], "color_temperature": "neutral"}

        all_pixels = np.vstack(all_colors)

        # K-means clustering
        from sklearn.cluster import KMeans
        try:
            kmeans = KMeans(n_clusters=5, n_init=10, random_state=42)
            kmeans.fit(all_pixels)
            centers = kmeans.cluster_centers_.astype(int)
        except ImportError:
            # Fallback without sklearn
            centers = np.mean(all_pixels, axis=0).reshape(1, 3).astype(int)

        # Classify color grade
        avg_saturation = np.mean([np.std(c) for c in centers])
        avg_brightness = np.mean(centers)

        if avg_saturation < 30 and avg_brightness < 100:
            color_grade = "moody"
        elif avg_brightness > 180:
            color_grade = "bright_pop"
        elif avg_brightness < 80:
            color_grade = "dark_dramatic"
        elif np.mean(centers[:, 0]) > np.mean(centers[:, 2]):  # R > B
            color_grade = "warm_cinematic"
        else:
            color_grade = "natural"

        # Color temperature
        avg_r = np.mean(centers[:, 0])
        avg_b = np.mean(centers[:, 2])
        if avg_r - avg_b > 30:
            color_temp = "warm"
        elif avg_b - avg_r > 30:
            color_temp = "cool"
        else:
            color_temp = "neutral"

        dominant_colors = [f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}" for c in centers[:5]]

        return {
            "color_grade": color_grade,
            "dominant_colors": dominant_colors,
            "color_temperature": color_temp,
            "avg_saturation": float(avg_saturation),
            "avg_brightness": float(avg_brightness),
        }

    except Exception as e:
        logger.error(f"Color analysis failed: {e}")
        return {"color_grade": "natural", "dominant_colors": [], "color_temperature": "neutral"}


def analyze_optical_flow(video_path: str) -> dict:
    """Analyze camera motion using optical flow."""
    try:
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Sample 5 frame pairs
        sample_points = np.linspace(0, total_frames - 2, 5, dtype=int)
        motion_magnitudes = []

        prev_gray = None
        for idx in sample_points:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ret, frame = cap.read()
            if not ret:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (320, 240))  # Downscale for speed

            if prev_gray is not None:
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, gray, None,
                    pyr_scale=0.5, levels=3, winsize=15,
                    iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
                )
                magnitude = np.mean(np.sqrt(flow[..., 0]**2 + flow[..., 1]**2))
                motion_magnitudes.append(float(magnitude))

            prev_gray = gray

        cap.release()

        avg_motion = np.mean(motion_magnitudes) if motion_magnitudes else 0

        if avg_motion < 1.0:
            motion_type = "static"
        elif avg_motion < 3.0:
            motion_type = "handheld"
        elif avg_motion < 8.0:
            motion_type = "tracking"
        else:
            motion_type = "drone"

        return {
            "motion_type": motion_type,
            "avg_motion_magnitude": round(avg_motion, 3),
        }

    except Exception as e:
        logger.error(f"Optical flow analysis failed: {e}")
        return {"motion_type": "handheld", "avg_motion_magnitude": 0}


def detect_text_overlays(video_path: str) -> dict:
    """Detect text overlays using pytesseract OCR."""
    try:
        import pytesseract
        from PIL import Image

        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30

        sample_indices = np.linspace(0, total_frames - 1, 5, dtype=int)
        text_count = 0
        texts_found = []

        for idx in sample_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ret, frame = cap.read()
            if not ret:
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)

            try:
                text = pytesseract.image_to_string(pil_img).strip()
                if len(text) > 3:  # Filter noise
                    text_count += 1
                    texts_found.append(text[:100])
            except Exception:
                pass

        cap.release()

        duration_s = total_frames / fps
        texts_per_minute = (text_count / duration_s * 60) if duration_s > 0 else 0

        if texts_per_minute > 10:
            energy = "high"
        elif texts_per_minute > 3:
            energy = "medium"
        else:
            energy = "low"

        return {
            "text_energy": energy,
            "texts_per_minute": round(texts_per_minute, 1),
            "text_count": text_count,
            "sample_texts": texts_found[:3],
        }

    except Exception as e:
        logger.error(f"Text detection failed: {e}")
        return {"text_energy": "low", "texts_per_minute": 0, "text_count": 0, "sample_texts": []}


def classify_transitions(video_path: str, scene_boundaries: list) -> dict:
    """Classify transition types using frame-diff analysis."""
    try:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        transitions = []

        for boundary_ms in scene_boundaries[:10]:  # Limit to 10 transitions
            frame_idx = int((boundary_ms / 1000) * fps)

            # Read frames around the boundary
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_idx - 2))
            ret1, before = cap.read()
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx + 2)
            ret2, after = cap.read()

            if ret1 and ret2:
                before_gray = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
                after_gray = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)
                before_gray = cv2.resize(before_gray, (320, 240))
                after_gray = cv2.resize(after_gray, (320, 240))

                diff = cv2.absdiff(before_gray, after_gray)
                mean_diff = np.mean(diff)

                if mean_diff > 100:
                    transitions.append("hard_cut")
                elif mean_diff > 60:
                    transitions.append("whip_pan")
                elif mean_diff > 30:
                    transitions.append("zoom_burst")
                else:
                    transitions.append("dissolve")

        cap.release()

        # Find dominant transition
        from collections import Counter
        if transitions:
            dominant = Counter(transitions).most_common(1)[0][0]
        else:
            dominant = "hard_cut"

        return {
            "dominant_transition": dominant,
            "transitions": transitions,
            "transition_variety": len(set(transitions)),
        }

    except Exception as e:
        logger.error(f"Transition classification failed: {e}")
        return {"dominant_transition": "hard_cut", "transitions": [], "transition_variety": 0}


@shared_task(name="workers.dna.tasks.extract_dna", bind=True, max_retries=3)
def extract_dna(self, job_id: str, media_id: str, mode: str = "clone"):
    """Extract Style DNA from inspiration reel."""
    logger.info(f"[DNA] Extracting Style DNA from media {media_id} for job {job_id}")

    session = SyncSessionLocal()
    try:
        job = session.execute(
            select(Job).where(Job.id == UUID(job_id))
        ).scalar_one_or_none()

        if not job:
            return

        job.status = JobStatus.EXTRACTING_DNA
        job.progress = 30
        session.commit()

        media_item = session.execute(
            select(MediaItem).where(MediaItem.id == UUID(media_id))
        ).scalar_one_or_none()

        if not media_item:
            return

        video_path = os.path.join("/app/uploads", str(media_item.user_id), media_item.filename)

        # Run all DNA extraction analyses
        # 1. Scene detection for cut pace
        from workers.scene.tasks import run_scene_detection
        try:
            segments = run_scene_detection(video_path)
            duration_s = (media_item.duration_ms or 15000) / 1000
            cut_pace = calculate_cut_pace(len(segments), duration_s)
            scene_boundaries = [s["start_ms"] for s in segments]
        except Exception:
            cut_pace = {"label": "medium", "avg_cut_duration": 2.0, "scene_count": 5}
            scene_boundaries = []

        # 2. Color analysis
        if HAS_CV2:
            color_data = analyze_color_histogram(video_path)
        else:
            color_data = {"color_grade": "natural", "dominant_colors": [], "color_temperature": "neutral"}

        # 3. Optical flow
        if HAS_CV2:
            motion_data = analyze_optical_flow(video_path)
        else:
            motion_data = {"motion_type": "handheld", "avg_motion_magnitude": 0}

        # 4. Text overlay detection
        if HAS_CV2:
            text_data = detect_text_overlays(video_path)
        else:
            text_data = {"text_energy": "low", "texts_per_minute": 0, "text_count": 0, "sample_texts": []}

        # 5. Transition classification
        if HAS_CV2:
            transition_data = classify_transitions(video_path, scene_boundaries)
        else:
            transition_data = {"dominant_transition": "hard_cut", "transitions": [], "transition_variety": 0}

        # 6. Audio analysis
        audio_data = {"bpm": 120}
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "audio.wav")
            from workers.audio.tasks import extract_audio, analyze_bpm
            if extract_audio(video_path, audio_path):
                bpm_data = analyze_bpm(audio_path)
                audio_data = {"bpm": bpm_data["bpm"], "beat_grid": bpm_data["beat_times"]}

        # Assemble Style DNA
        style_dna = {
            "cut_pace": cut_pace["label"],
            "cut_pace_detail": cut_pace,
            "color_grade": color_data["color_grade"],
            "color_data": color_data,
            "transition_type": transition_data["dominant_transition"],
            "transition_data": transition_data,
            "text_energy": text_data["text_energy"],
            "text_data": text_data,
            "bpm": audio_data.get("bpm", 120),
            "beat_grid": audio_data.get("beat_grid", []),
            "visual_motion": motion_data["motion_type"],
            "motion_data": motion_data,
            "color_temperature": color_data.get("color_temperature", "neutral"),
            "dominant_colors": color_data.get("dominant_colors", []),
        }

        # Store DNA in job
        job.style_dna = style_dna
        job.beat_grid = {"bpm": style_dna["bpm"], "beats": style_dna.get("beat_grid", [])}
        job.progress = 50
        session.commit()

        # Check if user media is done before pushing to blueprint
        from sqlalchemy import func
        from shared.models import MediaItem, MediaStatus
        media_ids = job.media_ids or []
        if media_ids:
            ready_count = session.execute(
                select(func.count()).select_from(MediaItem).where(
                    MediaItem.id.in_(media_ids),
                    MediaItem.status == MediaStatus.READY,
                )
            ).scalar() or 0
            if ready_count < len(media_ids):
                logger.info(f"[DNA] Waiting for user media ({ready_count}/{len(media_ids)} ready)")
                job.status = JobStatus.ANALYSING
                session.commit()
                return

        job.status = JobStatus.GENERATING_BLUEPRINT
        session.commit()

        from workers.blueprint.tasks import generate_blueprint
        generate_blueprint.delay(job_id)

        logger.info(f"[DNA] Style DNA extracted for job {job_id}: {style_dna['cut_pace']} pace, {style_dna['color_grade']} grade")

    except Exception as e:
        logger.error(f"[DNA] Error: {e}")
        session.rollback()
        if job:
            job.status = JobStatus.FAILED
            job.error_stage = "dna_extraction"
            job.error_message = str(e)
            session.commit()
        raise self.retry(countdown=30, max_retries=3)
    finally:
        session.close()
