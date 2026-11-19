#!/bin/zsh
# Double-click to play High Peaks: starts the local game server (if it is not already running) and opens the
# game in your browser. Close this window to stop the server.
cd "$(dirname "$0")"
URL="http://localhost:8755/index.html?sessionID=play&rgs_url=http://localhost:8755&lang=en&device=desktop"
if lsof -nP -iTCP:8755 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "High Peaks is already running."
  open "$URL"
  exit 0
fi
echo "Starting High Peaks... (close this window to stop it)"
( sleep 2; open "$URL" ) &
exec .venv/bin/python rgs/mock_rgs.py
