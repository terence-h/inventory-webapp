# Created using ChatGPT
#!/bin/bash

# Check if the .venv folder exists
if [ -d ".venv" ]; then
    echo ".venv exists. Activating and running the application."
    source .venv/bin/activate
    python app.py
else
    echo ".venv not found. Installing dependencies and setting up the environment."
    sudo apt install python3-picamera2 libzbar0 -y
    python -m venv --system-site-packages .venv
    source .venv/bin/activate
    pip install Pillow pyzbar Flask flask-login flask-socketio eventlet python-dateutil qrcode[pil]
    npm install
    python app.py
fi