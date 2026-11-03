import { describe, expect, it, vi } from "vitest";

import { renderRoute } from "./render-route";

const ROUTES: Array<[string, "student" | "instructor"]> = [
  ["/login", "student"],
  ["/chat", "student"],
  ["/chat/6f1c2a9b8d7e4f10a1b2c3d4e5f6a7b8", "student"],
  ["/practice", "student"],
  ["/knowledge", "student"],
  ["/instructor/builds", "instructor"],
  ["/instructor/deadlines", "instructor"],
];

describe("preview isolation", () => {
  it.each(ROUTES)(
    "renders %s without a network request",
    (path, role) => {
      const fetchSpy = vi.spyOn(globalThis, "fetch");

      renderRoute(path, { role });

      expect(fetchSpy).not.toHaveBeenCalled();
      fetchSpy.mockRestore();
    },
  );
});
