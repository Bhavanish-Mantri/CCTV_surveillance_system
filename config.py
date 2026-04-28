"""
config.py
---------
Central configuration for the CCTV Attendance & Intruder Detection System.
"""

import os

# MySQL

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 3306)),
    "user":     os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),   # ← set your MySQL password
    "database": os.getenv("DB_NAME", "cctv_attendance"),
    "autocommit": False,
}

# Flask

SECRET_KEY   = os.getenv("SECRET_KEY", "change-me-in-production")
DEBUG        = os.getenv("FLASK_DEBUG", "true").lower() == "true"
HOST         = os.getenv("FLASK_HOST", "0.0.0.0")
PORT         = int(os.getenv("FLASK_PORT", 5000))

# File paths

BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER   = os.path.join(BASE_DIR, "static", "uploads")
INTRUDER_FOLDER = os.path.join(BASE_DIR, "static", "intruders")
USER_IMG_FOLDER = os.path.join(BASE_DIR, "static", "user_images")

# Face recognition

FACE_DISTANCE_THRESHOLD   = float(os.getenv("FACE_THRESHOLD", 0.6))   
FRAME_RESIZE_SCALE        = float(os.getenv("FRAME_SCALE", 0.5))     
PROCESS_EVERY_N_FRAMES    = int(os.getenv("PROCESS_N_FRAMES", 2))    

# Attendance

ATTENDANCE_COOLDOWN_MINUTES = int(os.getenv("ATTENDANCE_COOLDOWN", 10))

# Allowed extensions

ALLOWED_VIDEO_EXT = {"mp4", "avi", "mov", "mkv", "webm"}
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg"}
