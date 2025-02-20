# inventory-webapp

## Backend services repo available here
https://github.com/terence-h/inventory-server

## Run this command whenever there's changes
npx @tailwindcss/cli -i ./static/css/input.css -o ./static/css/output.css --watch

## Setup
sudo apt install python3-picamera2 libzbar0 -y
python -m venv --system-site-packages .venv
source .venv/bin/activate
pip install Pillow pyzbar Flask flask-login flask-socketio eventlet python-dateutil qrcode[pil]
python app.py