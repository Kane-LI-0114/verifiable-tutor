/**
 * URL preview parsing for the offline demo.
 *
 * Live data is the default. A preview build (`VITE_PREVIEW=1`) or an explicit
 * `?preview=1` URL keeps the fixture-driven demo available without a backend,
 * and `?preview=loading|empty|error` selects the page state the demo renders.
 */

import type { PreviewState } from "@/lib/types";

/** The documented `?preview` values that enter the offline demo. */
const PREVIEW_VALUES = new Set(["1", "loading", "empty", "error"]);

function previewParam(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return new URLSearchParams(window.location.search).get("preview");
}

/** Whether this browser session should render the offline preview demo. */
export function isPreviewRuntime(): boolean {
  if (import.meta.env.VITE_PREVIEW === "1") {
    return true;
  }
  const value = previewParam();
  return value !== null && PREVIEW_VALUES.has(value);
}

/**
 * The page state the offline demo should render: `?preview=loading|empty|error`
 * selects one; `?preview=1`, an unknown value, or no parameter is normal.
 */
export function previewStateFromUrl(): PreviewState {
  const value = previewParam();
  if (value === "loading" || value === "empty" || value === "error") {
    return value;
  }
  return "normal";
}
