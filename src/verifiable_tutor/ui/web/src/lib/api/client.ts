/**
 * HTTP client for the local backend.
 *
 * Every call is same-origin: the session cookie is HttpOnly, so the browser
 * attaches it, and the API never needs a token in JavaScript. Errors carry the
 * HTTP status and the backend `detail` string so pages can map them to copy.
 */

import { detailFromPayload, isAbortError } from "./http";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** A request that never reached the server (offline, proxy down, aborted). */
export const NETWORK_ERROR_STATUS = 0;

interface RequestOptions {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
}

export async function apiFetch<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, signal } = options;
  const init: RequestInit = {
    method,
    credentials: "same-origin",
    signal,
  };
  if (body !== undefined) {
    init.headers = { "content-type": "application/json" };
    init.body = JSON.stringify(body);
  }

  let response: Response;
  try {
    response = await fetch(path, init);
  } catch (error) {
    if (isAbortError(error)) {
      throw error;
    }
    throw new ApiError(NETWORK_ERROR_STATUS, "network error");
  }

  if (!response.ok) {
    let detail = response.statusText || `HTTP ${response.status}`;
    try {
      detail = detailFromPayload(await response.json(), detail);
    } catch {
      // A non-JSON error body keeps the status text.
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

/**
 * Fetch a binary body (the source PDF) as an ArrayBuffer.
 *
 * The preview loads the whole file once instead of relying on range requests,
 * which keeps the local server simple; the corpus files are under 15 MB.
 */
export async function apiFetchBinary(
  path: string,
  options: { signal?: AbortSignal } = {},
): Promise<ArrayBuffer> {
  let response: Response;
  try {
    response = await fetch(path, {
      credentials: "same-origin",
      signal: options.signal,
    });
  } catch (error) {
    if (isAbortError(error)) {
      throw error;
    }
    throw new ApiError(NETWORK_ERROR_STATUS, "network error");
  }
  if (!response.ok) {
    let detail = response.statusText || `HTTP ${response.status}`;
    try {
      detail = detailFromPayload(await response.json(), detail);
    } catch {
      // A non-JSON error body keeps the status text.
    }
    throw new ApiError(response.status, detail);
  }
  return response.arrayBuffer();
}
