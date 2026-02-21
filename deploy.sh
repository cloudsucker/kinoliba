#!/bin/bash
set -e

# ===== GENERATE RUSSIAN LOCALE =====
echo "Ensuring Russian locale is available..."
sudo locale-gen ru_RU.UTF-8
sudo update-locale LANG=ru_RU.UTF-8
export LANG=ru_RU.UTF-8
export LC_ALL=ru_RU.UTF-8

# ===== VARIABLES =====
APP_NAME="kinoliba"
PROJECT_DIR="$HOME/$APP_NAME"
PYTHON_BIN="/usr/bin/python3"
SYSTEMD_FILE="/etc/systemd/system/$APP_NAME.service"
ENV_FILE="$PROJECT_DIR/.env"

cd "$PROJECT_DIR"

# ===== STOP SERVICE IF RUNNING (redeploy) =====
if systemctl is-active --quiet "$APP_NAME" 2>/dev/null; then
  echo "Stopping running $APP_NAME service..."
  sudo systemctl stop "$APP_NAME"
fi

# ===== CHECK .ENV =====
if [ ! -f "$ENV_FILE" ]; then
  echo ".env not found — creating from .env.example..."
  cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
  chmod 600 "$ENV_FILE"

  read -p "Enter your BotFather token: " BOT_TOKEN
  sed -i "s|BOT_TOKEN=.*|BOT_TOKEN=$BOT_TOKEN|" "$ENV_FILE"

  while true; do
    read -sp "Enter bot passphrase: " PASS1; echo
    read -sp "Confirm passphrase:   " PASS2; echo
    if [ "$PASS1" = "$PASS2" ] && [ -n "$PASS1" ]; then
      sed -i "s|BOT_PASSPHRASE=.*|BOT_PASSPHRASE=$PASS1|" "$ENV_FILE"
      break
    else
      echo "Passphrases do not match or are empty. Try again."
    fi
  done

  read -p "OpenRouter API key (leave empty to skip AI features): " OR_KEY
  if [ -n "$OR_KEY" ]; then
    sed -i "s|OPENROUTER_API_KEY=.*|OPENROUTER_API_KEY=$OR_KEY|" "$ENV_FILE"
  fi

  echo ".env saved at $ENV_FILE"
else
  echo ".env already exists — skipping interactive setup."
fi

# ===== ENSURE PERMISSIONS =====
chown -R "$(whoami)":"$(whoami)" "$PROJECT_DIR"
chmod 600 "$ENV_FILE"

# ===== UPDATE CODE =====
echo "Updating codebase from GitHub..."
git pull origin main

# ===== VIRTUAL ENV =====
echo "Checking virtual environment..."
if [ ! -d ".venv" ]; then
  if ! python3 -m venv --help >/dev/null 2>&1; then
    echo "python3-venv is missing. Installing..."
    sudo apt update
    sudo apt install -y python3-venv
  fi
  echo "Creating virtual environment..."
  $PYTHON_BIN -m venv .venv
fi

echo "Installing requirements..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# ===== SYSTEMD UNIT =====
echo "Creating/updating systemd unit..."
sudo tee "$SYSTEMD_FILE" > /dev/null <<EOL
[Unit]
Description=Telegram Bot Kinoliba
After=network.target

[Service]
User=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/python3 $PROJECT_DIR/main.py
Restart=always
EnvironmentFile=$ENV_FILE
Environment="PATH=$PROJECT_DIR/.venv/bin:/usr/bin:/bin"
Environment="LANG=ru_RU.UTF-8"
Environment="LC_ALL=ru_RU.UTF-8"

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl enable "$APP_NAME"
sudo systemctl restart "$APP_NAME"

echo "Deployment complete!"
