#!/usr/bin/env bash
# TACC environment mechanics spike (CPU only).
#
# Verifies, in one submitted job:
#   1. node and scheduler facts (scontrol time limit, cpu, memory, disk),
#   2. the public Python 3.12 environment and its PRoot userland runtime,
#   3. the MPI toolchain from the assignment 1 public environment,
#   4. the project-layer bootstrap: uv download and a hash-keyed cached install,
#   5. imports of the project delta (pypdfium2, pytest, paddle, paddleocr, cv2),
#   6. SQLite FTS5 and a real page render from a course PDF,
#   7. model availability on the Hugging Face mirror and optional weight download,
#   8. a CPU-only PP-DocLayoutV2 layout probe,
#   9. cross-job reuse: the same bootstrap call a second time must be instant.
#
# All outputs go to $TACC_USERDIR/env-spike so they survive the job.
set -u
export PS1="${PS1:-}"

HERE="${TACC_WORKDIR:-$(cd "$(dirname "$0")" && pwd)}"
OUT="${TACC_USERDIR:-$HOME}/env-spike"
PDF_DIR="${TACC_USERDIR:-$HOME}/corpus-pdf"
PUBLIC_ROOT="${PUBLIC_ROOT:-/mnt/home/public/course-envs/CSIT6000V/project/qwen3.8-27b-v1}"
MPI_ACTIVATE="/mnt/home/public/course-envs/CSIT6000V/assignment1/activate.sh"
JOB="${SLURM_JOB_ID:-manual}"
mkdir -p "$OUT"
# A resubmission must not inherit or probe the previous run's images/results.
rm -rf "$OUT/rendered" "$OUT/layout"
rm -f "$OUT/summary.json" "$OUT/checks.json" "$OUT/layout.json"
mkdir -p "$OUT/rendered" "$OUT/layout"
LOG="$OUT/env-spike-${JOB}.log"
: > "$LOG"
exec > >(tee -a "$LOG") 2>&1

PASS=0
FAIL=0
CRITICAL=0
RESULTS="$OUT/results-${JOB}.txt"
: > "$RESULTS"
record() {
    local status=$1 name=$2 detail=${3:-}
    printf '%s|%s|%s\n' "$status" "$name" "$detail" >> "$RESULTS"
    if [ "$status" = PASS ]; then PASS=$((PASS + 1)); else FAIL=$((FAIL + 1)); fi
    printf '[result] %s %s %s\n' "$status" "$name" "$detail"
}
critical() { CRITICAL=$((CRITICAL + 1)); }
run_proot() { bash "$PUBLIC_ROOT/runtime.sh" "$@"; }

# PaddleX only resolves local model dirs here; keep any residual network probe
# off the slow path and point downloads at the mirror.
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export PADDLE_PDX_CACHE_HOME="$HOME/models/paddlex"
export PADDLE_PDX_MODEL_SOURCE="${PADDLE_PDX_MODEL_SOURCE:-huggingface}"
export PADDLE_PDX_HUGGING_FACE_ENDPOINT="${PADDLE_PDX_HUGGING_FACE_ENDPOINT:-https://hf-mirror.com}"
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK="${PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK:-True}"

echo "=== environment mechanics spike ==="
echo "job=$JOB host=$(hostname) date=$(date -Is)"
echo "task_dir=$HERE"
echo "userdir=${TACC_USERDIR:-<unset>} slurm_userlog=${TACC_SLURM_USERLOG:-<unset>}"
echo "requirements=$(sha256sum "$HERE/_staged/requirements.txt" 2>/dev/null | cut -c1-16)"
echo "task_dir_files:"; ls -la "$HERE" | sed 's/^/  /'
echo

# ---------------------------------------------------------------- 1. node facts
echo "===== 1. node and scheduler facts ====="
if command -v scontrol >/dev/null 2>&1; then
    scontrol show job "$SLURM_JOB_ID" 2>&1 | sed -n '1,40p'
    echo
    scontrol show partition tacc 2>&1 | grep -E "PartitionName|MaxTime|MaxNodes|TotalCPUs|State" || true
    if scontrol show job "$SLURM_JOB_ID" 2>/dev/null | grep -q "JobId=$SLURM_JOB_ID"; then
        record PASS scontrol "$(scontrol show job "$SLURM_JOB_ID" 2>/dev/null | grep -o 'TimeLimit=[^ ]*' | head -1)"
    else
        record FAIL scontrol "job record unavailable"
    fi
