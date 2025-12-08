"""
Web App Configuration
Centralized settings for the IdentifAI web application
"""

# Camera settings (should match Raspberry Pi)
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30

# Video encoding settings
VIDEO_BITRATE = 10000000  # 10 Mbps

# Web app settings
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB for file uploads

# Activity logging settings
MAX_ACTIVITY_ENTRIES = 100
ACTIVITY_REFRESH_INTERVAL = 10000  # ms

# Auto-capture settings
DEFAULT_AUTO_CAPTURE_INTERVAL = 5000  # ms

# Stream monitoring
STREAM_CHECK_INTERVAL = 5000  # ms