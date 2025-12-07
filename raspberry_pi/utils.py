"""
utils.py
--------
Helper functions shared across Raspberry Pi scripts, including timestamp
formatting, image I/O helpers, directory setup, and network request utilities.
Keeps capture.py and cv_model.py simpler and more readable.
"""

import os
import logging
from datetime import datetime
from pathlib import Path

def setup_logging(log_file="capture.log", level=logging.INFO):
    """Setup logging configuration"""
    logging.basicConfig(
        filename=log_file,
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Also log to console
    console = logging.StreamHandler()
    console.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

def ensure_directory(dir_path):
    """Ensure a directory exists, create if it doesn't"""
    Path(dir_path).mkdir(parents=True, exist_ok=True)

def get_timestamp_string():
    """Get current timestamp as string"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_iso_timestamp():
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()

def cleanup_old_files(directory, max_age_days=7, pattern="*"):
    """Remove files older than max_age_days from directory"""
    import glob
    from datetime import timedelta

    cutoff_time = datetime.now() - timedelta(days=max_age_days)

    for filepath in glob.glob(os.path.join(directory, pattern)):
        if os.path.isfile(filepath):
            file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            if file_time < cutoff_time:
                try:
                    os.remove(filepath)
                    logging.info(f"Cleaned up old file: {filepath}")
                except Exception as e:
                    logging.error(f"Failed to remove {filepath}: {e}")

def get_file_size_mb(filepath):
    """Get file size in MB"""
    try:
        size_bytes = os.path.getsize(filepath)
        return size_bytes / (1024 * 1024)
    except:
        return 0