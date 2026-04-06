#!/usr/bin/env bash
set -euo pipefail

HOST_ADDRESS="${HOST_ADDRESS:-127.0.0.1}"
PORT="${PORT:-5000}"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3 first." >&2
  exit 1
fi

# Install OS prerequisites (Debian/Raspberry Pi OS)
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3-venv python3-pip
fi

VENV_DIR="$PROJECT_ROOT/.venv"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f "$PROJECT_ROOT/.env" ]; then
  cat <<'EOF'
Missing .env file in project root. Create one with: TEAM_NUMBER, DEFAULT_YEAR, BASE_URL, API_KEY
Example:
TEAM_NUMBER=1234
DEFAULT_YEAR=2026
BASE_URL=https://www.thebluealliance.com/api/v3
API_KEY=YOUR_TBA_KEY
EOF
  exit 1
fi

export FLASK_APP="app.py"
export FLASK_ENV="development"
export FLASK_RUN_HOST="$HOST_ADDRESS"
export FLASK_RUN_PORT="$PORT"

URL="http://${HOST_ADDRESS}:${PORT}/"

echo "Starting Flask at: $URL"

# Try to open in a browser if a GUI + browser is present.
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
elif command -v chromium-browser >/dev/null 2>&1; then
  chromium-browser "$URL" >/dev/null 2>&1 &
elif command -v chromium >/dev/null 2>&1; then
  chromium "$URL" >/dev/null 2>&1 &
elif command -v firefox >/dev/null 2>&1; then
  firefox "$URL" >/dev/null 2>&1 &
else
  echo "No browser opener found. Open this URL manually: $URL"
fi

flask run
