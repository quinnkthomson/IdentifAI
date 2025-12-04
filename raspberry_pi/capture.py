"""
capture.py
----------
Main loop running on the Raspberry Pi. Handles camera initialization, continuous
frame capture, and motion detection. When motion is detected, this script saves
an image locally and sends an event (including timestamp and file path) to the
Flask backend. This is the core data-producing component of the system.
"""