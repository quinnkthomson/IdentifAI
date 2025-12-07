import base64
import os
import time
from datetime import datetime
import json
import shutil
from io import BytesIO
from threading import Thread, Lock
from flask import Flask, render_template, request, jsonify, url_for, send_file, Response, redirect
from werkzeug.utils import secure_filename
from PIL import Image
from datetime import timezone

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
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
# Define asset directories
VIDEO_DIR = os.path.join(app.static_folder, 'videos')
IMAGES_DIR = os.path.join(app.static_folder, 'images')
ACTIVITY_LOG_PATH = os.path.join(app.static_folder, 'activity_log.json')
VERIFICATION_HISTORY_PATH = os.path.join(app.static_folder, 'verification_history.json')
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
if not os.path.exists(ACTIVITY_LOG_PATH):
    with open(ACTIVITY_LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump({"activities": []}, f)
if not os.path.exists(VERIFICATION_HISTORY_PATH):
    with open(VERIFICATION_HISTORY_PATH, 'w', encoding='utf-8') as f:
        json.dump({"verifications": []}, f)

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
        video_config = cam.create_video_configuration(main={"size": (640, 480)}, encode="main")
        cam.configure(video_config)
        cam.start()
        time.sleep(2)
        picam2 = cam

        # Always-on recording
        recording_filename = secure_filename(f"continuous-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.mp4")
        video_path = os.path.join(VIDEO_DIR, recording_filename)
        encoder = H264Encoder(10000000)
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
    return render_template('index.html', is_recording=is_recording)


@app.route('/dashboard')
def dashboard():
    images = sorted(os.listdir(IMAGES_DIR)) if os.path.exists(IMAGES_DIR) else []
    images = [img for img in images if img.lower().endswith(('.jpg', '.jpeg', '.png'))]
    images = list(reversed(images))

    # Map file -> timestamp from verification history; fallback to file mtime
    history = {}
    try:
        with open(VERIFICATION_HISTORY_PATH, 'r', encoding='utf-8') as vf:
            data = json.load(vf)
            for item in data.get('verifications', []):
                history[os.path.basename(item.get('file', ''))] = item.get('timestamp')
    except Exception:
        pass

    images_with_times = []
    for img in images:
        ts = history.get(img)
        if not ts:
            try:
                mtime = os.path.getmtime(os.path.join(IMAGES_DIR, img))
                ts = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
            except Exception:
                ts = ""
        images_with_times.append({"file": img, "timestamp": ts})

    return render_template('dashboard.html', images=images_with_times)


@app.route('/verification')
def verification():
    return redirect(url_for('dashboard'))

# --- Video Streaming Functions (from your app.py) ---

def generate_frames():
    """Generates JPEG frames from the camera for the web stream."""
    global picam2
    if picam2 is None:
        # Fallback: generate placeholder frames (simplified for brevity)
        while True:
            # Placeholder frame logic (omitted for brevity, use your full placeholder logic here)
            # ...
            # Generate a simple black frame for the placeholder
            width, height = 640, 480
            img = Image.new('RGB', (width, height), color='#1a1a1a')
            img_io = BytesIO()
            img.save(img_io, 'JPEG', quality=85)
            frame = img_io.getvalue()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.5)
    else:
        # Real camera stream
        while True:
            with camera_lock: # Safely access the camera
                buffer = BytesIO()
                # Use the main stream's configuration for the capture
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

        try:
            with open(VERIFICATION_HISTORY_PATH, 'r+', encoding='utf-8') as vf:
                data = json.load(vf)
                items = data.get('verifications', [])
                items.insert(0, {
                    "file": f'images/{filename}',
                    "timestamp": datetime.utcnow().isoformat() + 'Z'
                })
                items = items[:100]
                vf.seek(0)
                json.dump({"verifications": items}, vf)
                vf.truncate()
        except Exception as e:  # best-effort
            app.logger.warning(f"Failed to update verification history: {e}")

        return jsonify({"success": True, "url": url_for('static', filename=f'images/{filename}')})
    except Exception as e:
        app.logger.error(f"Failed to save snapshot: {e}")
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
            encoder = H264Encoder(10000000)
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

# Placeholder for your database init (to prevent errors)
def init_db():
    pass

# Initialize database on startup
with app.app_context():
    init_db()

# Run the application
if __name__ == '__main__':
    # Explicitly disable reloader to prevent double camera init and busy device errors
    app.run(debug=False, port=5001, threaded=True, use_reloader=False)