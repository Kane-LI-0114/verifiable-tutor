import { afterEach, describe, expect, it, vi } from "vitest";

import { synthesizeSpeech } from "@/lib/api/voice";

import { createFetchStub, errorResponse } from "./api-stub";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("synthesizeSpeech", () => {
  it("turns a rejected speech request into an ApiError with the backend detail", async () => {
    const blank = createFetchStub([
      {
        method: "POST",
        path: "/api/voice/speech",
        handler: () => errorResponse("text must not be empty", 400),
      },
    ]);
    await expect(synthesizeSpeech("")).rejects.toMatchObject({
      name: "ApiError",
      status: 400,
      detail: "text must not be empty",
    });
    blank.restore();

    const unsigned = createFetchStub([
      {
        method: "POST",
        path: "/api/voice/speech",
        handler: () => errorResponse("not signed in", 401),
      },
    ]);
    await expect(synthesizeSpeech("hello")).rejects.toMatchObject({
      name: "ApiError",
      status: 401,
      detail: "not signed in",
    });
    unsigned.restore();
  });

  it("reports an unreachable speech backend as a network error", async () => {
    createFetchStub([
      {
        method: "POST",
        path: "/api/voice/speech",
        handler: () => {
          throw new TypeError("fetch failed");
        },
      },
    ]);

    await expect(synthesizeSpeech("hello")).rejects.toMatchObject({
      name: "ApiError",
      status: 0,
      detail: "network error",
    });
  });
});
