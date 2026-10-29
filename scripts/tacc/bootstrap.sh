#!/usr/bin/env bash
# Idempotent project-layer environment for TACC jobs.
#
# Installs the pinned project dependencies into a cache directory under $HOME,
# keyed by the public environment build, the requirements hash, and a bootstrap
# revision. Writes a .ready marker so later jobs skip the install, and records
# which imports work in .imports.txt.
#
# Usage:  eval "$(bash _staged/bootstrap.sh _staged/requirements.txt)"
# Then:   run_proot "$VT_PYTHON" your_script.py
#
# The install runs inside the PRoot userland runtime because the compute node
# host is Ubuntu 18 and cannot execute the public Python 3.12 directly. The
# public environment is never modified.
set -u
export PS1="${PS1:-}"

PUBLIC_ROOT="${PUBLIC_ROOT:-/mnt/home/public/course-envs/CSIT6000V/project/qwen3.8-27b-v1}"
UV_VERSION="${UV_VERSION:-0.13.6}"
BOOTSTRAP_REV="${BOOTSTRAP_REV:-1}"
OPENCV_HEADLESS_VERSION="${OPENCV_HEADLESS_VERSION:-4.10.0.84}"
REQUIREMENTS="${1:?usage: bootstrap.sh <requirements.txt>}"

log() { printf '[bootstrap] %s\n' "$*" >&2; }

[ -x "$PUBLIC_ROOT/vllm-env/bin/python" ] || { log "ERROR public python missing"; exit 2; }
[ -f "$REQUIREMENTS" ] || { log "ERROR requirements missing: $REQUIREMENTS"; exit 2; }

# Cache key: public environment build, our own requirements content, and the
# bootstrap logic revision (bump it whenever the install steps change).
if [ -f "$PUBLIC_ROOT/requirements-installed.txt" ]; then
    public_key=$(sha256sum "$PUBLIC_ROOT/requirements-installed.txt" | cut -c1-12)
else
    public_key=$(basename "$(readlink -f "$PUBLIC_ROOT")" | tr -cd '[:alnum:]' | cut -c1-12)
fi
req_key=$(sha256sum "$REQUIREMENTS" | cut -c1-12)
KEY="${public_key}-${req_key}-r${BOOTSTRAP_REV}"
TARGET="$HOME/vt-deps/$KEY"
MARKER="$TARGET/.ready"

print_env() {
    local mode
    mode=$(cat "$MARKER" 2>/dev/null || echo target)
    printf 'export VT_DEPS_KEY=%s\n' "$KEY"
    printf 'export VT_DEPS_DIR=%s\n' "$TARGET"
    printf 'export VT_DEPS_MODE=%s\n' "$mode"
    if [ "$mode" = "venv" ]; then
        printf 'export VT_PYTHON=%s\n' "$TARGET/bin/python"
        printf 'export PATH=%s/bin%s\n' "$TARGET" "${PATH:+:$PATH}"
    else
        printf 'export VT_PYTHON=%s\n' "$PUBLIC_ROOT/vllm-env/bin/python"
        printf 'export PYTHONPATH=%s%s\n' "$TARGET" "${PYTHONPATH:+:$PYTHONPATH}"
        printf 'export PATH=%s/bin%s\n' "$TARGET" "${PATH:+:$PATH}"
    fi
}

if [ -f "$MARKER" ]; then
    log "cache hit $TARGET ($(cat "$MARKER"))"
    print_env
    exit 0
fi

# The public Python and uv both need the PRoot userland runtime. Reuse the
# runtime unpacked by the caller when QWEN_RUN_DIR is already exported.
if [ -z "${QWEN_RUN_DIR:-}" ]; then
    QWEN_RUN_DIR=$(bash "$PUBLIC_ROOT/prepare-runtime.sh") || { log "ERROR cannot prepare PRoot runtime"; exit 3; }
    export QWEN_RUN_DIR
fi
run_proot() { bash "$PUBLIC_ROOT/runtime.sh" "$@"; }

UV_BIN="$HOME/bin/uv"
mkdir -p "$HOME/bin" "$HOME/.cache/vt-bootstrap"
if [ ! -x "$UV_BIN" ]; then
    arch=$(uname -m)
    case "$arch" in
        x86_64) uv_arch=x86_64 ;;
        aarch64) uv_arch=aarch64 ;;
        *) log "ERROR unsupported arch $arch"; exit 3 ;;
    esac
    tarball="$HOME/.cache/vt-bootstrap/uv-${uv_arch}.tar.gz"
    log "downloading uv $UV_VERSION for $uv_arch"
    if ! curl -fsSL --retry 3 --retry-delay 2 \
            "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${uv_arch}-unknown-linux-gnu.tar.gz" \
            -o "$tarball"; then
        log "pinned uv download failed, trying the latest release"
        curl -fsSL --retry 3 --retry-delay 2 \
            "https://github.com/astral-sh/uv/releases/latest/download/uv-${uv_arch}-unknown-linux-gnu.tar.gz" \
            -o "$tarball" || { log "ERROR uv download failed"; exit 4; }
    fi
    unpack="$HOME/.cache/vt-bootstrap/unpack-$(date +%s)"
    mkdir -p "$unpack"
    tar -xzf "$tarball" -C "$unpack" || { log "ERROR uv unpack failed"; exit 4; }
    find "$unpack" -name uv -type f -exec install -m 0755 {} "$UV_BIN" \; || { log "ERROR uv install failed"; exit 4; }
    rm -rf "$unpack"
