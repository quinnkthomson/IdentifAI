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

    # Create events table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            image_path TEXT NOT NULL,
            is_motion BOOLEAN NOT NULL,
            is_person BOOLEAN NOT NULL,
            is_known BOOLEAN NOT NULL,
            person_name TEXT,
            label TEXT NOT NULL,
            confidence REAL NOT NULL,
            metadata TEXT
        )
    """)

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)

    # Create known people table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS known_people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            image_path TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

# ------------------------------------------------------------
# Event Functions
# ------------------------------------------------------------
def log_event(timestamp, image_path, is_motion, is_person, is_known, person_name, label, confidence, metadata):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO events (timestamp, image_path, is_motion, is_person, is_known, person_name, label, confidence, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, image_path, is_motion, is_person, is_known, person_name, label, confidence, metadata))

    conn.commit()
    conn.close()

def get_events(limit=10):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (limit,))
    events = cur.fetchall()
    conn.close()
    return events



