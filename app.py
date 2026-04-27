"""
app.py
------
Flask application — REST API + HTML dashboard for CCTV Attendance System.
"""

import os
import logging
import threading
from datetime import datetime

# Load .env overrides before config reads os.getenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optional; values fall back to defaults in config.py


from flask import (
    Flask, request, jsonify, render_template,
    redirect, url_for, flash, send_from_directory,
)
from werkzeug.utils import secure_filename

import database as db
import face_recognition_module as frm
from config import (
    SECRET_KEY, DEBUG, HOST, PORT,
    UPLOAD_FOLDER, INTRUDER_FOLDER, USER_IMG_FOLDER,
    ALLOWED_VIDEO_EXT, ALLOWED_IMAGE_EXT,
)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App init
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024   # 500 MB max upload

for folder in (UPLOAD_FOLDER, INTRUDER_FOLDER, USER_IMG_FOLDER):
    os.makedirs(folder, exist_ok=True)

# ---------------------------------------------------------------------------
# In-memory processing state (simple; not distributed)
# ---------------------------------------------------------------------------
processing_status: dict = {
    "running": False,
    "progress": 0,
    "message":  "Idle",
    "results":  [],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def allowed_file(filename: str, extensions: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions


def api_response(data=None, message="OK", status=200, error=None):
    payload = {"status": "success" if not error else "error", "message": message}
    if data is not None:
        payload["data"] = data
    if error:
        payload["error"] = str(error)
    return jsonify(payload), status


def serialise_row(row: dict) -> dict:
    """Convert datetime objects to ISO strings for JSON serialisation."""
    out = {}
    for k, v in row.items():
        out[k] = v.isoformat() if isinstance(v, datetime) else v
    return out


# ---------------------------------------------------------------------------
# Background video processor
# ---------------------------------------------------------------------------

def _run_video_processing(video_path: str):
    global processing_status
    processing_status.update({"running": True, "progress": 0, "message": "Loading encodings…", "results": []})

    try:
        known_data = db.get_all_encodings()
        processing_status["message"] = f"Loaded {len(known_data)} known face(s). Processing video…"

        face_results = []

        def on_known(result):
            db.mark_attendance(result["user_id"], result["confidence"] / 100.0)
            face_results.append(result)

        def on_unknown(result):
            if result.get("intruder_image_path"):
                rel = os.path.relpath(result["intruder_image_path"],
                                      os.path.join(os.path.dirname(__file__), "static"))
                rel = rel.replace("\\", "/")
                db.add_intruder(rel, 1.0 - result["confidence"] / 100.0)
            face_results.append(result)

        _, has_intruders = frm.process_video(
            video_path, known_data,
            on_known_face=on_known,
            on_unknown_face=on_unknown,
        )

        # Beep alert AFTER processing is complete (not during)
        if has_intruders:
            frm.trigger_alert()
            logger.info("Intruder(s) detected — alert triggered.")

        processing_status.update({
            "running":  False,
            "progress": 100,
            "message":  f"Done. {len(face_results)} face event(s) detected.",
            "results":  face_results,
        })
        logger.info("Background processing finished.")

    except Exception as e:
        processing_status.update({
            "running": False,
            "progress": 0,
            "message": f"Error: {e}",
        })
        logger.exception("Video processing failed")


# ===========================================================================
# HTML Routes (Dashboard)
# ===========================================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/attendance")
def attendance_page():
    logs = [serialise_row(r) for r in db.get_attendance_logs(200)]
    return render_template("attendance.html", logs=logs)


@app.route("/intruders")
def intruders_page():
    logs = [serialise_row(r) for r in db.get_intruder_logs(200)]
    return render_template("intruders.html", logs=logs)


@app.route("/users")
def users_page():
    from config import FACE_DISTANCE_THRESHOLD, ATTENDANCE_COOLDOWN_MINUTES
    users = db.get_all_users()
    return render_template(
        "users.html", users=users,
        threshold=FACE_DISTANCE_THRESHOLD,
        cooldown=ATTENDANCE_COOLDOWN_MINUTES,
    )


# ===========================================================================
# REST API — Video
# ===========================================================================

@app.route("/api/upload_video", methods=["POST"])
def upload_video():
    if "video" not in request.files:
        return api_response(message="No video file in request.", status=400, error="missing_field")
    file = request.files["video"]
    if not file.filename:
        return api_response(message="Empty filename.", status=400, error="empty_filename")
    if not allowed_file(file.filename, ALLOWED_VIDEO_EXT):
        return api_response(message="Unsupported video format.", status=400, error="bad_extension")

    if processing_status["running"]:
        return api_response(message="Another video is already being processed.", status=409, error="busy")

    fname = secure_filename(file.filename)
    save_path = os.path.join(UPLOAD_FOLDER, fname)
    file.save(save_path)
    logger.info(f"Video uploaded: {save_path}")

    t = threading.Thread(target=_run_video_processing, args=(save_path,), daemon=True)
    t.start()

    return api_response(message="Video uploaded. Processing started.", data={"filename": fname})


@app.route("/api/processing_status")
def get_processing_status():
    safe = {k: v for k, v in processing_status.items() if k != "results"}
    safe["result_count"] = len(processing_status.get("results", []))
    return api_response(data=safe)


# ===========================================================================
# REST API — Users
# ===========================================================================

@app.route("/api/users", methods=["GET"])
def list_users():
    users = db.get_all_users()
    return api_response(data=[serialise_row(u) for u in users])


@app.route("/api/users", methods=["POST"])
def add_user():
    name = request.form.get("name", "").strip()
    if not name:
        return api_response(message="'name' is required.", status=400, error="missing_field")
    if "image" not in request.files:
        return api_response(message="'image' file is required.", status=400, error="missing_field")

    image_file = request.files["image"]
    if not allowed_file(image_file.filename, ALLOWED_IMAGE_EXT):
        return api_response(message="Unsupported image format.", status=400, error="bad_extension")

    fname = secure_filename(f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{image_file.filename}")
    image_path = os.path.join(USER_IMG_FOLDER, fname)
    image_file.save(image_path)

    encoding = frm.encode_face_from_image(image_path)
    if encoding is None:
        os.remove(image_path)
        return api_response(
            message="No face detected in the uploaded image. Please use a clear frontal face photo.",
            status=422,
            error="no_face_detected",
        )

    rel = os.path.relpath(image_path, os.path.join(os.path.dirname(__file__), "static")).replace("\\", "/")
    user_id = db.add_user(name, rel, encoding)
    return api_response(message="User added.", data={"user_id": user_id, "name": name}, status=201)


@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id: int):
    deleted = db.delete_user(user_id)
    if deleted:
        return api_response(message=f"User {user_id} deleted.")
    return api_response(message="User not found.", status=404, error="not_found")


# ===========================================================================
# REST API — Attendance
# ===========================================================================

@app.route("/api/attendance", methods=["GET"])
def get_attendance():
    limit = int(request.args.get("limit", 200))
    logs  = db.get_attendance_logs(limit)
    return api_response(data=[serialise_row(r) for r in logs])


# ===========================================================================
# REST API — Intruders
# ===========================================================================

@app.route("/api/intruders", methods=["GET"])
def get_intruders():
    limit = int(request.args.get("limit", 200))
    logs  = db.get_intruder_logs(limit)
    return api_response(data=[serialise_row(r) for r in logs])




# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    db.init_db()
    logger.info(f"Starting CCTV Attendance System on http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=DEBUG, threaded=True)
