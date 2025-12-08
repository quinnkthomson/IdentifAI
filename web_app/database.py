"""
database.py
-----------
Creates and manages the SQLite database used by IdentifAI. Defines functions
for inserting motion/person-detection events, retrieving logs, managing user
accounts, and handling file paths to captured images.
"""

import sqlite3
import os
from datetime import datetime

# Ensure database directory exists and use absolute path
DB_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DB_DIR, exist_ok=True)
DATABASE_PATH = os.path.join(DB_DIR, 'events.db')

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Create face detection events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS face_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            image_path TEXT NOT NULL,
            faces_detected BOOLEAN NOT NULL,
            face_count INTEGER NOT NULL,
            source TEXT NOT NULL,
            processed BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)

    conn.commit()
    conn.close()

# ------------------------------------------------------------
# Face Detection Event Functions
# ------------------------------------------------------------
def log_face_event(timestamp, image_path, faces_detected, face_count, source):
    """Log a face detection event"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO face_events (timestamp, image_path, faces_detected, face_count, source, processed)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (timestamp, image_path, faces_detected, face_count, source, False))

    conn.commit()
    conn.close()

def get_face_events(limit=50):
    """Get face detection events, ordered by timestamp descending"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM face_events ORDER BY timestamp DESC LIMIT ?", (limit,))
    events = cur.fetchall()
    conn.close()
    return events

def get_face_events_with_faces(limit=50):
    """Get only events where faces were detected"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM face_events WHERE faces_detected = 1 ORDER BY timestamp DESC LIMIT ?", (limit,))
    events = cur.fetchall()
    conn.close()
    return events

def get_face_detection_stats():
    """Get statistics about face detection events"""
    conn = get_db()
    cur = conn.cursor()

    # Total events
    cur.execute("SELECT COUNT(*) as total_events FROM face_events")
    total_events = cur.fetchone()['total_events']

    # Events with faces
    cur.execute("SELECT COUNT(*) as face_events FROM face_events WHERE faces_detected = 1")
    face_events = cur.fetchone()['face_events']

    # Total faces detected
    cur.execute("SELECT SUM(face_count) as total_faces FROM face_events")
    total_faces = cur.fetchone()['total_faces'] or 0

    conn.close()

    return {
        'total_events': total_events,
        'face_events': face_events,
        'total_faces': total_faces
    }



