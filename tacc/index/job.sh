#!/usr/bin/env bash
# TACC BGE-M3 embedding-index job (1 GPU, 59 minutes).
#
# One submitted job embeds every chunk of one index request: it reads the
# manifest and input JSONL from USERDIR, loads BGE-M3 from $HOME/models/bge-m3
# (downloading the weights through the Hugging Face mirror on first use),
# encodes on the GPU, and writes vectors.npy, row_map.jsonl and summary.json to
# USERDIR. The local driver validates and stores the vectors; this job only
# computes them.
#
# Env knobs: PUBLIC_ROOT, HF_ENDPOINT.
set -u
export PS1="${PS1:-}"

HERE="${TACC_WORKDIR:-$(cd "$(dirname "$0")" && pwd)}"
USERDIR="${TACC_USERDIR:-$HOME}"
JOB="${SLURM_JOB_ID:-manual}"
JOB_STARTED_EPOCH=$(date +%s)
PUBLIC_ROOT="${PUBLIC_ROOT:-/mnt/home/public/course-envs/CSIT6000V/project/qwen3.8-27b-v1}"
REQUEST_FILE="$HERE/request.json"

if [ ! -f "$REQUEST_FILE" ]; then
    echo "[fatal] no request.json next to job.sh"
    exit 2
fi
REQ_OUT=$(sed -n 's/.*"out_dir"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$REQUEST_FILE")
OUT="${REQ_OUT:-$USERDIR/index/manual-$JOB}"
mkdir -p "$OUT/logs"
LOG="$OUT/logs/index-${JOB}.log"
: > "$LOG"
exec > >(tee -a "$LOG") 2>&1

# A later submit from the same account re-syncs TACC_WORKDIR; keep this job's
# own copy of its scripts so a running job never loses them.
JOBHOME="$OUT/jobhome-${JOB}"
mkdir -p "$JOBHOME"
cp -a "$HERE/." "$JOBHOME/" 2>/dev/null || true
HERE="$JOBHOME"
REQUEST_FILE="$HERE/request.json"

cleanup() {
    local rc=$?
    trap - EXIT INT TERM
    echo "--- gpu after ---"
    nvidia-smi --query-gpu=index,memory.used --format=csv 2>&1 || true
    echo "=== vt-index job done date=$(date -Is) rc=$rc ==="
    exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

echo "=== vt-index embedding job ==="
echo "job=$JOB host=$(hostname) date=$(date -Is)"
echo "task_dir=$HERE out=$OUT"
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
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
echo "HF_ENDPOINT=$HF_ENDPOINT"

nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader,nounits -l 2 > "$OUT/logs/vram-${JOB}.csv" 2>&1 &
VRAM_PID=$!

DEADLINE=$(( JOB_STARTED_EPOCH + 3300 ))
echo "--- embedding ---"
qwen-python "$HERE/index_worker.py" \
    --request "$REQUEST_FILE" \
    --job-id "$JOB" \
    --job-started-epoch "$JOB_STARTED_EPOCH" \
    --deadline-epoch "$DEADLINE" \
    --userdir "$USERDIR"
WORKER_RC=$?
echo "[worker] exit=$WORKER_RC"

if [ -n "${VRAM_PID:-}" ]; then kill "$VRAM_PID" 2>/dev/null || true; fi
VRAM_PEAK=""
if [ -f "$OUT/logs/vram-${JOB}.csv" ]; then
    VRAM_PEAK=$(awk -F, '{gsub(/ /, ""); if ($1 + 0 > peak) peak = $1 + 0} END {print peak + 0}' "$OUT/logs/vram-${JOB}.csv")
fi
echo "vram_peak_mib=$VRAM_PEAK"
echo "summary: $OUT/summary.json"
cat "$OUT/summary.json" 2>/dev/null | head -40 || true
exit "$WORKER_RC"
