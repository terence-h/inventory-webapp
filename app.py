# app.py
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from picamera2 import Picamera2
from pyzbar.pyzbar import decode
from PIL import Image, ImageDraw, ImageFont
import io
import requests
import json

from buzz import buzz

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Dummy user for authentication
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# User loader callback
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Initialize Picamera2
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": "RGB888", "size": (640, 480)}))
picam2.start()

buzz(0.2)

# API Server URL
API_URL = 'http://BACKEND_PC_IP:PORT/api'  # Replace with your backend API URL

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        password = request.form.get('password')

        # Authenticate user via .NET API
        response = requests.post(f'{API_URL}/login', json={'username': username, 'password': password})

        if response.status_code == 200:
            user_id = response.json().get('user_id')
            user = User(user_id)
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        # Get form data
        product_json = request.form.get('product_json')
        quantity = request.form.get('quantity')

        try:
            product_data = json.loads(product_json)
            product_data['quantity'] = int(quantity)
        except (json.JSONDecodeError, ValueError) as e:
            flash('Invalid input data.', 'danger')
            return redirect(url_for('add'))

        # Send data to .NET API
        response = requests.post(f'{API_URL}/products', json=product_data)

        if response.status_code == 201:
            flash('Product added successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Failed to add product.', 'danger')

    return render_template('add.html')

@app.route('/update/<product_id>', methods=['GET', 'POST'])
@login_required
def update(product_id):
    if request.method == 'POST':
        # Get form data
        product_json = request.form.get('product_json')
        quantity = request.form.get('quantity')

        try:
            product_data = json.loads(product_json)
            product_data['quantity'] = int(quantity)
        except (json.JSONDecodeError, ValueError) as e:
            flash('Invalid input data.', 'danger')
            return redirect(url_for('update', product_id=product_id))

        # Send update request to .NET API
        response = requests.put(f'{API_URL}/products/{product_id}', json=product_data)

        if response.status_code == 200:
            flash('Product updated successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Failed to update product.', 'danger')

    # Fetch existing product data
    response = requests.get(f'{API_URL}/products/{product_id}')
    if response.status_code == 200:
        product = response.json()
    else:
        flash('Product not found.', 'danger')
        return redirect(url_for('index'))

    return render_template('update.html', product=product)

@app.route('/delete/<product_id>', methods=['DELETE'])
@login_required
def delete(product_id):
    # Send delete request to .NET API
    response = requests.delete(f'{API_URL}/products/{product_id}')

    if response.status_code == 200:
        return jsonify({'message': 'Product deleted successfully.'}), 200
    else:
        return jsonify({'message': 'Failed to delete product.'}), 400

@app.route('/video_feed')
@login_required
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_frames():
    while True:
        # Capture frame from Picamera2
        frame = picam2.capture_array()

        # Convert to PIL Image
        image = Image.fromarray(frame)

        # Detect QR codes
        decoded_objects = decode(image)

        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        for obj in decoded_objects:
            # Parse JSON data from QR code
            try:
                qr_data = json.loads(obj.data.decode('utf-8'))
                product_id = qr_data.get('productId')
                batch_no = qr_data.get('batchNo')
                mfg_date = qr_data.get('mfgDate')
                mfg_expiry = qr_data.get('mfgExpiry', '')

                # Optional: Automatically add or check inventory
                # Example: Automatically add to inventory
                # response = requests.post(f'{API_URL}/products', json=qr_data)

            except json.JSONDecodeError:
                product_id = batch_no = mfg_date = mfg_expiry = 'Invalid QR Code'

            # Get bounding box coordinates
            (x, y, w, h) = obj.rect
            # Draw rectangle around QR code
            draw.rectangle([(x, y), (x + w, y + h)], outline="green", width=2)
            # Annotate the QR code with decoded data
            text = f"ID: {product_id}\nBatch: {batch_no}"
            draw.text((x, y - 10), text, fill="green", font=font)

        # Convert PIL Image to JPEG
        buf = io.BytesIO()
        image.save(buf, format='JPEG')
        frame = buf.getvalue()

        # Yield frame in byte format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, threaded=True)
    finally:
        picam2.close()