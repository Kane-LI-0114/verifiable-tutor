/**
 * Shared HTTP failure helpers.
 *
 * The JSON API client and the chat transport fail the same way: an aborted
 * request propagates untouched, every other thrown request error becomes a
 * normal request failure, and the backend `detail` string is extracted in one
 * place so pages can map it to copy.
 */

/** `DOMException.ABORT_ERR`; the code is stable across DOM implementations. */
const ABORT_DOM_EXCEPTION_CODE = 20;

/**
 * True only for an actual abort.
 *
 * A `DOMException` is not necessarily an abort: storage, CORS, and encoding
 * failures throw named DOMExceptions too, and those are request failures.
 */
export function isAbortError(error: unknown): boolean {
  if (typeof error !== "object" || error === null) {
    return false;
  }
  if ((error as { name?: unknown }).name === "AbortError") {
    return true;
  }
  return (
    typeof DOMException !== "undefined" &&
    error instanceof DOMException &&
    error.code === ABORT_DOM_EXCEPTION_CODE
  );
}

/** The first message of a FastAPI validation error array, if there is one. */
export function firstValidationMessage(detail: unknown): string | null {
  if (!Array.isArray(detail)) {
    return null;
  }
  for (const item of detail) {
    if (
      typeof item === "object" &&
      item !== null &&
      typeof (item as { msg?: unknown }).msg === "string"
    ) {
      return (item as { msg: string }).msg;
    }
  }
  return null;
}

/** Read the backend `detail` out of a parsed error payload. */
export function detailFromPayload(payload: unknown, fallback: string): string {
  if (typeof payload !== "object" || payload === null || !("detail" in payload)) {
    return fallback;
  }
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.length > 0) {
    return detail;
  }
  return firstValidationMessage(detail) ?? fallback;
}

/** Read the backend `detail` out of an error body that was already read as text. */
export function detailFromText(text: string, fallback = "request failed"): string {
  try {
    const payload = JSON.parse(text) as unknown;
    const detail = detailFromPayload(payload, "");
    if (detail.length > 0) {
      return detail;
    }
  } catch {
    // A non-JSON body keeps the raw text.
  }
  return text.length > 0 ? text : fallback;
}
