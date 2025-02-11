# app.py
import datetime
from flask import Flask, Response, render_template, redirect, session, url_for, request, flash, jsonify
import flask
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from picamera2 import Picamera2
from pyzbar.pyzbar import decode
from PIL import Image, ImageDraw, ImageFont
from dateutil import parser
import io
import requests
import json
import threading

from buzz import buzz

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key

socketio = SocketIO(app, async_mode='threading')

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

# API Server URL
API_URL = 'http://192.168.18.90:5201/api'  # Replace with your backend API URL

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        password = request.form.get('password')

        # Authenticate user via .NET API
        response = requests.post(f'{API_URL}/account/login', json={'username': username, 'password': password}, verify=False)

        if response.status_code == 200:
            user_id = response.json().get('Username')
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
    session.pop('_flashes', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    session.pop('_flashes', None)

    categories_response = requests.get(f'{API_URL}/Category/getcategories')
    categories = categories_response.json() if categories_response.status_code == 200 else []

    query_params = {
        'productNo': request.args.get('productNo'),
        'productName': request.args.get('productName'),
        'manufacturer': request.args.get('manufacturer'),
        'batchNo': request.args.get('batchNo'),
        'quantity': request.args.get('quantity'),
        'categoryId': request.args.get('categoryId'),
        'mfgDateFrom': request.args.get('mfgDateFrom'),
        'mfgDateTo': request.args.get('mfgDateTo'),
        'mfgExpiryDateFrom': request.args.get('mfgExpiryDateFrom'),
        'mfgExpiryDateTo': request.args.get('mfgExpiryDateTo'),
        'addedOn': request.args.get('addedOn'),
        'page': request.args.get('page')
    }

    # Remove any parameters that are None or empty
    query_params = {k: v for k, v in query_params.items() if v}

    # Pass the parameters to the API call
    response = requests.get(f'{API_URL}/Product/getProducts', params=query_params)
    data = response.json() if response.status_code == 200 else []

    products = data.get('items', [])
    current_page = data.get('currentPage', 1)
    total_pages = data.get('totalPages', 1)

    return render_template('index.html',
                           products=products,
                           categories=categories,
                           current_page=current_page,
                           total_pages=total_pages)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        # Get form data
        form_data = request.form.to_dict()

        try:
            form_data['quantity'] = int(form_data.get('quantity', 0))
        except (json.JSONDecodeError, ValueError) as e:
            flash('Invalid input data.', 'danger')
            return redirect(url_for('add'))

        # Send data to .NET API
        response = requests.post(f'{API_URL}/Product/addproduct', json=form_data)

        if response.status_code == 200:
            flash('Product added successfully.', 'success')
            return redirect(url_for('index'))
        else:
            json_message = json.loads(response.text)
            message = json_message['message'] if 'message' in json_message and json_message['message'] is not None else 'Failed to add product.'
            flash(message, 'danger')
    
    # Get categories from API
    categories_response = requests.get(f'{API_URL}/Category/getcategories')
    categories = categories_response.json() if categories_response.status_code == 200 else []

    return render_template('add.html', categories=categories)

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

        valid_qr_detected = False  # Flag to check if a valid QR code is detected
        qr_data = {}

        for obj in decoded_objects:
            # Parse JSON data from QR code
            try:
                qr_data = json.loads(obj.data.decode('utf-8'))
                productNo = qr_data.get('productNo')
                productName = qr_data.get('productName')
                manufacturer = qr_data.get('manufacturer')
                batch_no = qr_data.get('batchNo')
                quantity = qr_data.get('quantity')
                category_id = qr_data.get('categoryId')
                mfg_date_original = qr_data.get('mfgDate')
                mfg_expiry_original = qr_data.get('mfgExpiryDate', '')
                mfg_date = convert_to_input_date_format(mfg_date_original)
                mfg_expiry = convert_to_input_date_format(mfg_expiry_original) if mfg_expiry_original else ''

                # Example: Automatically add to inventory
                # response = requests.post(f'{API_URL}/products', json=qr_data)

                valid_qr_detected = True  # Set flag if valid JSON is detected

            except json.JSONDecodeError:
                error = 'Invalid QR Code'

            # # Get bounding box coordinates
            # (x, y, w, h) = obj.rect
            # # Draw rectangle around QR code
            # draw.rectangle([(x, y), (x + w, y + h)], outline="green", width=2)
            # # Annotate the QR code with decoded data
            # text = f"ID: {product_id}\nBatch: {batch_no}"
            # draw.text((x, y - 10), text, fill="green", font=font)

        if valid_qr_detected:
            # Emit SocketIO event to notify client
            data_to_emit = {
                'productNo': productNo,
                'productName': productName,
                'manufacturer': manufacturer,
                'batchNo': batch_no,
                'quantity': quantity,
                'categoryId': category_id,
                'mfgDate': mfg_date,
                'mfgExpiryDate': mfg_expiry
            }
            socketio.emit('qr_detected', {'data': data_to_emit})
            buzz()
            break

        # Convert PIL Image to JPEG
        buf = io.BytesIO()
        image.save(buf, format='JPEG')
        frame = buf.getvalue()

        # Yield frame in byte format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def convert_to_input_date_format(date_str):
    if not date_str:
        return ""
    try:
        parsed_date = parser.isoparse(date_str)
        return parsed_date.strftime("%Y-%m-%d")
    except (ValueError, TypeError) as e:
        return ""

if __name__ == '__main__':
    try:
        # app.run(host='0.0.0.0', port=5000)
        # threading.Thread(target=background_gen_frames, daemon=True).start()
        socketio.run(app, host='0.0.0.0', port=5000)
    finally:
        picam2.close()