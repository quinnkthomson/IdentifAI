"""
cv_model.py
-----------
Contains all computer vision functionality for the Raspberry Pi. Provides helper
functions for:
    - detecting people in the frame,
    - performing face recognition using OpenCV,
    - classifying detections as "known" or "unknown" based on reference images.

Used by capture.py to attach semantic labels to events before logging.
"""