import base64
import os
import time
from datetime import datetime
import json
from io import BytesIO
from threading import Thread, Lock
from flask import Flask, render_template, request, jsonify, url_for, Response
from werkzeug.utils import secure_filename
from PIL import Image
from datetime import timezone
from database import init_db, log_face_event, get_face_events_with_faces, get_face_detection_stats
from config import CAMERA_WIDTH, CAMERA_HEIGHT, VIDEO_BITRATE, MAX_CONTENT_LENGTH
import config as app_config

# Imports for Camera and Video Recording
# NOTE: You must have 'picamera2[full]' installed for the encoders to work:
# pip install picamera2[full]
try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder, Quality
    from picamera2.outputs import FfmpegOutput
    CAMERA_AVAILABLE = True
except ImportError as e:
    print(f"picamera2 or its dependencies not found: {e}")
    CAMERA_AVAILABLE = False
    class Picamera2:
        def __init__(self, *args, **kwargs): pass
        def configure(self, *args, **kwargs): pass
        def create_video_configuration(self, *args, **kwargs): return {}
        def start(self, *args, **kwargs): pass
        def capture_file(self, *args, **kwargs): pass
        def stop(self): pass
    class H264Encoder:
        def __init__(self, *args, **kwargs): pass
    class FfmpegOutput:
        def __init__(self, *args, **kwargs): pass

