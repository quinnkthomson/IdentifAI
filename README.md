# 🎯 IdentifAI - Raspberry Pi Face Detection System

## Overview

IdentifAI is a face detection system built with a Raspberry Pi 4 and Camera Module 3. The system captures images at regular intervals, detects faces using OpenCV Haar cascades, and displays results through a web dashboard. 

The architecture separates concerns between:
- **Raspberry Pi** (`raspberry_pi/`): Camera capture and face detection
- **Web Application** (`web_app/`): Dashboard, API, and data storage

---

## Features

- 📷 **Automatic Image Capture** - Captures images every 30 seconds
- 👤 **Face Detection** - Uses OpenCV Haar cascades to detect faces
- 🖥️ **Web Dashboard** - View detection events and statistics
- 📊 **Activity Logging** - Tracks all capture and detection events
- 🔄 **Live Feed** - Displays latest captured frame on web interface

---

## Hardware Requirements

- Raspberry Pi 4 (2GB+ RAM recommended)
- Raspberry Pi Camera Module 3 (wide or standard)
- MicroSD card (16GB+)
- Power supply
- Wi-Fi or Ethernet connection

---

## Project Structure

```
IdentifAI/
├── raspberry_pi/           # Camera and detection (runs on Pi)
│   ├── capture.py          # Main capture loop
│   ├── cv_model.py         # Face detection functions
│   ├── config.py           # Pi configuration settings
│   ├── utils.py            # Logging and helper functions
│   ├── requirements.txt    # Pi dependencies
│   ├── test_face_detection.py    # Detection test script
│   └── troubleshoot_camera.py    # Camera diagnostics
│
├── web_app/                # Web interface
│   ├── app.py              # Flask application
│   ├── database.py         # SQLite database functions
│   ├── config.py           # Web app configuration
│   ├── requirements.txt    # Web dependencies
│   ├── static/
│   │   ├── styles.css      # CSS styling
│   │   └── images/         # Captured images stored here
│   ├── templates/
│   │   ├── base.html       # Base template
│   │   ├── index.html      # Camera feed page
│   │   └── dashboard.html  # Detection events dashboard
│   └── data/
│       └── activity_log.json   # Activity feed
│
├── run_identifai.sh        # Convenience startup script
└── README.md
```

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/IdentifAI.git
cd IdentifAI
```

### 2. Enable Camera (Raspberry Pi)

```bash
sudo raspi-config
# Navigate to: Interface Options -> Camera -> Enable
sudo reboot
```

Test the camera:
```bash
libcamera-still -o test.jpg
```

### 3. Install Dependencies

**On Raspberry Pi (for capture service):**
```bash
cd raspberry_pi
pip install -r requirements.txt --only-binary=all
```

**For web application:**
```bash
cd web_app
pip install -r requirements.txt
```

---

## Configuration

### Raspberry Pi Settings (`raspberry_pi/config.py`)

| Setting | Default | Description |
|---------|---------|-------------|
| `CAPTURE_INTERVAL` | 30 | Seconds between captures |
| `BACKEND_URL` | `http://localhost:5001` | Web app URL |
| `ENABLE_FACE_DETECTION` | True | Enable/disable detection |
| `DEMO_MODE` | False | Use mock camera for testing |

---

## Running the System

### Option 1: Run Both Services Manually

**Terminal 1 - Start Web Server:**
```bash
cd web_app
python app.py
```
Web interface available at: `http://localhost:5001`

**Terminal 2 - Start Capture Service:**
```bash
cd raspberry_pi
python capture.py
```

### Option 2: Use Startup Script

```bash
./run_identifai.sh
```

---

## Usage

### Web Interface

- **Camera Feed** (`/`): Shows latest captured frame, updates every 30 seconds
- **Dashboard** (`/dashboard`): View face detection events and statistics

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Camera feed page |
| `/dashboard` | GET | Detection events dashboard |
| `/video_feed` | GET | MJPEG stream of latest frame |
| `/pi_capture` | POST | Receive capture from Pi |
| `/activity_log` | GET | JSON activity feed |

---

## Face Detection Settings

The detection uses OpenCV Haar cascades with tuned parameters to reduce false positives:

```python
scale_factor = 1.3      # Image pyramid scale
min_neighbors = 8       # Required neighbor detections  
minSize = (60, 60)      # Minimum face size in pixels
```

To adjust sensitivity in `cv_model.py`:
- **More detections**: Decrease `min_neighbors` (e.g., 5)
- **Fewer false positives**: Increase `min_neighbors` (e.g., 10)

---

## Troubleshooting

### Camera Not Detected

1. Check ribbon cable orientation (blue side toward Ethernet)
2. Run diagnostics:
```bash
cd raspberry_pi
python troubleshoot_camera.py
```

### Face Detection Not Working

Test the detection module:
```bash
cd raspberry_pi
python test_face_detection.py
```

### Camera Initialization Failed

If you see "camera init sequence did not complete":
1. Check if another process is using the camera
2. Reboot the Pi
3. The system will fall back to mock mode for testing

### OpenCV Installation Issues

Use pre-compiled binaries for faster installation:
```bash
pip install opencv-python-headless --only-binary=all
```

---

## Architecture

The system uses a producer-consumer architecture:

1. **capture.py** (Producer): Captures images, runs face detection, sends to web app
2. **app.py** (Consumer): Receives data, stores in database, serves web interface

**Data Flow:**
```
Camera → capture.py → cv_model.py → /pi_capture API → SQLite DB → Web Dashboard
```

---

## Testing Without Camera

Set `DEMO_MODE = True` in `raspberry_pi/config.py` to use mock camera for development.

---

## License

MIT License
