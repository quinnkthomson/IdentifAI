# IdentifAI - Design Document

## Overview

IdentifAI was intended to be a face detection system using a Raspberry Pi and camera module. The original goal was to capture images, detect faces using OpenCV, and display results on a web dashboard. The face detection component did not work as planned, so the final product is a live camera streaming system.

## Architecture

The project uses two separate services that communicate over HTTP:

1. **Capture Service** (`raspberry_pi/capture.py`) - Runs on the Raspberry Pi, controls the camera, and captures images every 30 seconds.

2. **Web Application** (`web_app/app.py`) - A Flask server that receives images and serves the web interface.

We separated these because camera access on Raspberry Pi is unreliable—if the camera crashes, we didn't want it to take down the web server too. This also means the web server could theoretically run on a different computer than the Pi.

## Video Streaming

For the live feed, we used MJPEG streaming. This works by sending a continuous stream of JPEG images to the browser:

```python
def generate_frames():
    while True:
        with open(LATEST_FRAME_PATH, 'rb') as f:
            frame = f.read()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.1)
```

The browser displays this as a video without needing JavaScript or WebSockets. We added caching so the file is only re-read when it actually changes, reducing unnecessary disk reads.

## What Went Wrong

The face detection using OpenCV failed for several reasons:

1. **Installation issues** - OpenCV is difficult to install on Raspberry Pi. The pip package has compatibility problems, and compiling from source takes hours.

2. **Path synchronization** - The capture service and web app disagreed on where images were stored. Detection events were logged with paths that the template couldn't find.

3. **Cascading complexity** - Each fix revealed new problems. The system had too many interconnected parts (capture → detection → database → template), and debugging was difficult.

## What Works

The streaming works because it's simple: `capture.py` saves a file, `app.py` reads that file. No database, no detection, no complex path handling. The lesson is that we should have built and tested this simple version first before adding complexity.

## Files

- `capture.py` handles all camera interaction
- `app.py` serves the web interface and receives uploads
- `database.py` stores detection events (unused in practice)
- `cv_model.py` contains face detection code (non-functional)
- Templates use Jinja2 inheritance with `base.html` as the parent

## Reflection

If we were to redo this project, we would start with just the streaming functionality and verify it worked before adding face detection. We also might have used a cloud-based detection API instead of trying to run OpenCV locally on the Pi.
