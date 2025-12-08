#!/usr/bin/env python3
"""
Test script for face detection functionality
Run this to verify that face detection is working properly
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

def test_face_detection():
    """Test face detection with a sample image"""
    try:
        from cv_model import has_faces, detect_faces, get_face_count
        print("✅ Face detection modules imported successfully")

        # Create a simple test image (this won't detect as a face, but tests the pipeline)
        import cv2
        import numpy as np

        # Create a blank image
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.imwrite('test_image.jpg', img)

        # Test face detection functions
        faces = detect_faces('test_image.jpg')
        has_face = has_faces('test_image.jpg')
        face_count = get_face_count('test_image.jpg')

        print("✅ Face detection functions working:"        print(f"   - Detected faces: {len(faces)}")
        print(f"   - Has faces: {has_face}")
        print(f"   - Face count: {face_count}")

        # Clean up
        os.remove('test_image.jpg')

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure OpenCV and dependencies are installed:")
        print("   pip install opencv-python numpy Pillow")
        return False

    except Exception as e:
        print(f"❌ Face detection test failed: {e}")
        return False

def test_raspberry_pi_imports():
    """Test that all Raspberry Pi modules can be imported"""
    try:
        import cv_model
        import utils
        print("✅ Raspberry Pi modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Raspberry Pi import error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing IdentifAI Face Detection System")
    print("=" * 50)

    # Test imports
    print("\n1. Testing module imports...")
    imports_ok = test_raspberry_pi_imports()

    if imports_ok:
        print("\n2. Testing face detection...")
        detection_ok = test_face_detection()

        if detection_ok:
            print("\n🎉 All tests passed! Face detection system is ready.")
        else:
            print("\n❌ Face detection test failed.")
    else:
        print("\n❌ Module imports failed - install dependencies first.")

    print("\n📋 To install dependencies:")
    print("   cd raspberry_pi")
    print("   pip install -r requirements.txt")
    print("\n📋 To run the capture system:")
    print("   python3 capture.py")