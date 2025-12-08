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
CAPTURE_INTERVAL = 10  # Seconds between captures (increased to reduce detection frequency)
IMAGE_QUALITY = 85

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