"""
cv_model.py
-----------
Contains computer vision functionality for the Raspberry Pi. Provides helper
functions for detecting faces in images using OpenCV Haar cascades.

Used by capture.py to determine if faces are present in captured images.
"""

import cv2
import os
import urllib.request
from typing import List, Tuple, Optional

# Haar cascade classifier for face detection
# Try multiple paths for the cascade file (handles different OpenCV installations)
def get_cascade_paths():
    """Get possible cascade file paths, handling cv2.data issues"""
    paths = []

    # Try cv2.data if available
    try:
        if hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
            paths.append(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    except:
        pass  # cv2.data not available, skip

    # Common system paths
    paths.extend([
        '/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
        '/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml',
        '/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml',
        'haarcascade_frontalface_default.xml'  # Current directory fallback
    ])

    return paths

POSSIBLE_CASCADE_PATHS = get_cascade_paths()

FACE_CASCADE_PATH = None
face_cascade = None

def download_cascade_file():
    """Download the Haar cascade file if not available locally"""
    local_path = 'haarcascade_frontalface_default.xml'
    url = 'https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml'

    if os.path.exists(local_path):
        print(f"Cascade file already exists locally: {local_path}")
        return local_path

    try:
        print(f"Downloading Haar cascade file from {url}...")
        urllib.request.urlretrieve(url, local_path)
        print(f"Successfully downloaded cascade file to: {local_path}")
        return local_path
    except Exception as e:
        print(f"Failed to download cascade file: {e}")
        return None

def init_face_detector():
    """Initialize the face detection cascade classifier"""
    global face_cascade, FACE_CASCADE_PATH
    if face_cascade is None:
        # Try different possible paths for the cascade file
        for cascade_path in POSSIBLE_CASCADE_PATHS:
            try:
                if os.path.exists(cascade_path):
                    face_cascade = cv2.CascadeClassifier(cascade_path)
                    if face_cascade and not face_cascade.empty():
                        FACE_CASCADE_PATH = cascade_path
                        print(f"Successfully loaded cascade from: {cascade_path}")
                        return face_cascade
            except Exception as e:
                print(f"Failed to load cascade from {cascade_path}: {e}")
                continue

        # If none of the standard paths worked, try downloading
        print("Standard cascade paths not found, attempting to download...")
        downloaded_path = download_cascade_file()
        if downloaded_path:
            try:
                face_cascade = cv2.CascadeClassifier(downloaded_path)
                if face_cascade and not face_cascade.empty():
                    FACE_CASCADE_PATH = downloaded_path
                    print(f"Successfully loaded downloaded cascade from: {downloaded_path}")
                    return face_cascade
            except Exception as e:
                print(f"Failed to load downloaded cascade: {e}")

        # If we get here, none of the paths worked
        raise FileNotFoundError(f"Could not find or load Haar cascade file. Tried paths: {POSSIBLE_CASCADE_PATHS}")
    return face_cascade

def detect_faces(image_path: str, scale_factor: float = 1.1, min_neighbors: int = 5) -> List[Tuple[int, int, int, int]]:
    """
    Detect faces in an image using Haar cascades.

    Args:
        image_path: Path to the image file
        scale_factor: Parameter specifying how much the image size is reduced at each image scale
        min_neighbors: Parameter specifying how many neighbors each candidate rectangle should have

    Returns:
        List of tuples (x, y, width, height) for each detected face
    """
    try:
        # Initialize detector if needed
        cascade = init_face_detector()

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            print(f"Warning: Could not load image {image_path}")
            return []

        # Convert to grayscale for face detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Detect faces
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=scale_factor,
            minNeighbors=min_neighbors,
            minSize=(30, 30)
        )

        # Convert numpy arrays to tuples
        face_rectangles = [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]

        return face_rectangles

    except Exception as e:
        print(f"Error detecting faces in {image_path}: {e}")
        return []

def has_faces(image_path: str) -> bool:
    """
    Check if an image contains any faces.

    Args:
        image_path: Path to the image file

    Returns:
        True if faces are detected, False otherwise
    """
    faces = detect_faces(image_path)
    return len(faces) > 0

def get_face_count(image_path: str) -> int:
    """
    Get the number of faces detected in an image.

    Args:
        image_path: Path to the image file

    Returns:
        Number of faces detected
    """
    faces = detect_faces(image_path)
    return len(faces)