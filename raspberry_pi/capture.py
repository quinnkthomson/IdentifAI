"""
capture.py
----------
Main loop running on the Raspberry Pi. Handles camera initialization, continuous
frame capture, and face detection. Saves images locally and sends events to the
Flask backend.
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
from cv_model import has_faces, get_face_count
from utils import setup_logging, ensure_directory, get_iso_timestamp
import shutil

class MockCamera:
    """Mock camera for testing when picamera2 is not available"""
    def __init__(self):
        self.is_open = False

    def start(self):
        self.is_open = True
        print("Mock camera started")

    def capture_file(self, filename):
        # Mock capture - create minimal placeholder file
        print(f"Mock capture: {filename}")
        try:
            Path(filename).touch()
        except:
            pass

    def stop(self):
        self.is_open = False
        print("Mock camera stopped")

def setup_camera():
    """Initialize and configure the camera"""
    if DEMO_MODE:
        print("Demo mode enabled, using mock camera")
        return MockCamera()

    if not CAMERA_AVAILABLE:
        print("Picamera2 not available, using mock camera")
        return MockCamera()

    try:
        print("Initializing Picamera2...")
        picam2 = Picamera2()
        print("Creating camera configuration...")
        config = picam2.create_still_configuration()
        print("Configuring camera...")
        picam2.configure(config)
        print("✅ Camera initialized successfully")
        return picam2
    except Exception as e:
        print(f"❌ Camera initialization failed: {e}")
        print("Falling back to mock camera for testing")
        return MockCamera()

def capture_image(camera, is_mock=False):
    """Capture an image and return the filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{CAPTURE_DIR}/capture_{timestamp}.jpg"

    try:
        camera.capture_file(filename)
        logging.info(f"Image captured: {filename}")
        
        # Copy to latest_frame.jpg for web display (only for real captures)
        if not is_mock and os.path.exists(filename) and os.path.getsize(filename) > 0:
            try:
                latest_path = LATEST_FRAME_PATH
                # Ensure directory exists
                os.makedirs(os.path.dirname(latest_path), exist_ok=True)
                shutil.copy2(filename, latest_path)
                logging.debug(f"Updated latest frame: {latest_path}")
            except Exception as e:
                logging.warning(f"Could not update latest frame: {e}")
        
        return filename
    except Exception as e:
        logging.error(f"Failed to capture image: {e}")
        return None

def send_to_backend(image_path, is_mock=False):
    """Send captured image data to the Flask backend"""
    try:
        # Skip face detection for mock captures or when disabled
        if is_mock or not ENABLE_FACE_DETECTION:
            faces_detected = False
            face_count = 0
        else:
            # Perform face detection for real captures
            faces_detected = has_faces(image_path)
            face_count = get_face_count(image_path) if faces_detected else 0

        # Only send if file exists and has content
        if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
            logging.debug(f"Skipping empty file: {image_path}")
            return False

        with open(image_path, 'rb') as image_file:
            files = {'file': image_file}
            data = {
                'timestamp': get_iso_timestamp(),
                'source': 'raspberry_pi',
                'faces_detected': 'true' if faces_detected else 'false',
                'face_count': str(face_count)
            }

            response = requests.post(f"{BACKEND_URL}/pi_capture", files=files, data=data, timeout=BACKEND_TIMEOUT)
            if response.status_code == 201:
                if faces_detected:
                    logging.info(f"✅ Face detected: {face_count} faces in {image_path}")
                return True
            else:
                logging.error(f"Failed to send to backend: {response.status_code}")
                return False
    except Exception as e:
        logging.error(f"Error sending to backend: {e}")
        return False

def main():
    """Main capture loop"""
    setup_logging(LOG_FILE, logging.DEBUG if DEBUG_MODE else logging.INFO)
    logging.info("=" * 50)
    logging.info("Starting Raspberry Pi capture service...")
    logging.info(f"Face detection: {'ENABLED' if ENABLE_FACE_DETECTION else 'DISABLED'}")
    logging.info(f"Capture interval: {CAPTURE_INTERVAL} seconds")
    logging.info("=" * 50)

    # Setup
    ensure_directory(CAPTURE_DIR)
    camera = setup_camera()

    try:
        camera.start()
        using_mock = isinstance(camera, MockCamera)
        
        if using_mock:
            logging.info("🎭 Running in MOCK mode - no real camera")
        else:
            logging.info("📷 Camera ready - capturing real images")

        capture_count = 0

        while True:
            image_path = capture_image(camera, is_mock=using_mock)
            if image_path:
                send_to_backend(image_path, is_mock=using_mock)
                capture_count += 1
                
                if capture_count % 5 == 0:
                    logging.info(f"📊 Captures completed: {capture_count}")

            time.sleep(CAPTURE_INTERVAL)

    except KeyboardInterrupt:
        logging.info("Stopping capture service...")
    finally:
        camera.stop()
        logging.info("Capture service stopped")

if __name__ == "__main__":
    main()
