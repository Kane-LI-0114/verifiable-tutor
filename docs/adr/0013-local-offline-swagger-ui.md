# ADR-0013: Local, offline Swagger UI API documentation

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-11-02 |
| **Deciders** | LI Jinchuan (project lead); recorded by the engineering agent |

## Context

The FastAPI backend (ADR-0012) exposes 20 operations, and the React UI will call them. FastAPI's default `/docs` and `/redoc` pages load their JavaScript and CSS from `cdn.jsdelivr.net`, so they do not work offline, and the default OpenAPI view documented responses as generic objects because most routes returned plain dictionaries.

The project's existing constraints point the same way: the demo must work offline after replay (ADR-0003 keeps the product UI free of CDNs), the backend runs on the laptop, and the repository owns its artifacts under `docs/`. The API documentation therefore needs three properties: it is available locally without a network, it stays in sync with the routes, and it shows enough schema detail to be useful.

## Decision

- Commit a maintained API documentation bundle under `docs/api/`:
  - `openapi.json`, a deterministic OpenAPI 3.1 export of the app (sorted keys, two-space indent, no timestamps or absolute paths);
  - `index.html`, a Swagger UI page that embeds the same schema inline and loads only relative local assets, so it opens offline from the file system;
  - `vendor/swagger-ui/`, the pinned Swagger UI distribution assets (`swagger-ui-dist` 5.34.1) with `VERSION`, `SHA256SUMS`, and the Apache-2.0 `LICENSE`.
- The backend serves the same local assets: `/docs` is a custom Swagger UI page using `/api-docs/vendor/swagger-ui/...` instead of a CDN, and `/api-docs/` mounts the committed bundle as static files. `/openapi.json` stays the live schema. ReDoc is disabled because it has no local assets.
- The documentation directory is injectable through `create_app(..., docs_api_dir=...)`; when the bundle is absent the two documentation routes are disabled with a warning and the API keeps working.
- `scripts/build_api_docs.py` regenerates `openapi.json` and `index.html`; `--check` fails when either is stale, and `tests/api/test_api_docs.py` runs the check so drift cannot land silently. `scripts/vendor_swagger_ui.sh` is the only step that needs the network and is used when upgrading Swagger UI.
- Add response models and tag metadata (`src/verifiable_tutor/api/schemas.py`) so the schema, and therefore the Swagger UI, shows fields, nullability, stream media types, and documented error responses.

The generated files are committed intentionally. They are deterministic deliverables guarded by a failing test, not incidental runtime output. This is the explicit exception to the repository rule against committing generated files; the API documentation bundle is the artifact.

## Consequences

**Positive:**

- The API documentation works offline, in the browser from `docs/api/index.html`, and from the running backend at `/docs` and `/api-docs/`.
- Drift is caught by `pytest`; changing a route without regenerating the bundle fails the suite.
- Swagger UI shows real response schemas, tag descriptions, stream media types, and error responses.
- No new Python or Node dependency, and no network at runtime.

**Negative:**

- About 1.9 MB of third-party Swagger UI assets are committed, which grows the repository and must be upgraded deliberately.
- The schema is a second generated artifact that must be regenerated after route or response-model changes; the failing check is the mitigation, but there is no CI.
- The offline page carries an inline copy of the schema, so it is larger than a page that fetches `openapi.json`.
- ReDoc is no longer available; users who want it need a separate vendored copy.

**Neutral:**

- `/docs` moves from CDN assets to local assets; `/api-docs/` is an additional read-only static surface with no authentication. The schema exposes no secrets.
- Swagger UI tries cookie-authenticated calls work because the UI and the API share an origin; the login endpoint sets the session cookie, and no Authorize button is needed.

## Alternatives considered

**Keep the default CDN pages.** For: zero repository growth and no maintenance. Against: no offline demo, external dependency, and no fixture for schema drift. Why not chosen: it contradicts the offline and local-first constraints.

**Add a Python package that bundles Swagger UI.** For: no checked-in browser assets. Against: a runtime dependency for documentation only, and the assets still need a path or a copy. Why not chosen: the committed vendor directory is smaller in dependency terms.

**Generate a Markdown API reference instead of Swagger UI.** For: reviewable text and no browser assets. Against: the required deliverable is an interactive Swagger UI, and the Markdown would be another generated artifact. Why not chosen: it does not satisfy the request.

**Serve `openapi.json` and let the browser fetch it from `index.html`.** For: smaller generated page. Against: `file://` fetches are blocked by browser CORS rules, so the offline page would require a local server. Why not chosen: the inline schema keeps double-click offline use working.

## Follow-ups

- Regenerate the bundle after any route, schema, or tag change; `pytest` fails until it is current.
- When adding CI, run `scripts/build_api_docs.py --check` as a step.
- Upgrade Swagger UI by changing the version in `scripts/vendor_swagger_ui.sh`, re-running it, regenerating the bundle, and reviewing the asset diff.
- If ReDoc or a second documentation surface is wanted, vendor its assets under the same model and record it in this ADR or a successor.

## References

- [ADR-0003](0003-react-spa-with-ai-elements.md), [ADR-0012](0012-fastapi-backend-structure-and-sessions.md)
- [docs/api/README.md](../api/README.md)
- [docs/fastapi-reference.md](../fastapi-reference.md)
- Swagger UI distribution: https://www.npmjs.com/package/swagger-ui-dist
