"""
database.py
-----------
MySQL database layer for CCTV Attendance & Intruder Detection System.
Handles all DB operations: users, attendance, intruders.
"""

import mysql.connector
import pickle
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any
from config import DB_CONFIG, ATTENDANCE_COOLDOWN_MINUTES

logger = logging.getLogger(__name__)

# Connection helper

def get_connection():
    """Return a fresh MySQL connection using config settings."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise

# Schema initialisation
# ---------------------------------------------------------------------------

def init_db():
    """Create the database and all required tables if they don't exist."""
    # Connect without specifying a database first so we can create it
    base_cfg = {k: v for k, v in DB_CONFIG.items() if k != "database"}
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**base_cfg)
        cursor = conn.cursor()
        db_name = DB_CONFIG["database"]
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.execute(f"USE `{db_name}`;")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                name        VARCHAR(255) NOT NULL,
                image_path  TEXT,
                encoding    LONGBLOB,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                user_id     INT NOT NULL,
                timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
                confidence  FLOAT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB;
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS intruders (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                image_path  TEXT,
                timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
                confidence  FLOAT COMMENT 'lowest distance to any known face'
            ) ENGINE=InnoDB;
        """)

        conn.commit()
        logger.info("Database initialised successfully.")
    except mysql.connector.Error as e:
        logger.error(f"DB initialisation error: {e}")
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

# User operations

def add_user(name: str, image_path: str, encoding) -> int:
    """Insert a new user; encoding is a numpy array serialised with pickle."""
    encoding_blob = pickle.dumps(encoding)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, image_path, encoding) VALUES (%s, %s, %s)",
            (name, image_path, encoding_blob),
        )
        conn.commit()
        user_id = cursor.lastrowid
        logger.info(f"Added user '{name}' with id={user_id}")
        return user_id
    except mysql.connector.Error as e:
        logger.error(f"add_user error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def get_all_users() -> List[Dict[str, Any]]:
    """Return all users (without the raw encoding blob for speed)."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, image_path, created_at FROM users")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def get_all_encodings() -> List[Tuple[int, str, Any]]:
    """Return [(user_id, name, encoding_array), ...] for all users."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, encoding FROM users WHERE encoding IS NOT NULL")
        rows = cursor.fetchall()
        result = []
        for uid, name, blob in rows:
            if blob:
                try:
                    enc = pickle.loads(blob)
                    result.append((uid, name, enc))
                except Exception as e:
                    logger.warning(f"Could not deserialise encoding for user {uid}: {e}")
        return result
    finally:
        cursor.close()
        conn.close()


def delete_user(user_id: int) -> bool:
    """Delete a user by ID."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        conn.close()

# Attendance operations
# ---------------------------------------------------------------------------

def mark_attendance(user_id: int, confidence: float) -> Optional[int]:
    """
    Insert an attendance record ONLY if the last entry for this user is older
    than ATTENDANCE_COOLDOWN_MINUTES.  Returns the new record id or None.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cutoff = datetime.now() - timedelta(minutes=ATTENDANCE_COOLDOWN_MINUTES)
        cursor.execute(
            "SELECT id FROM attendance WHERE user_id=%s AND timestamp > %s LIMIT 1",
            (user_id, cutoff),
        )
        if cursor.fetchone():
            logger.debug(f"Attendance for user {user_id} skipped (cooldown active)")
            return None

        cursor.execute(
            "INSERT INTO attendance (user_id, confidence) VALUES (%s, %s)",
            (user_id, round(confidence, 4)),
        )
        conn.commit()
        record_id = cursor.lastrowid
        logger.info(f"Attendance marked for user_id={user_id}, confidence={confidence:.4f}")
        return record_id
    except mysql.connector.Error as e:
        logger.error(f"mark_attendance error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def get_attendance_logs(limit: int = 200) -> List[Dict[str, Any]]:
    """Return attendance records joined with user name, most recent first."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.id, u.name, u.image_path, a.timestamp, a.confidence
            FROM attendance a
            JOIN users u ON a.user_id = u.id
            ORDER BY a.timestamp DESC
            LIMIT %s
        """, (limit,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

# Intruder operations

def add_intruder(image_path: str, confidence: float) -> int:
    """Insert an intruder record and return its id."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO intruders (image_path, confidence) VALUES (%s, %s)",
            (image_path, round(confidence, 4)),
        )
        conn.commit()
        record_id = cursor.lastrowid
        logger.info(f"Intruder recorded: {image_path}")
        return record_id
    except mysql.connector.Error as e:
        logger.error(f"add_intruder error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def get_intruder_logs(limit: int = 200) -> List[Dict[str, Any]]:
    """Return intruder records most recent first."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, image_path, timestamp, confidence FROM intruders ORDER BY timestamp DESC LIMIT %s",
            (limit,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
