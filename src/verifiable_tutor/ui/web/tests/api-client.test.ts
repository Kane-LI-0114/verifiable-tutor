import { afterEach, describe, expect, it } from "vitest";

import { apiFetch, ApiError, isUnauthorized, NETWORK_ERROR_STATUS } from "@/lib/api/client";
import { apiErrorMessage } from "@/lib/api/errors";
import { en } from "@/lib/i18n/en";

import { createFetchStub, errorResponse, jsonResponse } from "./api-stub";

let stub: ReturnType<typeof createFetchStub> | null = null;

afterEach(() => {
  stub?.restore();
  stub = null;
});

describe("apiFetch", () => {
  it("sends same-origin credentials and parses JSON", async () => {
    stub = createFetchStub([
      { method: "GET", path: "/api/auth/me", handler: () => jsonResponse({ id: "u1" }) },
    ]);

    const result = await apiFetch<{ id: string }>("/api/auth/me");

    expect(result).toEqual({ id: "u1" });
    expect(stub.calls[0].init.credentials).toBe("same-origin");
    expect(stub.calls[0].method).toBe("GET");
  });

  it("posts a JSON body with the JSON content type", async () => {
    stub = createFetchStub([
      {
        method: "POST",
        path: "/api/auth/login",
        handler: () => jsonResponse({ user: { id: "u1" } }),
      },
    ]);

    await apiFetch("/api/auth/login", {
      method: "POST",
      body: { email: "student@ust.hk", password: "correct-horse-battery" },
    });

    expect(stub.calls[0].body).toEqual({
      email: "student@ust.hk",
      password: "correct-horse-battery",
    });
    expect(stub.calls[0].init.headers).toEqual({ "content-type": "application/json" });
  });

  it("turns a backend detail into an ApiError with the status", async () => {
    stub = createFetchStub([
      {
        method: "POST",
        path: "/api/auth/login",
        handler: () => errorResponse("incorrect email or password", 401),
      },
    ]);

    await expect(
      apiFetch("/api/auth/login", { method: "POST", body: {} }),
    ).rejects.toMatchObject({
      name: "ApiError",
      status: 401,
      detail: "incorrect email or password",
    });
    expect(isUnauthorized(new ApiError(401, "x"))).toBe(true);
  });

  it("keeps the first validation message from a 422 body", async () => {
    stub = createFetchStub([
      {
        method: "POST",
        path: "/api/chat",
        handler: () =>
          jsonResponse(
            { detail: [{ loc: ["body", "thinking"], msg: "Input should be 'off'" }] },
            { status: 422 },
          ),
      },
    ]);

    await expect(apiFetch("/api/chat", { method: "POST", body: {} })).rejects.toMatchObject({
      status: 422,
      detail: "Input should be 'off'",
    });
  });

  it("returns nothing for a 204 response", async () => {
    stub = createFetchStub([
      { method: "POST", path: "/api/auth/logout", handler: () => new Response(null, { status: 204 }) },
    ]);

    await expect(
      apiFetch<void>("/api/auth/logout", { method: "POST" }),
    ).resolves.toBeUndefined();
  });

  it("reports an unreachable backend as a network error", async () => {
    stub = createFetchStub([
      {
        method: "GET",
        path: "/api/auth/me",
        handler: () => {
          throw new TypeError("fetch failed");
        },
      },
    ]);

    await expect(apiFetch("/api/auth/me")).rejects.toMatchObject({
      status: NETWORK_ERROR_STATUS,
    });
  });

  it("rethrows an actual abort untouched", async () => {
    const abort = new DOMException("The operation was aborted.", "AbortError");
    stub = createFetchStub([
      {
        method: "GET",
        path: "/api/auth/me",
        handler: () => {
          throw abort;
        },
      },
    ]);

    await expect(apiFetch("/api/auth/me")).rejects.toBe(abort);
  });

  it("treats a DOMException that is not an abort as a request failure", async () => {
    stub = createFetchStub([
      {
        method: "GET",
        path: "/api/auth/me",
        handler: () => {
          throw new DOMException("storage is blocked", "NotAllowedError");
        },
      },
    ]);

    await expect(apiFetch("/api/auth/me")).rejects.toMatchObject({
      name: "ApiError",
      status: NETWORK_ERROR_STATUS,
    });
  });
});

describe("apiErrorMessage", () => {
  it("maps stable backend details to the localized copy", () => {
    expect(
      apiErrorMessage(new ApiError(401, "incorrect email or password"), en),
    ).toBe(en.auth.invalidCredentials);
    expect(apiErrorMessage(new ApiError(403, "email domain is not allowed"), en)).toBe(
      en.auth.invalidEmail,
    );
    expect(
      apiErrorMessage(new ApiError(422, "password must be at least 8 characters"), en),
    ).toBe(en.auth.shortPassword);
  });

  it("falls back to generic copy for unknown details and unreachable requests", () => {
    expect(apiErrorMessage(new ApiError(500, "unmapped detail"), en)).toBe(
      en.common.serverError,
    );
    expect(
      apiErrorMessage(new ApiError(NETWORK_ERROR_STATUS, "network error"), en),
    ).toBe(en.common.networkError);
    expect(apiErrorMessage(new TypeError("fetch failed"), en)).toBe(
      en.common.networkError,
    );
  });
});
