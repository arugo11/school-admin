#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.demo-runtime"
BACKEND_PID_FILE="$RUNTIME_DIR/backend.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.pid"
BACKEND_LOG="$RUNTIME_DIR/backend.log"
FRONTEND_LOG="$RUNTIME_DIR/frontend.log"

mkdir -p "$RUNTIME_DIR"

if [[ -f "$ROOT_DIR/.env.local" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env.local"
  set +a
fi

is_running() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if [[ -n "${pid}" ]] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
    rm -f "$pid_file"
  fi
  return 1
}

wait_for_http() {
  local url="$1"
  local label="$2"
  for _ in $(seq 1 40); do
    if python3 - <<PY >/dev/null 2>&1
import urllib.request
urllib.request.urlopen("${url}", timeout=1)
PY
    then
      echo "$label ready: $url"
      return 0
    fi
    sleep 0.5
  done
  echo "$label did not become ready: $url" >&2
  return 1
}

if [[ ! -x "$ROOT_DIR/.venv/bin/python" ]]; then
  echo "Missing backend venv at $ROOT_DIR/.venv" >&2
  exit 1
fi

if ! is_running "$BACKEND_PID_FILE"; then
  (
    cd "$ROOT_DIR"
    setsid env PYTHONPATH=backend "$ROOT_DIR/.venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 \
      >"$BACKEND_LOG" 2>&1 < /dev/null &
    echo $! >"$BACKEND_PID_FILE"
  )
fi

if ! is_running "$FRONTEND_PID_FILE"; then
  (
    cd "$ROOT_DIR/frontend"
    setsid env VITE_API_BASE=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 4173 \
      >"$FRONTEND_LOG" 2>&1 < /dev/null &
    echo $! >"$FRONTEND_PID_FILE"
  )
fi

wait_for_http "http://127.0.0.1:8000/api/health" "backend"
wait_for_http "http://127.0.0.1:4173/students" "frontend"

echo
echo "Backend:  http://127.0.0.1:8000"
echo "Frontend: http://127.0.0.1:4173/students"
echo "Logs:"
echo "  $BACKEND_LOG"
echo "  $FRONTEND_LOG"
