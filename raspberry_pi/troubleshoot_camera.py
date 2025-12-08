#!/usr/bin/env python3
"""
Camera Troubleshooting Script for IdentifAI
Run this to diagnose Raspberry Pi camera issues
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and return the result"""
    print(f"\n🔍 {description}")
    print(f"Command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ SUCCESS")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
        else:
            print("❌ FAILED")
            if result.stderr.strip():
                print(f"Error: {result.stderr.strip()}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("⏰ TIMEOUT (took too long)")
        return False
    except Exception as e:
        print(f"💥 ERROR: {e}")
        return False

def check_system():
    """Check system prerequisites"""
    print("🖥️  SYSTEM CHECKS")
    print("=" * 50)

    # Check if running on Raspberry Pi
    run_command("uname -a | grep -i raspberry", "Check if running on Raspberry Pi")

    # Check Raspberry Pi OS version
    run_command("lsb_release -a 2>/dev/null || cat /etc/os-release", "Check OS version")

    # Check Python version
    run_command("python3 --version", "Check Python version")

def check_camera_hardware():
    """Check camera hardware and configuration"""
    print("\n📷 CAMERA HARDWARE CHECKS")
    print("=" * 50)

    # Check if camera is enabled in raspi-config
    run_command("raspi-config nonint get_camera", "Check if camera is enabled (should return 0)")

    # Check camera interface
    run_command("vcgencmd get_camera", "Check camera detection")

    # Check camera module
    run_command("ls /dev/video*", "List video devices")

    # Check for Raspberry Pi Camera Module
    run_command("ls /dev/vchiq", "Check for camera interface device")

def check_camera_libraries():
    """Check camera libraries"""
    print("\n📚 CAMERA LIBRARY CHECKS")
    print("=" * 50)

    # Check if picamera2 is installed
    run_command("python3 -c 'import picamera2; print(\"Picamera2 version:\", picamera2.__version__)'", "Check Picamera2 installation")

    # Check if OpenCV is installed
    run_command("python3 -c 'import cv2; print(\"OpenCV version:\", cv2.__version__)'", "Check OpenCV installation")

    # Test basic camera functionality
    camera_test_cmd = '''python3 -c "
try:
    from picamera2 import Picamera2
    print('Picamera2 import successful')
    cam = Picamera2()
    print('Picamera2 instance created')
    config = cam.create_still_configuration()
    print('Configuration created')
    cam.configure(config)
    print('Camera configured successfully')
except Exception as e:
    print(f'Camera test failed: {e}')
"'''
    run_command(camera_test_cmd, "Test basic camera functionality")

def check_permissions():
    """Check user permissions"""
    print("\n🔐 PERMISSIONS CHECKS")
    print("=" * 50)

    # Check if user is in video group
    run_command("groups | grep -q video && echo 'User is in video group' || echo 'User NOT in video group'", "Check video group membership")

    # Check current user
    run_command("whoami", "Check current user")

    # Check if user can access camera
    device_check_cmd = '''python3 -c "
import os
try:
    # Try to access camera device
    if os.path.exists('/dev/vchiq'):
        print('Can access camera device')
    else:
        print('Camera device not found')
except Exception as e:
    print(f'Permission check failed: {e}')
"'''
    run_command(device_check_cmd, "Check camera device access")

def provide_solutions():
    """Provide troubleshooting solutions"""
    print("\n🔧 TROUBLESHOOTING SOLUTIONS")
    print("=" * 50)

    solutions = [
        ("Enable Camera", "sudo raspi-config nonint do_camera 0"),
        ("Add user to video group", "sudo usermod -a -G video $USER"),
        ("Reboot after changes", "sudo reboot"),
        ("Check camera ribbon cable", "Ensure camera cable is properly seated"),
        ("Test with libcamera", "libcamera-still -o test.jpg"),
        ("Check camera LED", "Camera LED should light up when accessed"),
        ("Try different USB port", "If using USB camera, try different port"),
        ("Check power supply", "Ensure adequate power (3A+ recommended)")
    ]

    for i, (title, command) in enumerate(solutions, 1):
        print(f"{i}. {title}:")
        print(f"   {command}")
        print()

def main():
    """Main troubleshooting function"""
    print("🔧 IdentifAI Camera Troubleshooting")
    print("=" * 60)
    print("This script will diagnose common Raspberry Pi camera issues.")

    check_system()
    check_camera_hardware()
    check_camera_libraries()
    check_permissions()
    provide_solutions()

    print("\n📋 NEXT STEPS:")
    print("1. Run the suggested commands above")
    print("2. Reboot if you made system changes")
    print("3. Run this script again to verify fixes")
    print("4. Try: python3 capture.py (should now work with mock camera fallback)")
    print("\nIf issues persist, check the Raspberry Pi camera documentation.")

if __name__ == "__main__":
    main()