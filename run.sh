# Created using ChatGPT
#!/bin/bash

# Check if the .venv folder exists
if [ -d ".venv" ]; then
    echo ".venv exists. Activating and running the application."
    source .venv/bin/activate
    python app.py --ip 192.168.18.90:5201
else
    echo ".venv not found. Installing dependencies and setting up the environment."
    sudo apt install -y ca-certificates curl gnupg
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/nodesource.gpg
    echo "deb [signed-by=/usr/share/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" | sudo tee /etc/apt/sources.list.d/nodesource.list
    sudo apt update -y
    sudo apt install nodejs -y
    sudo apt install python3-picamera2 libzbar0 -y
    python -m venv --system-site-packages .venv
    source .venv/bin/activate
    pip install Pillow pyzbar Flask flask-login flask-socketio eventlet python-dateutil qrcode[pil]
    npm install
    python app.py --ip 192.168.18.90:5201
fi