else
    echo "scontrol not available"
    record FAIL scontrol "binary missing"
fi
echo
echo "--- nproc / memory ---"
nproc 2>/dev/null || true
free -h 2>/dev/null | head -3 || true
echo
echo "--- disk ---"
df -h /mnt/home "$HOME" /tmp 2>/dev/null | sed 's/^/  /' || true
echo
echo "--- MPI toolchain ---"
(
    set +u
    # shellcheck disable=SC1090
    source "$MPI_ACTIVATE"
    for program in gcc mpicc mpiexec make; do
        printf '%s=%s\n' "$program" "$(command -v "$program" 2>/dev/null || echo MISSING)"
    done
    mpicc -V 2>&1 | head -2 || true
    cat > "$OUT/mpi_hello.c" <<'EOF'
#include <mpi.h>
#include <stdio.h>
int main(int argc, char **argv) {
    int rank, size;
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    printf("hello from rank %d of %d\n", rank, size);
    MPI_Finalize();
    return 0;
}
EOF
    if mpicc -O2 -Wall "$OUT/mpi_hello.c" -o "$OUT/mpi_hello" 2>&1 && \
       mpiexec -n 2 "$OUT/mpi_hello" 2>&1; then
        exit 0
    else
        exit 1
    fi
)
if [ $? -eq 0 ]; then record PASS mpi_toolchain "compile and mpiexec -n 2"; else record FAIL mpi_toolchain "compile or run failed"; fi
echo

# ---------------------------------------------------------- 2. public environment
echo "===== 2. public environment and PRoot runtime ====="
set +u
# shellcheck disable=SC1090
source "$PUBLIC_ROOT/activate.sh"
ACTIVATE_RC=$?
set -u
export PS1="${PS1:-}"
if [ "$ACTIVATE_RC" -eq 0 ] && [ -n "${QWEN_RUN_DIR:-}" ]; then
    echo "QWEN_PROJECT_ROOT=$QWEN_PROJECT_ROOT"
    echo "PRoot run dir: $QWEN_RUN_DIR ($(du -sh "$QWEN_RUN_DIR" 2>/dev/null | cut -f1))"
    run_proot bash -c 'head -2 /etc/os-release 2>/dev/null; uname -r' || true
    run_proot "$PUBLIC_ROOT/vllm-env/bin/python" -c \
        'import vllm, torch, transformers; print("vllm", vllm.__version__, "torch", torch.__version__, "transformers", transformers.__version__)'
    IMPORT_RC=$?
    if [ "$IMPORT_RC" -eq 0 ]; then
        record PASS public_runtime "PRoot python 3.12.14 + vllm/torch/transformers import"
    else
        record FAIL public_runtime "import failed inside PRoot"
        critical
    fi
    record PASS proot_unpack "$(du -sh "$QWEN_RUN_DIR" 2>/dev/null | cut -f1)"
else
    record FAIL proot_unpack "activate.sh failed (rc=$ACTIVATE_RC)"
    critical
fi
echo

