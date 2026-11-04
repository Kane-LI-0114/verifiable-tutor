import { afterEach, describe, expect, it } from "vitest";

import { isPreviewRuntime, previewStateFromUrl } from "@/lib/preview/mode";

/** Point the jsdom document at a URL query without reloading the page. */
function visit(search: string): void {
  window.history.replaceState({}, "", `/${search}`);
}

afterEach(() => {
  window.history.replaceState({}, "", "/");
});

describe("preview runtime detection", () => {
  it("enters the offline demo for every documented ?preview value", () => {
    for (const value of ["1", "loading", "empty", "error"]) {
      visit(`?preview=${value}`);
      expect(isPreviewRuntime(), `?preview=${value}`).toBe(true);
    }
  });

  it("stays live when the URL carries no preview parameter", () => {
    visit("");

    expect(isPreviewRuntime()).toBe(false);
  });

  it("ignores an unknown preview value", () => {
    visit("?preview=unknown");

    expect(isPreviewRuntime()).toBe(false);
    expect(previewStateFromUrl()).toBe("normal");
  });
});

describe("preview page state from the URL", () => {
  it("selects the demo page state named by the URL", () => {
    for (const state of ["loading", "empty", "error"] as const) {
      visit(`?preview=${state}`);
      expect(previewStateFromUrl(), `?preview=${state}`).toBe(state);
    }
  });

  it("renders the normal page state for ?preview=1", () => {
    visit("?preview=1");

    expect(previewStateFromUrl()).toBe("normal");
  });

  it("renders the normal page state when the URL carries no preview parameter", () => {
    visit("");

    expect(previewStateFromUrl()).toBe("normal");
  });
});
