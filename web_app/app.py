import os
import time
from datetime import datetime
import json
import shutil
from io import BytesIO
from threading import Thread, Lock
from flask import Flask, render_template, request, jsonify, url_for, send_file, Response
from werkzeug.utils import secure_filename
from PIL import Image

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
# Define video directory
VIDEO_DIR = os.path.join(app.static_folder, 'videos')
os.makedirs(VIDEO_DIR, exist_ok=True)

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
    global picam2, CAMERA_AVAILABLE
    if not CAMERA_AVAILABLE or picam2 is not None:
        return

    # Only init in the main serving process; skip the reloader parent
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    try:
        cam = Picamera2()
        video_config = cam.create_video_configuration(main={"size": (640, 480)}, encode="main")
        cam.configure(video_config)
        cam.start()
        time.sleep(2)
        picam2 = cam
        app.logger.info("Camera initialized successfully for streaming and recording.")
    except Exception as e:
        app.logger.warning(f"Camera initialization failed: {e}, using placeholder.")
        picam2 = None
        CAMERA_AVAILABLE = False


# Initialize camera if this is the serving process
init_camera()

# Placeholder for your database/activity log imports (as they are not provided, using minimal needed)
def log_activity(activity_type, description):
    app.logger.info(f"Activity Log - {activity_type}: {description}") # Simple print for placeholder

# Define a route for the root URL ('/')
@app.route('/')
def home():
    # Placeholder for a basic index page that can include controls
    return render_template('index.html', is_recording=is_recording)

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

# --- New Video Recording Functions ---

@app.route('/start_recording', methods=['POST'])
def start_recording():
    global picam2, is_recording, recording_filename, encoder, output

    if not CAMERA_AVAILABLE:
        return jsonify({'error': 'Camera not available'}), 503

    if is_recording:
        return jsonify({'message': 'Already recording'}), 200

    try:
        # 1. Setup the recording file path
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
        recording_filename = secure_filename(f'video-{timestamp}.mp4')
        video_path = os.path.join(VIDEO_DIR, recording_filename)

        # 2. Configure the encoder and output
        with camera_lock:
            encoder = H264Encoder(10000000) # 10 Mbps bitrate
            output = FfmpegOutput(video_path)
            
            # 3. Start the recording
            picam2.start_encoder(encoder, output, quality=Quality.HIGH)
            is_recording = True
            log_activity('recording_start', f'Started recording to {recording_filename}')
            app.logger.info(f"Recording started: {video_path}")
            
            return jsonify({
                'success': True, 
                'message': 'Recording started',
                'filename': recording_filename,
                'url': url_for('static', filename=f'videos/{recording_filename}')
            }), 200

    except Exception as e:
        app.logger.error(f'Failed to start recording: {e}')
        # Clean up in case of failure
        if picam2 and encoder:
             try: picam2.stop_encoder() 
             except: pass
        is_recording = False
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global picam2, is_recording, recording_filename, encoder, output

    if not is_recording:
        return jsonify({'message': 'Not currently recording'}), 200

    if not CAMERA_AVAILABLE or picam2 is None:
        is_recording = False # Reset state
        return jsonify({'error': 'Camera not available'}), 503

    try:
        # 1. Stop the encoder
        with camera_lock:
            picam2.stop_encoder()
        
        # 2. Reset state variables
        filename = recording_filename
        is_recording = False
        recording_filename = None
        encoder = None
        output = None

        log_activity('recording_stop', f'Stopped recording and saved {filename}')
        app.logger.info(f"Recording stopped and saved as: {filename}")
        
        return jsonify({
            'success': True, 
            'message': 'Recording stopped and saved',
            'filename': filename,
            'url': url_for('static', filename=f'videos/{filename}')
        }), 200

    except Exception as e:
        app.logger.error(f'Failed to stop recording: {e}')
        # Attempt to reset state even on error
        is_recording = False 
        recording_filename = None
        encoder = None
        output = None
        return jsonify({'success': False, 'error': str(e)}), 500

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