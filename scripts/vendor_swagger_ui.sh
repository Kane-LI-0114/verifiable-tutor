#!/usr/bin/env bash
# Vendor the pinned Swagger UI assets into docs/api/vendor/swagger-ui/.
#
# This is the only step that needs the network. The committed assets are used
# offline by docs/api/index.html and by the backend's /docs page. Upgrade by
# changing SWAGGER_UI_VERSION, re-running this script, then regenerating the
# docs bundle with scripts/build_api_docs.py.
set -euo pipefail

VERSION="${SWAGGER_UI_VERSION:-5.34.1}"
BASE="https://unpkg.com/swagger-ui-dist@${VERSION}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/docs/api/vendor/swagger-ui"

mkdir -p "${OUT}"
for file in swagger-ui-bundle.js swagger-ui.css favicon-32x32.png LICENSE; do
  echo "fetching ${file} (${VERSION})"
  curl -fsSL "${BASE}/${file}" -o "${OUT}/${file}"
done

printf '%s\n' "${VERSION}" > "${OUT}/VERSION"

if command -v sha256sum >/dev/null 2>&1; then
  SHA="sha256sum"
else
  SHA="shasum -a 256"
fi
(
  cd "${OUT}"
  ${SHA} swagger-ui-bundle.js swagger-ui.css favicon-32x32.png LICENSE > SHA256SUMS
)

echo "vendored swagger-ui-dist ${VERSION} into ${OUT}"
