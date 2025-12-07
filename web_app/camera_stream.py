# import io
# import time
# from picamera2 import Picamera2
# from flask import Flask, Response

# app = Flask(__name__)
# picam2 = Picamera2()

# # Configure the camera for video streaming (640x480 is good for low latency)
# picam2.configure(picam2.create_video_configuration(main={"size": (640, 480)}))
# picam2.start()
# time.sleep(2)

# def generate_frames():
#     """Generates JPEG frames from the camera for the web stream."""
#     while True:
#         # Capture the frame as a JPEG image in memory
#         buffer = io.BytesIO()
#         picam2.capture_file(buffer, format='jpeg')
#         frame = buffer.getvalue()

#         # Yield the frame using the multipart boundary required for video streaming
#         yield (b'--frame\r\n'
#                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# @app.route('/video_feed')
# def video_feed():
#     """Route to serve the raw video feed to the HTML image tag."""
#     return Response(generate_frames(),
#                     mimetype='multipart/x-mixed-replace; boundary=frame')

# @app.route('/')
# def index():
#     """Route for the main web page (the viewer)."""
#     return """
#     <html>
#         <head>
#             <title>Pi Camera Stream</title>
#         </head>
#         <body>
#             <h1>Raspberry Pi Camera Stream</h1>
#             <img src="/video_feed" />
#         </body>
#     </html>
#     """

# if __name__ == '__main__':
#     # Run the Flask app on port 8000, accessible from any device on the network (0.0.0.0)
#     app.run(host='0.0.0.0', port=8000, debug=False)
