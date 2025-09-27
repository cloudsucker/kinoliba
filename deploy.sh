#!/bin/bash
set -e

# ===== VARIABLES =====
APP_NAME="kinoliba"
PROJECT_DIR="/opt/$APP_NAME"
PYTHON_BIN="/usr/bin/python3"
SYSTEMD_FILE="/etc/systemd/system/$APP_NAME.service"
TOKEN_FILE="$PROJECT_DIR/bot/data/token.txt"
PASSPHRASE_FILE="$PROJECT_DIR/bot/data/passphrase.txt"

cd "$PROJECT_DIR"

# ===== CHECK TOKEN =====
if [ ! -f "$TOKEN_FILE" ]; then
  echo "Token file not found!"
  mkdir -p "$(dirname "$TOKEN_FILE")"
  read -p "Please enter your BotFather token: " BOT_TOKEN
  echo "$BOT_TOKEN" > "$TOKEN_FILE"
  chmod 600 "$TOKEN_FILE"
  echo "Token saved to $TOKEN_FILE"
fi

# ===== CHECK PASSPHRASE =====
if [ ! -f "$PASSPHRASE_FILE" ]; then
  echo "Passphrase file not found!"
  mkdir -p "$(dirname "$PASSPHRASE_FILE")"
  
  while true; do
    read -p "Please enter a passphrase for the bot: " PASS1
    read -p "Confirm passphrase: " PASS2
    if [ "$PASS1" = "$PASS2" ] && [ -n "$PASS1" ]; then
      echo "$PASS1" > "$PASSPHRASE_FILE"
      chmod 600 "$PASSPHRASE_FILE"
      echo "Passphrase saved to $PASSPHRASE_FILE"
      break
    else
      echo "Passphrases do not match or are empty. Please try again."
    fi
  done
fi

# ===== ENSURE OWNERSHIP =====
# Все файлы бота принадлежат текущему пользователю
chown -R $(whoami):$(whoami) "$PROJECT_DIR/bot"
chmod 700 "$PROJECT_DIR/bot/data"

# ===== UPDATE CODE =====
echo "Updating codebase from GitHub..."
git pull origin production

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
if [ ! -f "$SYSTEMD_FILE" ]; then
  echo "Creating systemd unit..."
  sudo tee $SYSTEMD_FILE > /dev/null <<EOL
[Unit]
Description=Telegram Bot Kinoliba
After=network.target

[Service]
User=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/python3 $PROJECT_DIR/main.py
Restart=always
Environment="PATH=$PROJECT_DIR/.venv/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
EOL

  sudo systemctl daemon-reload
  sudo systemctl enable $APP_NAME
  sudo systemctl start $APP_NAME
else
  echo "Restarting systemd unit..."
  sudo systemctl restart $APP_NAME
fi

echo "Bot deployment completed successfully!"
