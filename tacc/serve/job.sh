#!/usr/bin/env bash
# TACC Qwen knowledge-base job (2 GPUs, 59 minutes).
#
# One submitted job serves the course Qwen model inside the job, generates
# knowledge cards for one chunk batch through the local OpenAI endpoint, writes
# records, progress and a summary to USERDIR, and exits. There is no inbound
# service and no SSH forwarding: the local driver uploads the request, submits
# this job, polls it, and downloads the results.
#
# Env knobs: PUBLIC_ROOT, VLLM_PORT, VLLM_READY_TIMEOUT.
set -u
export PS1="${PS1:-}"

HERE="${TACC_WORKDIR:-$(cd "$(dirname "$0")" && pwd)}"
cd "$HERE"
PUBLIC_ROOT="${PUBLIC_ROOT:-/mnt/home/public/course-envs/CSIT6000V/project/qwen3.8-27b-v1}"
JOB="${SLURM_JOB_ID:-manual}"
JOB_STARTED_EPOCH=$(date +%s)
VLLM_PORT="${VLLM_PORT:-8000}"
SERVER_URL="http://127.0.0.1:${VLLM_PORT}/v1"
SERVED_NAME="qwen3.8-27b"
REQUEST_FILE="$HERE/request.json"
LOG="$HERE/job-${JOB}.log"
: > "$LOG"
exec > >(tee -a "$LOG") 2>&1

# A later submit from the same account re-syncs TACC_WORKDIR; keep this job's
# own copy of its scripts and prompts so a running job never loses them.
JOBHOME="${TMPDIR:-/tmp}/vt-kb-job-${JOB}"
mkdir -p "$JOBHOME"
cp -a "$HERE/." "$JOBHOME/" 2>/dev/null || true
HERE="$JOBHOME"
REQUEST_FILE="$HERE/request.json"
LOG="$JOBHOME/job-${JOB}.log"
touch "$LOG"

VLLM_PID=""
LAUNCHER=""
READY_EPOCH=""

cleanup() {
    local rc=$?
    trap - EXIT INT TERM
    if [ -n "$VLLM_PID" ]; then kill "$VLLM_PID" 2>/dev/null || true; fi
    pkill -f "vllm serve" 2>/dev/null || true
    pkill -f "EngineCore" 2>/dev/null || true
    sleep 2
    echo "--- gpu after ---"
    nvidia-smi --query-gpu=index,memory.used --format=csv 2>&1 || true
    echo "=== qwen knowledge-base job done date=$(date -Is) rc=$rc ==="
    exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

echo "=== qwen knowledge-base job ==="
echo "job=$JOB host=$(hostname) date=$(date -Is)"
echo "task_dir=$HERE server_url=$SERVER_URL"
ls -la "$HERE" | sed 's/^/  /'

unset CUDA_VISIBLE_DEVICES
echo "--- gpu before ---"
nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv 2>&1 || true

echo "--- activating public environment ---"
set +u
# shellcheck disable=SC1090
source "$PUBLIC_ROOT/activate.sh"
ACTIVATE_RC=$?
set -u
if [ "$ACTIVATE_RC" -ne 0 ] || [ -z "${QWEN_RUN_DIR:-}" ]; then
    echo "[fatal] public environment activation failed rc=$ACTIVATE_RC"
    exit 1
fi
echo "QWEN_PROJECT_ROOT=$QWEN_PROJECT_ROOT"
echo "QWEN_MODEL_PATH=$QWEN_MODEL_PATH"
echo "QWEN_RUN_DIR=$QWEN_RUN_DIR"

wait_for_server() {
    local budget_s=$1
    local started
    started=$(date +%s)
    while true; do
        if curl -sf -m 3 "$SERVER_URL/models" > /dev/null 2>&1; then
            READY_EPOCH=$(date +%s)
            echo "[server] ready after $(( READY_EPOCH - started ))s on the waited attempt"
            return 0
        fi
        if [ -n "$VLLM_PID" ] && ! kill -0 "$VLLM_PID" 2>/dev/null; then
            echo "[server] launcher exited before readiness"
            return 1
        fi
        if [ $(( $(date +%s) - started )) -ge "$budget_s" ]; then
            echo "[server] not ready after ${budget_s}s"
            return 1
        fi
        sleep 5
    done
}

start_server() {
    local launcher=$1
    shift
    LAUNCHER="$launcher"
    echo "[server] starting with launcher=$launcher"
    "$@" > "$HERE/server-${JOB}.log" 2>&1 &
    VLLM_PID=$!
    wait_for_server "${VLLM_READY_TIMEOUT:-900}"
}

stop_server() {
    if [ -n "$VLLM_PID" ]; then kill "$VLLM_PID" 2>/dev/null || true; fi
    pkill -f "vllm serve" 2>/dev/null || true
    pkill -f "EngineCore" 2>/dev/null || true
    sleep 2
    VLLM_PID=""
}

LAUNCHED=0
if [ -f "$PUBLIC_ROOT/serve.sh" ]; then
    if start_server "serve.sh" bash "$PUBLIC_ROOT/serve.sh"; then
        LAUNCHED=1
    else
        echo "[server] serve.sh path failed; tail:"
        tail -40 "$HERE/server-${JOB}.log" 2>/dev/null | sed 's/^/  /'
        stop_server
    fi
fi
if [ "$LAUNCHED" -eq 0 ]; then
    start_server "direct" \
        qwen-run "$PUBLIC_ROOT/vllm-env/bin/vllm" serve "$QWEN_MODEL_PATH" \
        --served-model-name "$SERVED_NAME" \
        --host 127.0.0.1 --port "$VLLM_PORT" \
        --tensor-parallel-size 2 \
        --max-model-len 32768 \
        --max-num-seqs 4 \
        --gpu-memory-utilization 0.85 \
        --trust-remote-code || {
            echo "[server] direct start failed; tail:"
            tail -40 "$HERE/server-${JOB}.log" 2>/dev/null | sed 's/^/  /'
            exit 1
        }
fi
if [ -z "$READY_EPOCH" ]; then
    echo "[fatal] server never became ready"
    exit 1
fi
VLLM_STARTUP=$(( READY_EPOCH - JOB_STARTED_EPOCH ))
DEADLINE=$(( JOB_STARTED_EPOCH + 3300 ))
echo "[server] launcher=$LAUNCHER startup_seconds=$VLLM_STARTUP deadline_in=$(( DEADLINE - $(date +%s) ))s"
curl -s -m 5 "$SERVER_URL/models" | head -c 500 || true
echo

echo "--- generating knowledge records ---"
qwen-python "$HERE/kb_worker.py" \
    --request "$REQUEST_FILE" \
    --server-url "$SERVER_URL" \
    --model "$SERVED_NAME" \
    --job-id "$JOB" \
    --job-started-epoch "$JOB_STARTED_EPOCH" \
    --vllm-ready-epoch "$READY_EPOCH" \
    --launcher "$LAUNCHER" \
    --userdir "${TACC_USERDIR:-$HOME}" \
    --deadline-epoch "$DEADLINE"
WORKER_RC=$?
echo "[worker] exit=$WORKER_RC"
if [ "$WORKER_RC" -ne 0 ]; then
    exit "$WORKER_RC"
fi
exit 0
