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
    """Lazily initialize the camera once, avoiding double-start from the reloader."""
    global picam2, CAMERA_AVAILABLE, encoder, output, is_recording, recording_filename
    if not CAMERA_AVAILABLE or picam2 is not None:
        return

    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    try:
        cam = Picamera2()
        video_config = cam.create_video_configuration(main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT)}, encode="main")
        cam.configure(video_config)
        cam.start()
        time.sleep(2)
        picam2 = cam

        # Always-on recording
        recording_filename = secure_filename(f"continuous-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.mp4")
        video_path = os.path.join(VIDEO_DIR, recording_filename)
        encoder = H264Encoder(VIDEO_BITRATE)
        output = FfmpegOutput(video_path)
        picam2.start_encoder(encoder, output, quality=Quality.HIGH)
        is_recording = True
        app.logger.info("Camera initialized and continuous recording started.")
    except Exception as e:
        app.logger.warning(f"Camera initialization failed: {e}, using placeholder.")
        picam2 = None
        CAMERA_AVAILABLE = False


# Initialize camera if this is the serving process
init_camera()


def _load_activities():
    """Load activity list tolerating legacy array format."""
    try:
        with open(ACTIVITY_LOG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("activities", [])
    except Exception:
        pass
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
    # Get face detection events (only those with faces detected)
    face_events = get_face_events_with_faces(limit=100)

    # Convert to format expected by template
    face_events_data = []
    for event in face_events:
        face_events_data.append({
            "id": event["id"],
            "file": event["image_path"].replace("images/", ""),
            "timestamp": event["timestamp"],
            "face_count": event["face_count"],
            "source": event["source"]
        })

    # Get statistics
    stats = get_face_detection_stats()

    return render_template('dashboard.html', face_events=face_events_data, stats=stats)


# --- Video Streaming Functions (from your app.py) ---

def generate_frames():
    """Generates JPEG frames from the camera for the web stream."""
    global picam2
    if picam2 is None:
        # Generate a placeholder frame with helpful message
        width, height = CAMERA_WIDTH, CAMERA_HEIGHT
        img = Image.new('RGB', (width, height), color='#2a2a2a')

        try:
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)

            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            except:
                font = ImageFont.load_default()

            messages = [
                "Camera Stream Unavailable",
                "",
                "The camera is currently being used by",
                "the face detection capture service.",
                "",
                "To view live video:",
                "1. Stop capture.py (Ctrl+C)",
                "2. Refresh this page"
            ]

            y_offset = 50
            for message in messages:
                if message == "":
                    y_offset += 10
                    continue
                bbox = draw.textbbox((0, 0), message, font=font)
                text_width = bbox[2] - bbox[0]
                x = (width - text_width) // 2
                draw.text((x, y_offset), message, fill='white', font=font)
                y_offset += 25

        except ImportError:
            pass

        img_io = BytesIO()
        img.save(img_io, 'JPEG', quality=85)
        frame = img_io.getvalue()

        while True:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(5)  # Update every 5 seconds
    else:
        # Real camera stream
        while True:
            with camera_lock:
                buffer = BytesIO()
                picam2.capture_file(buffer, format='jpeg')
            frame = buffer.getvalue()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """Return the video stream from the camera."""
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
    activities = _load_activities()
    enriched = []
    for act in activities:
        ts = act.get('timestamp') or datetime.utcnow().isoformat() + 'Z'
        time_ago = _compute_time_ago(ts)
        enriched.append({**act, "time_ago": time_ago, "timestamp": ts})
    return jsonify({"activities": enriched})

# --- New Video Recording Functions ---

@app.route('/start_recording', methods=['POST'])
def start_recording():
    global picam2, is_recording, recording_filename, encoder, output
    if not CAMERA_AVAILABLE or picam2 is None:
        return jsonify({'error': 'Camera not available'}), 503

    if is_recording:
        return jsonify({'message': 'Already recording', 'filename': recording_filename}), 200

    # If recording ever stopped, restart it
    try:
        with camera_lock:
            recording_filename = secure_filename(f"continuous-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.mp4")
            video_path = os.path.join(VIDEO_DIR, recording_filename)
            encoder = H264Encoder(VIDEO_BITRATE)
            output = FfmpegOutput(video_path)
            picam2.start_encoder(encoder, output, quality=Quality.HIGH)
            is_recording = True
            log_activity('recording_start', f'Recording resumed: {recording_filename}')
        return jsonify({'success': True, 'filename': recording_filename}), 200
    except Exception as e:
        app.logger.error(f'Failed to start recording: {e}')
        is_recording = False
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global picam2, is_recording, recording_filename, encoder, output
    return jsonify({'message': 'Recording is always on; stop not permitted'}), 405

# Initialize database on startup
with app.app_context():
    init_db()

# Run the application
if __name__ == '__main__':
    # Explicitly disable reloader to prevent double camera init and busy device errors
    app.run(debug=False, port=5001, threaded=True, use_reloader=False)