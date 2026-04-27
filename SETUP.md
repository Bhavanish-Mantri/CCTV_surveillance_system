# CCTV AI Attendance & Intruder Detection System — Setup Guide

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.8 – 3.10 | 3.11+ may have dlib issues |
| MySQL | 8.x | XAMPP / standalone |
| Visual C++ Build Tools | Latest | Required for dlib on Windows |
| CMake | 3.x | Required for dlib on Windows |

---

## Step 1 — Install CMake + dlib (Windows)

```bash
# 1. Download and install CMake from https://cmake.org/download/
# 2. Install Visual C++ Build Tools:
#    https://visualstudio.microsoft.com/visual-cpp-build-tools/
# 3. Install dlib (before face_recognition):
pip install cmake
pip install dlib
```

> **Tip:** If `pip install dlib` fails, use a pre-built wheel:
> https://github.com/jloh02/dlib/releases

---

## Step 2 — Create Python Virtual Environment

```bash
cd d:\City_scene_global_project
python -m venv venv
venv\Scripts\activate
```

---

## Step 3 — Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4 — Configure MySQL

1. Start MySQL (XAMPP → MySQL → Start, or `net start mysql`).
2. Open `config.py` and set your MySQL password:

```python
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "YOUR_MYSQL_PASSWORD",   # ← edit this
    "database": "cctv_attendance",
    ...
}
```

3. (Optional) Import the schema manually:
```bash
mysql -u root -p < schema.sql
```
The app also auto-creates the DB/tables on first run.

---

## Step 5 — Run the Application

```bash
python app.py
```

Open your browser: **http://localhost:5000**

---

## Step 6 — Using the System

### 6a. Register Users
1. Go to **Manage Users** (`/users`).
2. Enter the person's full name.
3. Upload a clear frontal face photo (JPG/PNG).
4. Click **Add User** — the system extracts and stores the face encoding.

### 6b. Process a Video
1. Go to **Dashboard** (`/`).
2. Drag & drop or browse for a surveillance video (MP4, AVI, MOV, MKV).
3. Click **Process Video**.
4. Watch the progress bar; results appear automatically.

### 6c. View Results
- **Attendance Records** (`/attendance`): All recognised users with timestamps and confidence scores.
- **Intruder Alerts** (`/intruders`): Unknown face crops with photo evidence.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload_video` | Upload + start video processing |
| `GET`  | `/api/processing_status` | Poll current processing state |
| `GET`  | `/api/users` | List all registered users |
| `POST` | `/api/users` | Add a new user (multipart: name + image) |
| `DELETE` | `/api/users/<id>` | Remove a user |
| `GET`  | `/api/attendance` | Fetch attendance logs |
| `GET`  | `/api/intruders` | Fetch intruder alerts |

---

## Configuration Reference (`config.py`)

| Key | Default | Description |
|-----|---------|-------------|
| `FACE_DISTANCE_THRESHOLD` | `0.5` | Lower = stricter matching |
| `FRAME_RESIZE_SCALE` | `0.25` | Frame downscale factor for speed |
| `PROCESS_EVERY_N_FRAMES` | `3` | Skip every N frames for speed |
| `ATTENDANCE_COOLDOWN_MINUTES` | `10` | Prevent duplicate entries |

---

## Folder Structure

```
d:\City_scene_global_project\
├── app.py                    ← Flask app & API
├── database.py               ← MySQL layer
├── face_recognition_module.py← Core AI pipeline
├── config.py                 ← All configuration
├── requirements.txt
├── schema.sql
├── SETUP.md
├── static\
│   ├── css\style.css
│   ├── js\main.js
│   ├── uploads\              ← Uploaded videos
│   ├── intruders\            ← Intruder face crops
│   └── user_images\          ← User registration photos
└── templates\
    ├── base.html
    ├── index.html
    ├── attendance.html
    ├── intruders.html
    └── users.html
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `dlib` install fails | Install CMake + Visual C++ Build Tools first |
| `No module named face_recognition` | `pip install face-recognition` |
| DB connection refused | Check MySQL is running; verify password in `config.py` |
| No face detected in upload | Use a clear, well-lit frontal photo |
| Video processing hangs | Reduce `PROCESS_EVERY_N_FRAMES` or `FRAME_RESIZE_SCALE` |
| Alert sound not working | Install `playsound` or ignore — system still works |
