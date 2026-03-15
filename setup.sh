#!/usr/bin/env bash

set -e

SERVICE_NAME="white-noise-api"
PROJECT_DIR="$(pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
USER_NAME="$(whoami)"

echo "Updating apt packages..."
sudo apt update

echo "Installing Python 3.12..."
sudo apt install -y python3.12 python3.12-venv curl mpg123

echo "Installing uv..."
curl -Ls https://astral.sh/uv/install.sh | sh

# ensure uv is in PATH for this script
export PATH="$HOME/.local/bin:$PATH"

echo "Creating virtual environment..."
uv venv --python 3.12 "$VENV_DIR"

echo "Activating environment..."
source "$VENV_DIR/bin/activate"

echo "Installing project..."
uv pip install "$PROJECT_DIR"

echo "Installing uvicorn..."
uv pip install "uvicorn[standard]"

echo "Creating systemd service..."

SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=White Noise FastAPI Service
After=network.target

[Service]
User=$USER_NAME
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_DIR/bin/uvicorn white_noise.app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "Reloading systemd..."
sudo systemctl daemon-reload

echo "Enabling service..."
sudo systemctl enable $SERVICE_NAME

echo "Starting service..."
sudo systemctl start $SERVICE_NAME

echo ""
echo "========================================"
echo "Setup complete!"
echo "Your FastAPI server is running."
echo ""
echo "Check status:"
echo "  sudo systemctl status $SERVICE_NAME"
echo ""
echo "View logs:"
echo "  journalctl -u $SERVICE_NAME -f"
echo ""
echo "Restart service:"
echo "  sudo systemctl restart $SERVICE_NAME"
echo "========================================"