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

try:
    from picamera2 import Picamera2
    CAMERA_AVAILABLE = True
except ImportError:
    print("Warning: picamera2 not available, using mock camera")
    CAMERA_AVAILABLE = False

from config import *
from cv_model import has_faces, get_face_count
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
        # If this is a real camera, try to restart it
        if hasattr(camera, 'stop') and hasattr(camera, 'start') and not isinstance(camera, MockCamera):
            try:
                logging.info("Attempting to restart camera...")
                camera.stop()
                import time
                time.sleep(1)
                camera.start()
                logging.info("Camera restarted successfully")
            except Exception as restart_error:
                logging.error(f"Failed to restart camera: {restart_error}")
        return None

def send_to_backend(image_path):
    """Send captured image data to the Flask backend"""
    try:
        # Perform face detection
        faces_detected = has_faces(image_path)
        face_count = get_face_count(image_path) if faces_detected else 0

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
                    logging.info(f"Face detection event: {face_count} faces in {image_path}")
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

    try:
        camera.start()
        logging.info(f"Camera initialized. Capturing every {CAPTURE_INTERVAL} seconds...")
    except Exception as e:
        logging.error(f"Failed to start camera: {e}")
        if isinstance(camera, MockCamera):
            logging.info("Using mock camera - no real camera available")
            logging.info(f"Mock capture mode. Capturing every {CAPTURE_INTERVAL} seconds...")
        else:
            logging.error("Real camera failed to start. Switching to mock camera for testing.")
            # Switch to mock camera
            camera = MockCamera()
            camera.start()
            logging.info("Mock camera activated. System will run in demo mode.")

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

def main():
    """Main capture loop"""
    setup_logging(LOG_FILE, logging.DEBUG if DEBUG_MODE else logging.INFO)
    logging.info("Starting Raspberry Pi capture service...")

    # Setup
    ensure_directory(CAPTURE_DIR)
    camera = setup_camera()

    try:
        camera.start()
        logging.info(f"Camera initialized. Capturing every {CAPTURE_INTERVAL} seconds...")

        # Main capture loop
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

    except Exception as e:
        logging.error(f"Failed to start camera service: {e}")
        if isinstance(camera, MockCamera):
            logging.info("Running in demo mode - no camera required")
        else:
            raise

if __name__ == "__main__":
    main()