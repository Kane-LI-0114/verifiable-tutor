# Local Swagger UI API documentation

This directory is the maintained, offline Swagger UI for the local backend. It is generated from the app's OpenAPI schema by `scripts/build_api_docs.py` and committed so the documentation works without a network and stays reviewable in Git. The decision is recorded in [ADR-0013](../adr/0013-local-offline-swagger-ui.md).

## What is here

| Path | Content |
|---|---|
| `openapi.json` | Deterministic OpenAPI 3.1 export of the app (sorted keys, two-space indent, no timestamps or paths) |
| `index.html` | Generated Swagger UI page; the schema is embedded inline and only relative local assets are loaded |
| `vendor/swagger-ui/` | Pinned `swagger-ui-dist` assets (`swagger-ui-bundle.js`, `swagger-ui.css`, `favicon-32x32.png`), `VERSION`, `SHA256SUMS`, Apache-2.0 `LICENSE` |

The generated files are committed on purpose and guarded by a test; edit the routes or the generator, never these files.

## Open the documentation

- Offline from the repository: open `docs/api/index.html` in a browser. The schema is inline, so no server and no network are needed.
- From the running backend: `.venv/bin/fastapi dev`, then `http://127.0.0.1:8000/docs` (local assets, live schema) or `http://127.0.0.1:8000/api-docs/` (the committed bundle).
- From a plain static server: `python3 -m http.server -d docs/api 8765`, then `http://127.0.0.1:8765/`.

"Try it out" calls work while the backend runs: sign in through `POST /api/auth/login` (the six digit code appears in the backend log when SMTP is unset in development mode), and the same-origin session cookie is used by later calls. There is no Authorize button because the API does not use bearer tokens.

## Regenerate after API changes

```bash
.venv/bin/python scripts/build_api_docs.py           # rewrite openapi.json and index.html
.venv/bin/python scripts/build_api_docs.py --check   # exit 1 when stale
```

Run the check before committing; `tests/api/test_api_docs.py` also runs it, and the suite fails while the bundle is stale. The check exits 2 when the vendored assets are missing or corrupt.

## Upgrade Swagger UI

The vendored version is 5.34.1. To upgrade, change the default in `scripts/vendor_swagger_ui.sh` (or pass `SWAGGER_UI_VERSION`), re-download, regenerate, and review the diff:

```bash
SWAGGER_UI_VERSION=5.34.1 bash scripts/vendor_swagger_ui.sh   # only this step needs the network
.venv/bin/python scripts/build_api_docs.py
```

The script writes `VERSION`, recomputes `SHA256SUMS`, and keeps the upstream `LICENSE`. Commit the asset change together with the regeneration.

## Notes

- The bundle is documentation only; it exposes the OpenAPI schema and no secrets or runtime data.
- Do not serve this directory from a public host; the local demo is the target.
- `/openapi.json` remains the live schema from the running app; the committed `openapi.json` is the reviewed snapshot.