# ------------------------------------------------------------- 3. project layer
echo "===== 3. project-layer bootstrap ====="
DEPS_STARTED=$(date +%s)
boot_stdout=$(bash "$HERE/_staged/bootstrap.sh" "$HERE/_staged/requirements.txt")
boot_rc=$?
DEPS_SECONDS=$(( $(date +%s) - DEPS_STARTED ))
if [ "$boot_rc" -eq 0 ]; then
    eval "$boot_stdout"
    record PASS bootstrap_install "mode=$(cat "$VT_DEPS_DIR/.ready" 2>/dev/null || echo unknown) seconds=${DEPS_SECONDS} imports=$(tr '\n' ' ' < "$VT_DEPS_DIR/.imports.txt" 2>/dev/null)"
    echo "VT_DEPS_DIR=$VT_DEPS_DIR"
    echo "VT_PYTHON=$VT_PYTHON"
    echo "install record: $(cat "$VT_DEPS_DIR/.install.json" 2>/dev/null || echo missing)"
    du -sh "$VT_DEPS_DIR" 2>/dev/null
    if [ "${VT_DEPS_MODE:-target}" = venv ]; then
        site_packages="$VT_DEPS_DIR/lib/python3.12/site-packages"
    else
        site_packages="$VT_DEPS_DIR"
    fi
    ls "$site_packages" 2>/dev/null | grep '\.dist-info$' | sed 's/\.dist-info$//' | sort > "$OUT/installed-packages-${JOB}.txt"
    echo "installed distributions: $(wc -l < "$OUT/installed-packages-${JOB}.txt")"
else
    record FAIL bootstrap_install "exit=$boot_rc"
    critical
fi

REUSE_STARTED=$(date +%s%N 2>/dev/null || date +%s)
boot2_stdout=$(bash "$HERE/_staged/bootstrap.sh" "$HERE/_staged/requirements.txt")
boot2_rc=$?
REUSE_ENDED=$(date +%s%N 2>/dev/null || date +%s)
if [ "$boot2_rc" -eq 0 ]; then
    eval "$boot2_stdout"
    if [ "${REUSE_ENDED}" -gt 1000000000000 ] 2>/dev/null; then
        REUSE_MS=$(( (REUSE_ENDED - REUSE_STARTED) / 1000000 ))
    else
        REUSE_MS=$(( (REUSE_ENDED - REUSE_STARTED) * 1000 ))
    fi
    record PASS bootstrap_reuse "second call ${REUSE_MS}ms (cache key $VT_DEPS_KEY)"
else
    REUSE_MS=0
    record FAIL bootstrap_reuse "exit=$boot2_rc"
fi
echo

# ------------------------------------------------------- 4. imports and render
echo "===== 4. imports, SQLite FTS5, page render ====="
SAMPLE_PDF=""
for candidate in "$PDF_DIR/ACS_Lecture_1_2026F.pdf" "$PDF_DIR/ACS_Lecture_0_2026F.pdf" "$PDF_DIR/Tutorial_1.pdf"; do
    if [ -f "$candidate" ]; then SAMPLE_PDF="$candidate"; break; fi
done
echo "sample pdf: ${SAMPLE_PDF:-<none uploaded>}"
if [ -z "$SAMPLE_PDF" ]; then
    record FAIL sample_pdf "no course PDF found under $PDF_DIR"
    critical
else
    record PASS sample_pdf "$(basename "$SAMPLE_PDF")"
fi
CHECKS_RC=1
if [ -n "${VT_PYTHON:-}" ]; then
    run_proot "$VT_PYTHON" "$HERE/checks.py" \
        --pdf "$SAMPLE_PDF" \
        --out-dir "$OUT/rendered" \
        --out "$OUT/checks-${JOB}.json"
    CHECKS_RC=$?
fi
if [ "$CHECKS_RC" -eq 0 ]; then record PASS checks_py "all critical imports and FTS5"; else record FAIL checks_py "rc=$CHECKS_RC"; critical; fi
echo

# ------------------------------------------------------------- 5. model weights
echo "===== 5. model availability and weights ====="
HF_BIN="$PUBLIC_ROOT/vllm-env/bin/hf"
mkdir -p "$HOME/models"
download_model() {
    local repo=$1 dir=$2 marker=$3
    if [ -f "$HOME/models/$dir/$marker" ]; then
        echo "[models] already present: $dir"
        return 0
    fi
    local started=$(date +%s)
    timeout 1500 bash "$PUBLIC_ROOT/runtime.sh" "$HF_BIN" download "$repo" --local-dir "$HOME/models/$dir"
    local rc=$?
    echo "[models] $repo -> local-dir $dir rc=$rc seconds=$(( $(date +%s) - started )) size=$(du -sh "$HOME/models/$dir" 2>/dev/null | cut -f1)"
    return $rc
}
if download_model "PaddlePaddle/PP-DocLayoutV2" "PP-DocLayoutV2" "inference.pdiparams"; then
    record PASS download_layout_v2 "$(du -sh "$HOME/models/PP-DocLayoutV2" 2>/dev/null | cut -f1)"
