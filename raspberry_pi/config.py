"""
config.py
---------
Stores configuration parameters for the Pi-side system: camera resolution,
motion detection thresholds, model paths, database/API endpoints, and tunable
constants. Central location for modifying behavior without touching main code.
"""

# Camera settings
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FRAMERATE = 30

# Capture settings
CAPTURE_DIR = "captured_images"
CAPTURE_INTERVAL = 30  # Seconds between captures (30s = ~2 per minute, much less spam)
IMAGE_QUALITY = 85

# Latest frame for web display (saved to web_app for streaming)
LATEST_FRAME_PATH = "../web_app/static/images/latest_frame.jpg"

# Backend communication
BACKEND_URL = "http://localhost:5001"  # Flask app URL
BACKEND_TIMEOUT = 10  # Request timeout in seconds

# Motion detection (for future use)
MOTION_THRESHOLD = 5000
MIN_MOTION_AREA = 500

# File paths
LOG_FILE = "capture.log"

# Debug settings
DEBUG_MODE = True
VERBOSE_LOGGING = True

# Demo mode (runs without camera if True)
DEMO_MODE = False  # Set to True to force mock camera even if real camera available

# Face detection settings
ENABLE_FACE_DETECTION = True  # Set to False to skip face detection (just capture images)