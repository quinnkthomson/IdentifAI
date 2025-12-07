"""
capture.py
----------
Main loop running on the Raspberry Pi. Handles camera initialization, continuous
frame capture, and motion detection. When motion is detected, this script saves
an image locally and sends an event (including timestamp and file path) to the
Flask backend. This is the core data-producing component of the system.
"""

import os
import time
import requests
import logging
from datetime import datetime
from pathlib import Path

try:
    from picamera2 import Picamera2
    CAMERA_AVAILABLE = True
except ImportError:
    print("Warning: picamera2 not available, using mock camera")
    CAMERA_AVAILABLE = False

from config import *
from utils import setup_logging, ensure_directory, get_iso_timestamp

class MockCamera:
    """Mock camera for testing when picamera2 is not available"""
    def __init__(self):
        self.is_open = False

    def start(self):
        self.is_open = True
        print("Mock camera started")

    def capture_file(self, filename):
        # Create a simple test image file
        with open(filename, 'w') as f:
            f.write("Mock image data")
        print(f"Mock capture saved to {filename}")

    def stop(self):
        self.is_open = False
        print("Mock camera stopped")

def setup_camera():
    """Initialize and configure the camera"""
    if CAMERA_AVAILABLE:
        picam2 = Picamera2()
        config = picam2.create_still_configuration()
        picam2.configure(config)
        return picam2
    else:
        return MockCamera()

def capture_image(camera):
    """Capture an image and return the filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{CAPTURE_DIR}/capture_{timestamp}.jpg"

    try:
        camera.capture_file(filename)
        logging.info(f"Image captured: {filename}")
        return filename
    except Exception as e:
        logging.error(f"Failed to capture image: {e}")
        return None

def send_to_backend(image_path):
    """Send captured image data to the Flask backend"""
    try:
        with open(image_path, 'rb') as image_file:
            files = {'file': image_file}
            data = {
                'timestamp': get_iso_timestamp(),
                'source': 'raspberry_pi'
            }

            response = requests.post(f"{BACKEND_URL}/pi_capture", files=files, data=data, timeout=BACKEND_TIMEOUT)
            if response.status_code == 201:
                logging.info(f"Successfully sent {image_path} to backend")
                return True
            else:
                logging.error(f"Failed to send to backend: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logging.error(f"Error sending to backend: {e}")
        return False

def main():
    """Main capture loop"""
    setup_logging(LOG_FILE, logging.DEBUG if DEBUG_MODE else logging.INFO)
    logging.info("Starting Raspberry Pi capture service...")

    # Setup
    ensure_directory(CAPTURE_DIR)
    camera = setup_camera()
    camera.start()

    logging.info(f"Camera initialized. Capturing every {CAPTURE_INTERVAL} seconds...")

    try:
        while True:
            # Capture image
            image_path = capture_image(camera)
            if image_path:
                # Send to backend
                send_to_backend(image_path)

            # Wait before next capture
            time.sleep(CAPTURE_INTERVAL)

    except KeyboardInterrupt:
        logging.info("Stopping capture service...")
    finally:
        camera.stop()

if __name__ == "__main__":
    main()