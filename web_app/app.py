from flask import Flask, render_template, request, jsonify, url_for, send_file
import os
import base64
from datetime import datetime
from werkzeug.utils import secure_filename
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import json
import shutil

# Initialize the Flask application
# Set the template folder to the correct path
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
app = Flask(__name__, template_folder=template_dir)

# Activity log file
ACTIVITY_LOG_FILE = os.path.join(os.path.dirname(__file__), 'static', 'activity_log.json')

def log_activity(activity_type, description):
    """Log an activity event (snapshot, approve, deny)."""
    if not os.path.isdir(os.path.dirname(ACTIVITY_LOG_FILE)):
        os.makedirs(os.path.dirname(ACTIVITY_LOG_FILE), exist_ok=True)
    
    activities = []
    if os.path.isfile(ACTIVITY_LOG_FILE):
        try:
            with open(ACTIVITY_LOG_FILE, 'r') as f:
                activities = json.load(f)
        except:
            activities = []
    
    # Add new activity at the beginning (most recent first)
    activities.insert(0, {
        'type': activity_type,
        'description': description,
        'timestamp': datetime.utcnow().isoformat()
    })
    
    # Keep only the last 50 activities
    activities = activities[:50]
    
    try:
        with open(ACTIVITY_LOG_FILE, 'w') as f:
            json.dump(activities, f, indent=2)
    except Exception as e:
        app.logger.error('Failed to write activity log: %s', e)

# Define a route for the root URL ('/')
@app.route('/')
def home():
    # Use render_template to serve the 'index.html' file
    # Flask automatically looks for templates inside the 'templates'
    # folder within the 'root_path' ('web_app' in this case).
    return render_template('index.html')

# Define a route for the dashboard
@app.route('/dashboard')
def dashboard():
    # Build path to images folder inside static
    images_dir = os.path.join(app.static_folder, 'images')
    images = []
    if os.path.isdir(images_dir):
        # list files (images) sorted by modified time desc
        files = [f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f))]
        files.sort(key=lambda fn: os.path.getmtime(os.path.join(images_dir, fn)), reverse=True)
        images = files
    return render_template('dashboard.html', images=images)


@app.route('/save_snapshot', methods=['POST'])
def save_snapshot():
    """Receive a base64 image (data URL) and save it into static/images."""
    # Support multipart/form-data uploads (preferred) or JSON dataURL fallback.
    images_dir = os.path.join(app.static_folder, 'images')
    os.makedirs(images_dir, exist_ok=True)

    # 1) multipart file upload
    if request.files and 'file' in request.files:
        f = request.files['file']
        filename = secure_filename(f.filename) if f.filename else None
        # ensure an extension
        if not filename or '.' not in filename:
            # guess from content_type
            content_type = f.content_type or ''
            ext = 'jpg' if 'jpeg' in content_type or 'jpg' in content_type else 'png'
            timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%S%f')
            filename = secure_filename(f'snapshot-{timestamp}.{ext}')

        file_path = os.path.join(images_dir, filename)
        try:
            f.save(file_path)
        except Exception as e:
            app.logger.error('Failed to save uploaded file: %s', e)
            return jsonify({'error': 'failed to save', 'details': str(e)}), 500

        image_url = url_for('static', filename=f'images/{filename}')
        app.logger.info('Saved snapshot (multipart): %s', file_path)
        # Log activity
        log_activity('snapshot', f'Snapshot saved: {filename}')
        return jsonify({'filename': filename, 'url': image_url}), 201

    # 2) JSON dataURL fallback (existing behavior)
    data = request.get_json(silent=True)
    if not data or 'image' not in data:
        return jsonify({'error': 'no image provided'}), 400

    data_url = data['image']
    if ',' not in data_url:
        return jsonify({'error': 'invalid data URL'}), 400

    header, encoded = data_url.split(',', 1)
    if 'jpeg' in header or 'jpg' in header:
        ext = 'jpg'
    elif 'png' in header:
        ext = 'png'
    else:
        ext = 'jpg'

    try:
        image_data = base64.b64decode(encoded)
    except Exception as e:
        app.logger.error('Base64 decode error: %s', e)
        return jsonify({'error': 'invalid base64'}), 400

    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%S%f')
    filename = secure_filename(f'snapshot-{timestamp}.{ext}')
    file_path = os.path.join(images_dir, filename)
    try:
        with open(file_path, 'wb') as out:
            out.write(image_data)
    except Exception as e:
        app.logger.error('Failed to save decoded image: %s', e)
        return jsonify({'error': 'failed to save', 'details': str(e)}), 500

    image_url = url_for('static', filename=f'images/{filename}')
    app.logger.info('Saved snapshot (dataURL): %s', file_path)
    # Log activity
    log_activity('snapshot', f'Snapshot saved: {filename}')
    return jsonify({'filename': filename, 'url': image_url}), 201


@app.route('/verification')
def verification():
    """Display the face verification page with saved images."""
    images_dir = os.path.join(app.static_folder, 'images')
    images = []
    if os.path.isdir(images_dir):
        files = [f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f))]
        files.sort(key=lambda fn: os.path.getmtime(os.path.join(images_dir, fn)), reverse=True)
        images = files
    return render_template('verification.html', images=images)


