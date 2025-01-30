# app.py

from flask import Flask, render_template, Response
from picamera2 import Picamera2
from PIL import Image, ImageDraw, ImageFont
from pyzbar.pyzbar import decode
import io

app = Flask(__name__)

# Initialize Picamera2
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)}))
picam2.start()

def gen_frames():
    while True:
        # Capture frame from Picamera2
        frame = picam2.capture_array()

        # Convert frame to PIL Image
        image = Image.fromarray(frame)

        # Detect QR codes in the image
        decoded_objects = decode(image)

        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        for obj in decoded_objects:
            # Get bounding box coordinates
            (x, y, w, h) = obj.rect
            # Draw rectangle around QR code
            draw.rectangle([(x, y), (x + w, y + h)], outline="green", width=2)
            # Annotate the QR code with decoded data
            qr_data = obj.data.decode('utf-8')
            qr_type = obj.type
            text = f"{qr_data} ({qr_type})"
            draw.text((x, y - 10), text, fill="green", font=font)

        # Convert PIL Image to JPEG
        buf = io.BytesIO()
        image.save(buf, format='JPEG')
        frame = buf.getvalue()

        # Yield frame in byte format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, threaded=True)
    finally:
        picam2.close()
