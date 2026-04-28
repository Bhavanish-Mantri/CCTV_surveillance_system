"""
face_recognition_module.py
--------------------------
Core face-recognition pipeline for the CCTV system.

Responsibilities:
  - Load encodings from DB
  - Process a video file frame-by-frame
  - Match detected faces against known encodings
  - Return structured results (known / unknown)
  - Trigger alert sound on intruder detection
"""

import cv2
import face_recognition
import numpy as np
import logging
import os
import threading
import time
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional

from config import (
    FACE_DISTANCE_THRESHOLD,
    FRAME_RESIZE_SCALE,
    PROCESS_EVERY_N_FRAMES,
    INTRUDER_FOLDER,
)

logger = logging.getLogger(__name__)

# Alert helpers (non-blocking)

def _play_beep():
    """Play alert sound in a background thread (Windows + fallback)."""
    try:
        import winsound
        winsound.Beep(1000, 400)   # 1 kHz, 400 ms
    except Exception:
        try:
            import playsound
            sound_path = os.path.join(os.path.dirname(__file__), "static", "alert.wav")
            if os.path.exists(sound_path):
                playsound.playsound(sound_path)
        except Exception as e:
            logger.debug(f"Audio alert unavailable: {e}")


def trigger_alert():
    """Fire-and-forget beep in a daemon thread."""
    t = threading.Thread(target=_play_beep, daemon=True)
    t.start()

# Encoding helpers
# ---------------------------------------------------------------------------

def encode_face_from_image(image_path: str) -> Optional[np.ndarray]:
    """
    Load an image from disk and return the face encoding.
    Uses num_jitters=5 for higher-quality encoding (slower but much more
    accurate for the stored reference that all video frames compare against).
    Returns None if no face is detected.
    """
    try:
        img = face_recognition.load_image_file(image_path)
        locs = face_recognition.face_locations(img, model="hog")
        if not locs:
            logger.warning(f"No face found in image: {image_path}")
            return None
        if len(locs) > 1:
            logger.warning(f"Multiple faces found in {image_path}; using the first one.")
        encs = face_recognition.face_encodings(img, known_face_locations=[locs[0]], num_jitters=5)
        return encs[0] if encs else None
    except Exception as e:
        logger.error(f"Error encoding image {image_path}: {e}")
        return None


def encode_face_from_array(rgb_array: np.ndarray) -> Optional[np.ndarray]:
    """Encode the first (and ideally only) face in an RGB numpy array."""
    try:
        encs = face_recognition.face_encodings(rgb_array)
        return encs[0] if encs else None
    except Exception as e:
        logger.error(f"Error encoding face array: {e}")
        return None

# Matching
# ---------------------------------------------------------------------------

def find_best_match(
    unknown_encoding: np.ndarray,
    known_data: List[Tuple[int, str, np.ndarray]],
) -> Tuple[Optional[int], Optional[str], float]:
    """
    Compare unknown_encoding against all known encodings.

    Returns (user_id, name, distance).
    If no match below threshold → (None, "Unknown", best_distance).
    """
    if not known_data:
        return None, "Unknown", 1.0

    known_ids   = [row[0] for row in known_data]
    known_names = [row[1] for row in known_data]
    known_encs  = [row[2] for row in known_data]

    distances = face_recognition.face_distance(known_encs, unknown_encoding)
    best_idx  = int(np.argmin(distances))
    best_dist = float(distances[best_idx])

    if best_dist < FACE_DISTANCE_THRESHOLD:
        return known_ids[best_idx], known_names[best_idx], best_dist
    else:
        return None, "Unknown", best_dist

# Main processing pipeline

FaceResult = Dict[str, Any]
"""
Keys:
  frame_no  : int
  user_id   : int | None
  name      : str
  distance  : float
  confidence: float   (1 - distance, clamped 0-1)
  is_known  : bool
  face_loc  : tuple   (top, right, bottom, left) in original frame coords
  intruder_image_path : str | None   (path where intruder crop was saved)
"""


