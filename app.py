# app.py
import atexit
from flask import Flask, Response, render_template, redirect, session, url_for, request, flash, jsonify
from flask_socketio import SocketIO
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin
from picamera2 import Picamera2
from pyzbar.pyzbar import decode
from PIL import Image
from dateutil import parser
import io
import requests
import json
import base64

from buzz import buzz, cleanup_gpio, create_buzzer
from generate_qr_code import generate_qr_code

atexit.register(cleanup_gpio)
create_buzzer()

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

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
            user_id = response.json().get('username')
            user = User(user_id)
            login_user(user)
            session.pop('_flashes', None)
            session['username'] = user_id
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

    data = {
        'username': session['username']
    }
    requests.post(f'{API_URL}/Account/logout', json=data)
    session['username'] = None

    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    # session.pop('_flashes', None)

    categories_response = requests.get(f'{API_URL}/Category/getcategories')
    categories = categories_response.json() if categories_response.status_code == 200 else []

    query_params = {
        'productNo': request.args.get('productNo'),
        'productName': request.args.get('productName'),
        'manufacturer': request.args.get('manufacturer'),
        'batchNo': request.args.get('batchNo'),
        'quantityFrom': request.args.get('quantityFrom'),
        'quantityTo': request.args.get('quantityTo'),
        'categoryId': request.args.get('categoryId'),
        'mfgDateFrom': request.args.get('mfgDateFrom'),
        'mfgDateTo': request.args.get('mfgDateTo'),
        'mfgExpiryDateFrom': request.args.get('mfgExpiryDateFrom'),
        'mfgExpiryDateTo': request.args.get('mfgExpiryDateTo'),
        # 'addedOn': request.args.get('addedOn'),
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

@app.route('/logs')
@login_required
def logs():
    session.pop('_flashes', None)

    categories_response = requests.get(f'{API_URL}/Audit/getAuditTypes')
    categories = categories_response.json() if categories_response.status_code == 200 else []

    query_params = {
        'auditLogId': request.args.get('auditLogId'),
        'auditTypeId': request.args.get('auditTypeId'),
        'actionBy': request.args.get('actionBy'),
        'startDate': request.args.get('dateFrom'),
        'endDate': request.args.get('dateTo'),
        'page': request.args.get('page')
    }

    # Remove any parameters that are None or empty
    query_params = {k: v for k, v in query_params.items() if v}

    # Pass the parameters to the API call
    response = requests.get(f'{API_URL}/Audit/getAuditLogs', params=query_params)
    data = response.json() if response.status_code == 200 else []

    audit_logs = data.get('items', [])
    current_page = data.get('currentPage', 1)
    total_pages = data.get('totalPages', 1)

    return render_template('logs.html',
                           audit_logs=audit_logs,
                           categories=categories,
                           current_page=current_page,
                           total_pages=total_pages)

@app.route('/logs/view/<auditId>', methods=['GET'])
@login_required
def view_log(auditId):
    session.pop('_flashes', None)

    categories_response = requests.get(f'{API_URL}/Audit/getAuditTypes')
    categories = categories_response.json() if categories_response.status_code == 200 else []

    # Pass the parameters to the API call
    response = requests.get(f'{API_URL}/Audit/getAuditLog/{auditId}')
    data = response.json() if response.status_code == 200 else []

    return render_template('view.html',
                           audit_log=data,
                           categories=categories)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        # Get form data
        form_data = request.form.to_dict()

        for date_field in ['mfgDate', 'mfgExpiryDate']:
            if not form_data.get(date_field):
                form_data[date_field] = None

        try:
            form_data['quantity'] = int(form_data.get('quantity', 0))
            form_data['username'] = session['username']
        except (json.JSONDecodeError, ValueError) as e:
            flash('Invalid input data.', 'danger')
            return redirect(url_for('add'))
        
        # Send data to .NET API
        response = requests.post(f'{API_URL}/Product/addProduct', json=form_data)

        if response.status_code == 200:
            flash('Product added successfully.', 'success')
        else:
            json_message = json.loads(response.text)
            message = json_message['message'] if 'message' in json_message and json_message['message'] is not None else 'Failed to add product.'
            flash(message, 'danger')
    
    # Get categories from API
    categories_response = requests.get(f'{API_URL}/Category/getcategories')
    categories = categories_response.json() if categories_response.status_code == 200 else []

    return render_template('add.html', categories=categories)

@app.route('/edit/<productId>', methods=['GET', 'POST'])
@login_required
def edit(productId):
    if request.method == 'POST':
        # Get form data
        form_data = request.form.to_dict()

        for date_field in ['mfgDate', 'mfgExpiryDate']:
            if not form_data.get(date_field):
                form_data[date_field] = None

        try:
            form_data['productId'] = int(productId)
            form_data['quantity'] = int(form_data.get('quantity', 0))
            form_data['username'] = session['username']
        except (json.JSONDecodeError, ValueError) as e:
            flash('Invalid input data.', 'danger')
            return redirect(url_for('add'))

        # Send data to .NET API
        response = requests.post(f'{API_URL}/Product/editProduct', json=form_data)

        if response.status_code == 200:
            flash('Product updated successfully.', 'success')
        else:
            json_message = json.loads(response.text)
            message = json_message['message'] if 'message' in json_message and json_message['message'] is not None else 'Failed to add product.'
            flash(message, 'danger')

    # Fetch existing product data
    response = requests.get(f'{API_URL}/Product/getProduct/{productId}')
    if response.status_code == 200:
        product = response.json()
    else:
        flash('Product not found.', 'danger')
        return redirect(url_for('index'))
    
    categories_response = requests.get(f'{API_URL}/Category/getcategories')
    categories = categories_response.json() if categories_response.status_code == 200 else []

    return render_template('edit.html', product=product, categories=categories)

@app.route('/delete/<product_id>', methods=['POST'])
@login_required
def delete(product_id):
    form_data = {
        'username': session['username']
    }

    response = requests.post(f'{API_URL}/Product/deleteProduct/{product_id}', json=form_data)
    response_json = response.json()

    if response.status_code == 200:
        flash(response_json['message'], 'success')
    else:
        flash(response_json['message'], 'error')

    return jsonify(response_json), response.status_code

@app.route('/generateqr', methods=['GET', 'POST'])
@login_required
def generateqr():
    if request.method == 'POST':
        # Get form data
        form_data = request.form.to_dict()

        for date_field in ['mfgDate', 'mfgExpiryDate']:
            if not form_data.get(date_field):
                form_data[date_field] = None

        try:
            form_data['quantity'] = int(form_data.get('quantity', 0))
        except (json.JSONDecodeError, ValueError) as e:
            flash('Invalid input data.', 'danger')
            return redirect(url_for('generateqr'))
        
        # Generate QR code image
        img = generate_qr_code(form_data)
        
        # Save image to bytes buffer
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')

        categories_response = requests.get(f'{API_URL}/Category/getcategories')
        categories = categories_response.json() if categories_response.status_code == 200 else []

        return render_template('generateqr.html', 
                             categories=categories,
                             qr_image=img_base64,
                             message='QR code generated successfully')
    
    # Get categories from API
    categories_response = requests.get(f'{API_URL}/Category/getcategories')
    categories = categories_response.json() if categories_response.status_code == 200 else []

    return render_template('generateqr.html', categories=categories)

# @app.route('/qrcode')
# @login_required
# def qr_code():
#     product_data = {
#         "productNo": "BEV-001",
#         "productName": "Cold Brew Coffee",
#         "manufacturer": "Brew Masters",
#         "batchNo": "B2023-06",
#         "quantity": 427,
#         "categoryId": 5,
#         "mfgDate": "2024-09-11",
#         "mfgExpiryDate": "2025-10-26"
#     }
    
#     img = generate_qr_code(product_data)
    
#     img_buffer = io.BytesIO()
#     img.save(img_buffer, format='PNG')
#     img_buffer.seek(0)
    
#     return send_file(img_buffer, mimetype='image/png')

@app.route('/video_feed')
@login_required
def video_feed():
    # picam2.start()
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def gen_frames():
    while True:
        frame = picam2.capture_array()
        image = Image.fromarray(frame)
        decoded_objects = decode(image)

        # draw = ImageDraw.Draw(image)
        # font = ImageFont.load_default()

        valid_qr_detected = False
        qr_data = {}

        for obj in decoded_objects:
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
                valid_qr_detected = True

            except json.JSONDecodeError:
                error = 'Invalid QR Code'

            # (x, y, w, h) = obj.rect
            # # Draw rectangle around QR code
            # draw.rectangle([(x, y), (x + w, y + h)], outline="green", width=2)
            # # Annotate the QR code with decoded data
            # text = f"ID: {product_id}\nBatch: {batch_no}"
            # draw.text((x, y - 10), text, fill="green", font=font)

        if valid_qr_detected:
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

        buf = io.BytesIO()
        image.save(buf, format='JPEG')
        frame = buf.getvalue()

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
        socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)
    finally:
        picam2.close()