@app.route('/verify_face', methods=['POST'])
def verify_face():
    """Handle face verification approval/denial and move images accordingly."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'error': 'no data provided'}), 400

    image_name = data.get('image')
    decision = data.get('decision')  # 'approve' or 'deny'

    if not image_name or decision not in ['approve', 'deny']:
        return jsonify({'success': False, 'error': 'invalid image or decision'}), 400

    # Verify the file exists in main images folder
    images_dir = os.path.join(app.static_folder, 'images')
    file_path = os.path.join(images_dir, secure_filename(image_name))
    if not os.path.isfile(file_path):
        return jsonify({'success': False, 'error': 'image not found'}), 404

    # Determine destination folder
    dest_folder = 'approved' if decision == 'approve' else 'denied'
    dest_dir = os.path.join(images_dir, dest_folder)
    os.makedirs(dest_dir, exist_ok=True)

    dest_path = os.path.join(dest_dir, image_name)

    # Move the file
    try:
        shutil.move(file_path, dest_path)
        app.logger.info('Moved image to %s: %s', dest_folder, image_name)
        # Log activity
        activity_type = 'approve' if decision == 'approve' else 'deny'
        action_text = 'approved' if decision == 'approve' else 'denied'
        log_activity(activity_type, f'Face {action_text}')
    except Exception as e:
        app.logger.error('Failed to move image: %s', e)
        return jsonify({'success': False, 'error': 'failed to move image', 'details': str(e)}), 500

    # Load verification history (JSON file)
    history_file = os.path.join(app.static_folder, 'verification_history.json')
    history = {}
    if os.path.isfile(history_file):
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
        except:
            history = {}

    # Add entry
    history[image_name] = {
        'decision': decision,
        'timestamp': datetime.utcnow().isoformat()
    }

    # Save history
    try:
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        app.logger.error('Failed to save history: %s', e)

    return jsonify({'success': True, 'message': f'Face {decision} recorded and moved'}), 200


@app.route('/activity_log')
def activity_log():
    """Return the recent activity log with formatted times."""
    activities = []
    if os.path.isfile(ACTIVITY_LOG_FILE):
        try:
            with open(ACTIVITY_LOG_FILE, 'r') as f:
                activities = json.load(f)
        except:
            activities = []
    
    # Format timestamps to "time ago" format
    now = datetime.utcnow()
    formatted = []
    for activity in activities:
        try:
            timestamp = datetime.fromisoformat(activity['timestamp'])
            diff = now - timestamp
            
            if diff.total_seconds() < 60:
                time_ago = 'just now'
            elif diff.total_seconds() < 3600:
                minutes = int(diff.total_seconds() / 60)
                time_ago = f'{minutes} minute{"s" if minutes > 1 else ""} ago'
            elif diff.total_seconds() < 86400:
                hours = int(diff.total_seconds() / 3600)
                time_ago = f'{hours} hour{"s" if hours > 1 else ""} ago'
            else:
                days = int(diff.total_seconds() / 86400)
                time_ago = f'{days} day{"s" if days > 1 else ""} ago'
            
            formatted.append({
                'type': activity['type'],
                'description': activity['description'],
                'time_ago': time_ago
            })
        except:
            pass
    
    return jsonify({'activities': formatted}), 200


@app.route('/verification_summary')
def verification_summary():
    """Return summary of approved and denied images."""
    images_dir = os.path.join(app.static_folder, 'images')
    
    approved = []
    denied = []
    
    # Get approved images
    approved_dir = os.path.join(images_dir, 'approved')
    if os.path.isdir(approved_dir):
        approved = sorted(os.listdir(approved_dir), reverse=True)
    
    # Get denied images
    denied_dir = os.path.join(images_dir, 'denied')
    if os.path.isdir(denied_dir):
        denied = sorted(os.listdir(denied_dir), reverse=True)
    
    return jsonify({
        'approved': approved,
        'denied': denied,
        'total_approved': len(approved),
        'total_denied': len(denied)
    }), 200



@app.route('/video_feed')
def video_feed():
    """Return a placeholder/test image for the video stream."""
    # Create a simple placeholder image with text
    width, height = 640, 480
    img = Image.new('RGB', (width, height), color='#1a1a1a')
    draw = ImageDraw.Draw(img)
    
    # Draw a simple frame border
    border_color = '#444444'
    draw.rectangle([10, 10, width-10, height-10], outline=border_color, width=2)
    
    # Add placeholder text
    text = "Camera Stream\n(Placeholder - No Camera Connected)"
    text_color = '#999999'
    # Try to use a default font; fall back to default if not available
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Arial.ttf', 24)
    except:
        font = ImageFont.load_default()
    
    # Draw text centered
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    draw.text((x, y), text, fill=text_color, font=font)
    
    # Convert image to bytes
    img_io = BytesIO()
    img.save(img_io, 'JPEG', quality=85)
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/jpeg')

# Run the application
if __name__ == '__main__':
    # Change port to 5001 to avoid conflicts
    app.run(debug=True, port=5001)