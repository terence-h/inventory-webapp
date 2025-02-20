# inventory-webapp

## Run this command whenever there's changes
npx @tailwindcss/cli -i ./static/css/input.css -o ./static/css/output.css --watch

## Install necessary libraries
sudo apt install python3-picamera2 libzbar0 -y

## Create Python virtual env with system wide packages (.venv)
python -m venv --system-site-packages .venv

## Activate the virtual environment to ensure installing to correct venv
source .venv/bin/activate
pip install Pillow pyzbar Flask flask-login flask-socketio eventlet python-dateutil qrcode[pil]

## Enable Tailwind CSS watch to detect any change to HTML files
npx @tailwindcss/cli -i ./static/css/input.css 	o ./static/css/output.css --watch

## To run the program:
python app.py