fi
run_proot "$UV_BIN" --version 2>&1 | sed 's/^/[bootstrap] uv /' >&2

export UV_CACHE_DIR="$HOME/.cache/uv"
export UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-300}"
export UV_CONCURRENT_DOWNLOADS="${UV_CONCURRENT_DOWNLOADS:-4}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"

# Serialise installs across jobs that share the same cache key. Two spike jobs
# started on the same minute and raced on this directory in the 27854/27855 run.
mkdir -p "$HOME/vt-deps"
LOCK="$HOME/vt-deps/.lock-$KEY"
lock_acquired=0
for _ in $(seq 1 60); do
    if mkdir "$LOCK" 2>/dev/null; then lock_acquired=1; break; fi
    log "waiting for another job to finish installing $KEY"
    sleep 2
done
if [ "$lock_acquired" -eq 1 ]; then
    trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT INT TERM
else
    log "WARNING: cache lock not acquired, proceeding"
fi

started=$(date +%s)
log "installing $(wc -l < "$REQUIREMENTS") pins into $TARGET (revision $BOOTSTRAP_REV)"

install_target_once() {
    mkdir -p "$TARGET"
    run_proot "$UV_BIN" pip install \
        --python "$PUBLIC_ROOT/vllm-env/bin/python" \
        --target "$TARGET" \
        --link-mode copy \
        -r "$REQUIREMENTS"
}

install_target() {
    local attempt
    for attempt in 1 2 3; do
        log "target install attempt $attempt of 3"
        if install_target_once; then return 0; fi
        log "attempt $attempt failed (flaky PyPI route?), cleaning and retrying"
        rm -rf "$TARGET"
        sleep 10
    done
    return 1
}

mode=target
if install_target; then
    mode=target
else
    log "target install failed after retries, falling back to a venv"
    rm -rf "$TARGET"
    if run_proot "$UV_BIN" venv --clear --python "$PUBLIC_ROOT/vllm-env/bin/python" "$TARGET" \
        && run_proot "$UV_BIN" pip install --python "$TARGET/bin/python" --link-mode copy -r "$REQUIREMENTS"; then
        mode=venv
    else
        log "ERROR both install modes failed"
        exit 5
    fi
fi

if [ "$mode" = venv ]; then
    site_packages="$TARGET/lib/python3.12/site-packages"
else
    site_packages="$TARGET"
fi

probe_module() {
    local module=$1
    if [ "$mode" = venv ]; then
        run_proot "$TARGET/bin/python" -c "import $module" >/dev/null 2>&1
    else
        PYTHONPATH="$TARGET" run_proot "$PUBLIC_ROOT/vllm-env/bin/python" -c "import $module" >/dev/null 2>&1
    fi
}

# The compute node userland has no libGL, which the mandated
# opencv-contrib-python wheel needs. Overlay the headless build of the same
# version when the plain import fails.
overlay=no
if ! probe_module cv2; then
    log "import cv2 failed (no libGL userland?), overlaying opencv-python-headless $OPENCV_HEADLESS_VERSION"
    rm -rf "$site_packages/cv2"
    if [ "$mode" = venv ]; then
        run_proot "$UV_BIN" pip install --python "$TARGET/bin/python" --no-deps --link-mode copy \
            "opencv-python-headless==$OPENCV_HEADLESS_VERSION" || overlay=failed
    else
        run_proot "$UV_BIN" pip install --python "$PUBLIC_ROOT/vllm-env/bin/python" --target "$TARGET" --no-deps --link-mode copy \
            "opencv-python-headless==$OPENCV_HEADLESS_VERSION" || overlay=failed
    fi
    if [ "$overlay" != "failed" ]; then overlay=yes; fi
fi

import_lines=()
for module in cv2 paddle paddleocr pypdfium2; do
    if probe_module "$module"; then
        import_lines+=("$module=ok")
    else
        import_lines+=("$module=fail")
    fi
done
printf '%s\n' "${import_lines[@]}" > "$TARGET/.imports.txt"
log "imports: ${import_lines[*]}"

# Only now is the cache directory complete: the install succeeded, the OpenCV
# repair (if any) ran, and the import probes recorded their outcome. Later jobs
# read .imports.txt instead of re-probing.
echo "$mode" > "$MARKER"

elapsed=$(( $(date +%s) - started ))
imports_json=$(printf '"%s",' "${import_lines[@]}")
imports_json="[${imports_json%,}]"
printf '{"key":"%s","mode":"%s","bootstrap_rev":%s,"seconds":%s,"requirements_sha256":"%s","opencv_headless_overlay":"%s","imports":%s}\n' \
    "$KEY" "$mode" "$BOOTSTRAP_REV" "$elapsed" "$(sha256sum "$REQUIREMENTS" | cut -d' ' -f1)" "$overlay" "$imports_json" \
    > "$TARGET/.install.json"
log "installed in ${elapsed}s, mode $mode"
print_env
