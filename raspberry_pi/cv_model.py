"""
cv_model.py
-----------
Contains computer vision functionality for the Raspberry Pi. Provides helper
functions for detecting faces in images using OpenCV Haar cascades.

Used by capture.py to determine if faces are present in captured images.
"""

import cv2
import os
from typing import List, Tuple, Optional

# Haar cascade classifier for face detection
FACE_CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_cascade = None

def init_face_detector():
    """Initialize the face detection cascade classifier"""
    global face_cascade
    if face_cascade is None:
        if not os.path.exists(FACE_CASCADE_PATH):
            raise FileNotFoundError(f"Haar cascade file not found: {FACE_CASCADE_PATH}")
        face_cascade = cv2.CascadeClassifier(FACE_CASCADE_PATH)
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