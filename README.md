# IdentifAI - User Manual

## What is IdentifAI?

IdentifAI is a camera streaming system designed for Raspberry Pi. It captures images from a connected camera module and displays them through a web-based interface that you can access from any browser on your local network.

**Important Note:** This project was originally intended to include face detection using OpenCV. However, that implementation encountered significant technical challenges and was not completed successfully. The current version provides **live camera streaming only**. The face detection code remains in the repository but is non-functional.

---

## Requirements

Before you begin, make sure you have:

### Hardware
- Raspberry Pi 4 (2GB RAM or more recommended)
- Raspberry Pi Camera Module 3 (either wide-angle or standard version)
- MicroSD card with Raspberry Pi OS installed
- Power supply for the Pi
- Network connection (Wi-Fi or Ethernet)

### Software
- Python 3.7 or higher
- pip (Python package manager)
- A modern web browser (Chrome, Firefox, Safari, or Edge)

---

## Installation

Follow these steps exactly to set up IdentifAI on your system.

### Step 1: Download the Project

Open a terminal and run:

```bash
git clone https://github.com/yourusername/IdentifAI.git
cd IdentifAI
```

If you received the project as a ZIP file, extract it and navigate to the folder:

```bash
cd /path/to/IdentifAI
```

### Step 2: Enable the Camera (Raspberry Pi Only)

If you're running on a Raspberry Pi with a camera module attached:

```bash
sudo raspi-config
```

Use the arrow keys to navigate to **Interface Options**, then **Camera**, then select **Enable**. Press Enter to confirm, then select **Finish** and reboot:

```bash
sudo reboot
```

After rebooting, test that your camera works:

```bash
libcamera-still -o test.jpg
```

If this creates a `test.jpg` file, your camera is working.

### Step 3: Install Python Dependencies

Navigate to the web application folder and install the required packages:

```bash
cd web_app
pip install -r requirements.txt
```

This installs Flask (the web framework) and Pillow (for image processing).

If you're on the Raspberry Pi and want to run the capture service:

```bash
cd ../raspberry_pi
pip install -r requirements.txt --only-binary=all
```

The `--only-binary=all` flag speeds up installation significantly on Raspberry Pi.

---

## Running IdentifAI

### Starting the Web Server

From the project root directory:

```bash
cd web_app
python app.py
```

You should see output like:

```
 * Running on http://127.0.0.1:5001
```

**Leave this terminal window open.** The server must keep running for the web interface to work.

### Accessing the Web Interface

Open your web browser and go to:

- **http://localhost:5001** - If viewing on the same computer running the server
- **http://[PI-IP-ADDRESS]:5001** - If viewing from another device on the network

To find your Raspberry Pi's IP address, run `hostname -I` in a terminal.

### What You'll See

**Home Page (Camera Feed):**
- A large black area showing the latest camera frame
- Buttons to capture snapshots, toggle fullscreen, and refresh the stream
- Status information showing connection state and uptime

**Dashboard Page:**
- Click "View Dashboard" in the top right
- Shows statistics and a gallery area (currently empty due to face detection not working)
- An activity feed sidebar

---

## Starting the Camera Capture Service

To have the system automatically capture images, open a **second terminal window** and run:

```bash
cd raspberry_pi
python capture.py
```

This will:
1. Initialize the camera
2. Take a photo every 30 seconds
3. Save it to the web interface for display

You should see output like:

```
Starting Raspberry Pi capture service...
Face detection: ENABLED
Capture interval: 30 seconds
Camera ready - capturing real images
```

**Note:** Even though it says "Face detection: ENABLED", this feature does not work correctly. The capture service will still capture and display images.

### Running Without a Camera

If you don't have a camera connected (for testing on a regular computer):

1. Open `raspberry_pi/config.py`
2. Find the line `DEMO_MODE = False`
3. Change it to `DEMO_MODE = True`
4. Save the file
5. Run `python capture.py`

In demo mode, the system creates placeholder files instead of actual camera captures.

---

## Configuration Options

### Web App Settings (`web_app/config.py`)

| Setting | Default | What it does |
|---------|---------|--------------|
| `CAMERA_WIDTH` | 640 | Width of displayed images in pixels |
| `CAMERA_HEIGHT` | 480 | Height of displayed images in pixels |
| `MAX_CONTENT_LENGTH` | 16MB | Maximum upload file size |

### Capture Settings (`raspberry_pi/config.py`)

| Setting | Default | What it does |
|---------|---------|--------------|
| `CAPTURE_INTERVAL` | 30 | Seconds between automatic captures |
| `BACKEND_URL` | http://localhost:5001 | Where to send captured images |
| `DEMO_MODE` | False | Set to True to run without a real camera |
| `ENABLE_FACE_DETECTION` | True | Ignored (feature not working) |

---

## Troubleshooting

### "Address already in use" Error

Another program is using port 5001. Either:
- Close the other program, or
- Change the port in `web_app/app.py` on the last line: `app.run(debug=False, port=5002, ...)`

### Camera Not Detected

1. Check the ribbon cable is firmly connected at both ends
2. The blue side of the ribbon should face the Ethernet port on the Pi
3. Run `libcamera-still -o test.jpg` to test independently
4. If the camera works with libcamera but not with IdentifAI, reboot the Pi

### Web Page Shows "Waiting for camera..."

This means the capture service isn't running or hasn't captured a frame yet:
1. Make sure `capture.py` is running in a separate terminal
2. Wait 30 seconds for the first capture
3. Click the "Refresh" button on the web interface

### Dashboard is Empty

This is expected. The face detection feature that would populate the dashboard is not functional. The dashboard UI exists but has no data to display.

### Images Not Loading on Dashboard

If you previously had the system running and images were saved, they may not display due to path configuration issues. This is a known limitation of the current implementation.

---

## Stopping the System

To stop IdentifAI:

1. In the terminal running `capture.py`, press **Ctrl+C**
2. In the terminal running `app.py`, press **Ctrl+C**

The system will shut down gracefully.

---

## File Locations

After running, you'll find:

- **Captured images:** `web_app/static/images/`
- **Latest frame:** `web_app/static/images/latest_frame.jpg`
- **Activity log:** `web_app/data/activity_log.json`
- **Database:** `web_app/data/events.db`
- **Capture logs:** `raspberry_pi/capture.log`

---

## Quick Reference

| Task | Command |
|------|---------|
| Start web server | `cd web_app && python app.py` |
| Start capture service | `cd raspberry_pi && python capture.py` |
| View camera feed | Open http://localhost:5001 |
| View dashboard | Open http://localhost:5001/dashboard |
| Stop any service | Press Ctrl+C in its terminal |

---

## Getting Help

If you encounter issues not covered in this manual:

1. Check the terminal output for error messages
2. Ensure all dependencies are installed correctly
3. Verify your camera is working with `libcamera-still -o test.jpg`
4. Try rebooting the Raspberry Pi

The system logs detailed information to the terminal, which can help identify problems.