# Initialize Flask application and settings
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
app = Flask(__name__, template_folder=template_dir)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
# Define asset directories
VIDEO_DIR = os.path.join(app.static_folder, 'videos')
IMAGES_DIR = os.path.join(app.static_folder, 'images')
ACTIVITY_LOG_PATH = os.path.join(os.path.dirname(__file__), 'data', 'activity_log.json')
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
if not os.path.exists(ACTIVITY_LOG_PATH):
    with open(ACTIVITY_LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump({"activities": []}, f)

# Camera State Variables
picam2 = None
encoder = None
output = None
recording_thread = None
is_recording = False
recording_filename = None
camera_lock = Lock()  # Use a lock to safely manage camera access


def init_camera():
    """Camera is managed by capture.py - web app doesn't initialize camera."""
    # Camera initialization disabled to avoid conflicts with capture.py
    # This prevents startup delays and camera access conflicts
    global picam2
    picam2 = None
    app.logger.info("Camera initialization skipped - managed by capture.py service")


# Don't initialize camera automatically - let capture.py handle it
# This prevents camera conflicts and startup delays
# Camera will be initialized only when explicitly needed (if capture.py isn't running)
# init_camera()  # Disabled to avoid conflicts with capture.py


def _load_activities():
    """Load activity list tolerating legacy array format."""
    try:
        if not os.path.exists(ACTIVITY_LOG_PATH):
            return []
        with open(ACTIVITY_LOG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data[:100]  # Limit to 100 entries for performance
            if isinstance(data, dict):
                activities = data.get("activities", [])
                return activities[:100]  # Limit to 100 entries
    except Exception as e:
        app.logger.warning(f"Failed to load activities: {e}")
    return []


def _compute_time_ago(ts_str):
    try:
        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = now - ts
        secs = int(delta.total_seconds())
        if secs < 0:
            secs = 0
        if secs < 60:
            return f"{secs}s ago"
        mins = secs // 60
        if mins < 60:
            return f"{mins}m ago"
        hours = mins // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        return f"{days}d ago"
    except Exception:
        return ""


def log_activity(activity_type, description, image=None):
    entry = {
        "type": activity_type,
        "description": description,
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    }
    if image:
        entry["image"] = image

    try:
        activities = _load_activities()
        activities.insert(0, entry)
        activities = activities[:100]
        with open(ACTIVITY_LOG_PATH, 'w', encoding='utf-8') as f:
            json.dump({"activities": activities}, f)
    except Exception as e:
        app.logger.warning(f"Failed to write activity log: {e}")

@app.route('/')
def home():
    return render_template('index.html', is_recording=is_recording, config=app_config)


@app.route('/dashboard')
def dashboard():
    face_events_data = []
    stats = {'face_events': 0, 'total_faces': 0, 'total_events': 0}
    
    try:
        # Get face detection events (only those with faces detected, limited for performance)
        face_events = get_face_events_with_faces(limit=30)

        # Convert to format expected by template
        for event in face_events:
            try:
                # Handle image path - extract just the filename
                image_path = event["image_path"] if event["image_path"] else ""
                # Remove 'images/' prefix if present
                if image_path.startswith("images/"):
                    filename = image_path[7:]  # Remove "images/" prefix
                else:
                    filename = os.path.basename(image_path)
                
                # Only add if we have a valid filename
                if filename:
                    face_events_data.append({
                        "id": event["id"],
                        "file": filename,
                        "timestamp": event["timestamp"],
                        "face_count": event["face_count"],
                        "source": event["source"]
                    })
            except Exception as e:
                app.logger.warning(f"Error processing event: {e}")
                continue

        # Get statistics
        stats = get_face_detection_stats()

    except Exception as e:
        app.logger.error(f"Dashboard error: {e}")

    return render_template('dashboard.html', face_events=face_events_data, stats=stats)


# --- Video Streaming Functions ---

LATEST_FRAME_PATH = os.path.join(IMAGES_DIR, 'latest_frame.jpg')

def generate_frames():
    """Serves the latest captured frame as a responsive stream."""
    last_mtime = 0
    last_frame = None
    placeholder_sent = False
    
    while True:
        try:
            # Check if latest frame exists
            if os.path.exists(LATEST_FRAME_PATH):
                try:
                    current_mtime = os.path.getmtime(LATEST_FRAME_PATH)
                    
                    # Only read file if it's been modified or we haven't read it yet
                    if current_mtime != last_mtime or last_frame is None:
                        with open(LATEST_FRAME_PATH, 'rb') as f:
                            frame = f.read()
                        
                        if len(frame) > 100:  # Sanity check for valid JPEG
                            last_frame = frame
                            last_mtime = current_mtime
                            placeholder_sent = False
                    
                    # Always yield the last valid frame
                    if last_frame:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + last_frame + b'\r\n')
                except (IOError, OSError):
                    # File might be being written, skip this iteration
                    pass
            else:
                # Show placeholder only once, then keep serving it
                if not placeholder_sent or last_frame is None:
                    width, height = CAMERA_WIDTH, CAMERA_HEIGHT
                    img = Image.new('RGB', (width, height), color='#1a1a1a')
                    
                    try:
                        from PIL import ImageDraw, ImageFont
                        draw = ImageDraw.Draw(img)
                        try:
                            font = ImageFont.load_default()
                        except:
                            font = None
                        
                        if font:
                            messages = ["Waiting for camera...", "", "Start capture.py to see live feed"]
                            y = height // 2 - 30
                            for msg in messages:
                                if msg:
                                    draw.text((width // 4, y), msg, fill='#888888', font=font)
                                y += 25
                    except:
                        pass
                    
                    img_io = BytesIO()
                    img.save(img_io, 'JPEG', quality=85)
                    last_frame = img_io.getvalue()
                    placeholder_sent = True
                
                if last_frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + last_frame + b'\r\n')
            
            # Fast polling for responsive feel (0.1s = 10fps max)
            time.sleep(0.1)
            
        except Exception as e:
            app.logger.error(f"Stream error: {e}")
            time.sleep(0.5)

@app.route('/video_feed')
def video_feed():
    """Return the latest captured frame as a stream."""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/save_snapshot', methods=['POST'])
def save_snapshot():
    ts = datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S-%fZ')
    filename = secure_filename(f"snapshot-{ts}.jpg")
    path = os.path.join(IMAGES_DIR, filename)

    try:
        if 'file' in request.files:
            file = request.files['file']
            file.save(path)
        else:
            data = request.get_json(silent=True) or {}
            image_b64 = data.get('image', '')
            if image_b64.startswith('data:image'):
                image_b64 = image_b64.split(',', 1)[1]
            img_bytes = base64.b64decode(image_b64)
            with open(path, 'wb') as f:
                f.write(img_bytes)

        log_activity('snapshot', f'Snapshot saved: {filename}', image=f'images/{filename}')

        return jsonify({"success": True, "url": url_for('static', filename=f'images/{filename}')})
    except Exception as e:
        app.logger.error(f"Failed to save snapshot: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/pi_capture', methods=['POST'])
def pi_capture():
    """Receive image and face detection data from Raspberry Pi"""
    try:
        # Get form data
        timestamp = request.form.get('timestamp')
        source = request.form.get('source', 'raspberry_pi')
        faces_detected = request.form.get('faces_detected', 'false').lower() == 'true'
        face_count = int(request.form.get('face_count', '0'))

        # Save uploaded file
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400

        # Generate secure filename with timestamp
        ts = datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S-%fZ')
        filename = secure_filename(f"pi_capture_{ts}.jpg")
        filepath = os.path.join(IMAGES_DIR, filename)

        # Save the file
        file.save(filepath)

        # Log face detection event in database
        image_path = f'images/{filename}'
        log_face_event(timestamp, image_path, faces_detected, face_count, source)

        # Log activity
        if faces_detected:
            log_activity('face_detected', f'Face detected: {face_count} faces in image', image=image_path)
            app.logger.info(f"Face detection event logged: {face_count} faces in {filename}")
        else:
            log_activity('image_captured', f'Image captured from {source}', image=image_path)
            app.logger.info(f"Image captured from {source}: {filename}")

        return jsonify({"success": True, "message": "Image and detection data received"}), 201

    except Exception as e:
        app.logger.error(f"Failed to process Pi capture: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/activity_log')
def activity_log():
    try:
        activities = _load_activities()
        enriched = []
        # Limit processing to first 50 for performance
        for act in activities[:50]:
            try:
                ts = act.get('timestamp') or datetime.utcnow().isoformat() + 'Z'
                time_ago = _compute_time_ago(ts)
                enriched.append({**act, "time_ago": time_ago, "timestamp": ts})
            except Exception as e:
                app.logger.warning(f"Error processing activity: {e}")
                continue
        return jsonify({"activities": enriched})
    except Exception as e:
        app.logger.error(f"Activity log error: {e}")
        return jsonify({"activities": []})

# --- New Video Recording Functions ---

@app.route('/start_recording', methods=['POST'])
def start_recording():
    """Recording is handled by capture.py, not the web app"""
    return jsonify({'message': 'Recording managed by capture.py service'}), 200

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    """Recording is handled by capture.py, not the web app"""
    return jsonify({'message': 'Recording managed by capture.py service'}), 200

# Initialize database on startup (non-blocking)
try:
    with app.app_context():
        init_db()
        app.logger.info("Database initialized successfully")
except Exception as e:
    app.logger.error(f"Database initialization error: {e}")

# Run the application
if __name__ == '__main__':
    # Explicitly disable reloader to prevent double camera init and busy device errors
    app.run(debug=False, port=5001, threaded=True, use_reloader=False)