def process_video(
    video_path: str,
    known_data: List[Tuple[int, str, np.ndarray]],
    on_known_face=None,
    on_unknown_face=None,
) -> Tuple[List[FaceResult], bool]:
    """
    Process a video file and return face-recognition results.

    Parameters
    ----------
    video_path    : Path to the video file.
    known_data    : Output of database.get_all_encodings().
    on_known_face : Callable(result) — side-effects for known faces.
    on_unknown_face : Callable(result) — called only for *unique* intruders.

    Returns
    -------
    (results, has_intruders)
      results       : list of FaceResult dicts
      has_intruders : True if at least one unique intruder was detected
    """
    os.makedirs(INTRUDER_FOLDER, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    results: List[FaceResult] = []
    frame_no = 0

    # ── Intruder dedup: track unique unknown face encodings ──
    seen_unknown_encodings: List[np.ndarray] = []
    INTRUDER_DEDUP_THRESHOLD = FACE_DISTANCE_THRESHOLD  # same person if below this

    logger.info(f"Starting video processing: {video_path}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_no += 1
        if frame_no % PROCESS_EVERY_N_FRAMES != 0:
            continue

        # --- Resize for faster detection ---
        small_frame = cv2.resize(
            frame, (0, 0), fx=FRAME_RESIZE_SCALE, fy=FRAME_RESIZE_SCALE
        )
        rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        try:
            face_locations  = face_recognition.face_locations(rgb_small, model="hog")
            face_encodings  = face_recognition.face_encodings(rgb_small, face_locations)
        except Exception as e:
            logger.warning(f"Frame {frame_no}: face detection error — {e}")
            continue

        if not face_locations:
            continue

        scale_inv = 1.0 / FRAME_RESIZE_SCALE

        for loc, enc in zip(face_locations, face_encodings):
            # Scale location back to original frame size
            top, right, bottom, left = [int(v * scale_inv) for v in loc]

            user_id, name, distance = find_best_match(enc, known_data)
            confidence = float(np.clip(1.0 - distance, 0.0, 1.0))
            is_known   = user_id is not None

            intruder_path = None
            is_new_intruder = False

            if not is_known:
                # ── Check if this unknown face was already seen ──
                already_seen = False
                if seen_unknown_encodings:
                    dists = face_recognition.face_distance(seen_unknown_encodings, enc)
                    if float(np.min(dists)) < INTRUDER_DEDUP_THRESHOLD:
                        already_seen = True

                if not already_seen:
                    # New unique intruder — save one photo
                    is_new_intruder = True
                    seen_unknown_encodings.append(enc)

                    crop = frame[max(0, top):bottom, max(0, left):right]
                    ts   = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    filename = f"intruder_{ts}.jpg"
                    intruder_path = os.path.join(INTRUDER_FOLDER, filename)
                    try:
                        if crop.size > 0:
                            cv2.imwrite(intruder_path, crop)
                        else:
                            cv2.imwrite(intruder_path, frame)
                    except Exception as e:
                        logger.error(f"Could not save intruder image: {e}")
                        intruder_path = None

            result: FaceResult = {
                "frame_no":           frame_no,
                "user_id":            user_id,
                "name":               name,
                "distance":           distance,
                "confidence":         round(confidence * 100, 1),
                "is_known":           is_known,
                "face_loc":           (top, right, bottom, left),
                "intruder_image_path": intruder_path,
            }
            results.append(result)
            logger.debug(
                f"Frame {frame_no}: name={name}, dist={distance:.4f}, conf={confidence*100:.1f}%"
            )

            if is_known and callable(on_known_face):
                try:
                    on_known_face(result)
                except Exception as e:
                    logger.error(f"on_known_face callback error: {e}")

            if is_new_intruder and callable(on_unknown_face):
                try:
                    on_unknown_face(result)
                except Exception as e:
                    logger.error(f"on_unknown_face callback error: {e}")

    cap.release()
    has_intruders = len(seen_unknown_encodings) > 0
    logger.info(
        f"Video processing complete. Frames scanned: {frame_no}, "
        f"Faces found: {len(results)}, Unique intruders: {len(seen_unknown_encodings)}"
    )
    return results, has_intruders
