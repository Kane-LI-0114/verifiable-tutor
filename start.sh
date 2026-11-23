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
# Local Langfuse tracing is optional. When Docker is running and the stack is
# installed at ~/tools/langfuse (override with LANGFUSE_DIR), it starts with
# the project. A missing Docker or a failed start prints a warning and the
# project continues without tracing (docs/langfuse-local.md).
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
LANGFUSE_DIR="${LANGFUSE_DIR:-$HOME/tools/langfuse}"
LANGFUSE_URL="${LANGFUSE_URL:-http://127.0.0.1:3000}"

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
      sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'
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

start_langfuse() {
  if [ ! -f "$LANGFUSE_DIR/docker-compose.yml" ]; then
    echo "start.sh: Langfuse stack not found at $LANGFUSE_DIR; skipping local tracing (see docs/langfuse-local.md)" >&2
    return
  fi
  if ! command -v docker >/dev/null 2>&1; then
    echo "start.sh: docker is not on PATH; skipping local tracing" >&2
    return
  fi
  if ! docker info >/dev/null 2>&1; then
    echo "start.sh: Docker is not running; skipping local tracing (start Docker Desktop to enable it)" >&2
    return
  fi

  echo "start.sh: starting local Langfuse from $LANGFUSE_DIR"
  if ! (cd "$LANGFUSE_DIR" && docker compose up -d postgres clickhouse redis minio langfuse-web langfuse-worker); then
    echo "start.sh: Langfuse failed to start; continuing without local tracing" >&2
    return
  fi

  if ! command -v curl >/dev/null 2>&1; then
    echo "start.sh: Langfuse containers started at $LANGFUSE_URL"
    return
  fi
  for _ in $(seq 1 15); do
    if curl -fsS --max-time 2 "$LANGFUSE_URL/api/public/ready" >/dev/null 2>&1; then
      echo "start.sh: Langfuse is ready at $LANGFUSE_URL"
      return
    fi
    sleep 2
  done
  echo "start.sh: Langfuse is starting but not ready yet; tracing will catch up at $LANGFUSE_URL" >&2
}

if [ "$PREVIEW" = "1" ]; then
  echo "start.sh: preview mode; skipping local Langfuse tracing"
else
  start_langfuse
fi

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