else
    record FAIL download_layout_v2 "hf download failed"
    critical
fi
OCR_MODEL=""
for repo in "PaddlePaddle/PaddleOCR-VL-1.6" "PaddlePaddle/PaddleOCR-VL"; do
    short=${repo##*/}
    if download_model "$repo" "$short" "model.safetensors"; then OCR_MODEL="$short"; break; fi
done
if [ -n "$OCR_MODEL" ]; then
    OCR_WEIGHTS=$(find "$HOME/models/$OCR_MODEL" -name '*.safetensors' -printf '%s\n' 2>/dev/null | awk '{s+=$1} END {printf "%.0f", s/1e6}')
    record PASS download_ocr_model "model=$OCR_MODEL safetensors_mb=${OCR_WEIGHTS:-0}"
else
    record FAIL download_ocr_model "no candidate downloaded"
    critical
fi
echo "models dir:"; du -sh "$HOME/models"/* 2>/dev/null | sed 's/^/  /' || true
echo

# ------------------------------------------------------------- 6. layout probe
echo "===== 6. CPU layout probe (PP-DocLayoutV2) ====="
LAYOUT_RC=1
LAYOUT_RAN=0
LAYOUT_IMAGE="$OUT/rendered/sample-p001.png"
if [ -n "${VT_PYTHON:-}" ] && [ -f "$LAYOUT_IMAGE" ]; then
    timeout 1200 bash "$PUBLIC_ROOT/runtime.sh" "$VT_PYTHON" "$HERE/layout_probe.py" \
        --image "$LAYOUT_IMAGE" \
        --model-dir "$HOME/models/PP-DocLayoutV2" \
        --out "$OUT/layout-${JOB}.json" \
        --out-dir "$OUT/layout"
    LAYOUT_RC=$?
    LAYOUT_RAN=1
else
    echo "skipping layout probe: VT_PYTHON or rendered page missing"
    LAYOUT_RAN=0
fi
if [ "$LAYOUT_RC" -eq 0 ]; then
    record PASS layout_cpu "PP-DocLayoutV2 detection on a rendered course page"
else
    record FAIL layout_cpu "rc=$LAYOUT_RC ran=${LAYOUT_RAN:-0}"
    critical
fi
echo

# --------------------------------------------------------------- 7. summary
echo "===== 7. summary ====="
NOW=$(date -Is)
cat > "$OUT/summary-${JOB}.json" <<EOF
{
  "schema": "vt-env-spike/1",
  "job_id": "${JOB}",
  "host": "$(hostname)",
  "generated_at": "${NOW}",
  "task_dir": "${HERE}",
  "cache_key": "${VT_DEPS_KEY:-}",
  "deps_mode": "$(cat "${VT_DEPS_DIR:-/nonexistent}/.ready" 2>/dev/null || echo unknown)",
  "deps_install_seconds": ${DEPS_SECONDS},
  "deps_second_call_ms": ${REUSE_MS},
  "ocr_model": "${OCR_MODEL:-}",
  "pass": ${PASS},
  "fail": ${FAIL},
  "critical_failures": ${CRITICAL},
  "checks_json": "checks-${JOB}.json",
  "layout_json": "layout-${JOB}.json",
  "installed_packages": "installed-packages-${JOB}.txt",
  "results": "results-${JOB}.txt",
  "log": "env-spike-${JOB}.log"
}
EOF
cp "$OUT/summary-${JOB}.json" "$OUT/summary.json"
echo
cat "$RESULTS"
echo
echo "pass=$PASS fail=$FAIL critical=$CRITICAL"
echo "summary: $OUT/summary-${JOB}.json"
echo "=== environment mechanics spike done $(date -Is) ==="
if [ "$CRITICAL" -gt 0 ]; then exit 1; fi
exit 0
