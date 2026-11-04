#!/usr/bin/env bash
# Start the verifiable-tutor demo from the repository root.
#
# Usage:
#   ./start.sh                 build the browser UI, then run the backend on one origin
#   ./start.sh --dev           run the backend and the Vite dev server together
#   ./start.sh --no-build      skip npm ci and the UI build, then run the backend
#   ./start.sh --preview       build the offline preview demo (no API calls)
#   ./start.sh --port 8001     serve the backend on another port
#   ./start.sh --help          show this message
#
# Requirements: Node 18 or later with npm, the project .venv, and a .env file
# with a non-empty SESSION_SECRET. The UI build writes the ignored
# src/verifiable_tutor/ui/static directory.
#
# The default mode serves the SPA at http://127.0.0.1:8000/ from FastAPI.
# The --dev mode serves the SPA from Vite (usually http://127.0.0.1:5173/)
# and proxies /api to the backend.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB="$ROOT/src/verifiable_tutor/ui/web"
HOST="127.0.0.1"
PORT="8000"
MODE="serve"
BUILD="1"
PREVIEW="0"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dev)
      MODE="dev"
      ;;
    --no-build)
      BUILD="0"
      ;;
    --preview)
      PREVIEW="1"
      ;;
    --port)
      [ "$#" -ge 2 ] || { echo "start.sh: --port needs a value" >&2; exit 2; }
      PORT="$2"
      shift
      ;;
    -h|--help)
      sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "start.sh: unknown option: $1" >&2
      exit 2
      ;;
  esac
  shift
done

fail() {
  echo "start.sh: $*" >&2
  exit 1
}

command -v node >/dev/null 2>&1 || fail "node is not on PATH; install Node 18 or later"
command -v npm >/dev/null 2>&1 || fail "npm is not on PATH"
[ -x "$ROOT/.venv/bin/fastapi" ] || fail "missing .venv/bin/fastapi; create the environment from AGENTS.md"
[ -f "$ROOT/.env" ] || fail "missing .env; copy .env.example to .env and set SESSION_SECRET"
grep -Eq '^[[:space:]]*SESSION_SECRET=[^[:space:]]+' "$ROOT/.env" \
  || fail "SESSION_SECRET is empty in .env; the backend fails closed without it"

install_ui_deps() {
  cd "$WEB"
  if [ ! -d node_modules ] \
    || [ package-lock.json -nt node_modules/.package-lock.json ]; then
    echo "start.sh: installing UI dependencies with npm ci"
    npm ci
  fi
}

if [ "$MODE" = "dev" ]; then
  install_ui_deps

  echo "start.sh: starting the backend on http://$HOST:$PORT"
  cd "$ROOT"
  "$ROOT/.venv/bin/fastapi" dev --host "$HOST" --port "$PORT" &
  BACKEND_PID="$!"
  cleanup() {
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  }
  trap cleanup EXIT INT TERM

  if command -v curl >/dev/null 2>&1; then
    for _ in $(seq 1 30); do
      if curl -fsS "http://$HOST:$PORT/api/health" >/dev/null 2>&1; then
        break
      fi
      sleep 0.5
    done
  fi

  echo "start.sh: starting the Vite dev server; /api proxies to http://$HOST:$PORT"
  cd "$WEB"
  if [ "$PREVIEW" = "1" ]; then
    echo "start.sh: preview demo mode, the browser uses fixture data"
    VITE_PREVIEW=1 npm run dev
  else
    npm run dev
  fi
else
  install_ui_deps
  if [ "$BUILD" = "1" ]; then
    if [ "$PREVIEW" = "1" ]; then
      echo "start.sh: building the offline preview UI into src/verifiable_tutor/ui/static"
      VITE_PREVIEW=1 npm run build
    else
      echo "start.sh: building the UI into src/verifiable_tutor/ui/static"
      npm run build
    fi
  fi
  cd "$ROOT"
  echo "start.sh: serving http://$HOST:$PORT/ (SPA and API on one origin)"
  exec "$ROOT/.venv/bin/fastapi" dev --host "$HOST" --port "$PORT"
fi
