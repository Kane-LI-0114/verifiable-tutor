import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

import { clearHistoryCache } from "./src/lib/chat/history-cache";

afterEach(() => {
  cleanup();
  clearHistoryCache();
});

if (typeof window !== "undefined" && typeof window.matchMedia !== "function") {
  window.matchMedia = (query: string): MediaQueryList => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}

if (typeof window !== "undefined" && typeof window.ResizeObserver !== "function") {
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}

if (typeof Element !== "undefined") {
  if (typeof Element.prototype.hasPointerCapture !== "function") {
    Element.prototype.hasPointerCapture = () => false;
  }
  if (typeof Element.prototype.releasePointerCapture !== "function") {
    Element.prototype.releasePointerCapture = () => {};
  }
  if (typeof Element.prototype.scrollIntoView !== "function") {
    Element.prototype.scrollIntoView = () => {};
  }
  // jsdom has no Web Animations API, and the list animation probes for it
  // through ResizeObserver and then calls animate on the element. Without a
  // stub every render that touches a list throws an unhandled error.
  if (typeof Element.prototype.animate !== "function") {
    Element.prototype.animate = (() =>
      ({
        cancel: () => {},
        finish: () => {},
        finished: Promise.resolve(),
        playState: "finished",
        // The list animation waits on the finish event, so the stub has to
        // deliver it rather than returning a silent object.
        addEventListener: (type: string, listener: () => void) => {
          if (type === "finish") {
            queueMicrotask(listener);
          }
        },
        removeEventListener: () => {},
      }) as unknown as Animation) as Element["animate"];
  }
}
