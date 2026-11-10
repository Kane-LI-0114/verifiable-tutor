import { vi } from "vitest";

export interface FetchCall {
  url: string;
  path: string;
  method: string;
  body: unknown;
  init: RequestInit;
}

export type RouteHandler = (call: FetchCall) => Response | Promise<Response>;

export interface StubRoute {
  method?: string;
  /** Exact pathname or a pattern matched against it. */
  path: string | RegExp;
  handler: RouteHandler;
}

function pathOf(url: string): string {
  try {
    return new URL(url, "http://localhost").pathname;
  } catch {
    return url;
  }
}

function matches(route: StubRoute, call: FetchCall): boolean {
  const method = (route.method ?? "GET").toUpperCase();
  if (method !== call.method) {
    return false;
  }
  return typeof route.path === "string"
    ? route.path === call.path
    : route.path.test(call.path);
}

/**
 * Install a fetch stub for the live API and record every call.
 *
 * An unstubbed request fails the test loudly, so a page that calls an
 * unexpected endpoint or an endpoint it should not call shows up as a defect
 * rather than a silent network error.
 */
export function createFetchStub(routes: StubRoute[]) {
  const calls: FetchCall[] = [];
  const fetchImpl = vi.fn(
    async (input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.href
            : input.url;
      const method = (init.method ?? "GET").toUpperCase();
      const path = pathOf(url);
      let body: unknown;
      if (typeof init.body === "string") {
        try {
          body = JSON.parse(init.body);
        } catch {
          body = init.body;
        }
      }
      const call: FetchCall = { url, path, method, body, init };
      calls.push(call);
      const route = routes.find((candidate) => matches(candidate, call));
      if (!route) {
        throw new Error(`unexpected fetch: ${method} ${path}`);
      }
      return route.handler(call);
    },
  );
  vi.stubGlobal("fetch", fetchImpl);
  return {
    calls,
    fetch: fetchImpl,
    restore: () => {
      vi.unstubAllGlobals();
    },
  };
}

export function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    ...init,
    headers: { "content-type": "application/json", ...(init.headers ?? {}) },
  });
}

export function errorResponse(detail: string, status: number): Response {
  return new Response(JSON.stringify({ detail }), {
    status,
    headers: { "content-type": "application/json" },
  });
}

export interface SseOptions {
  headers?: Record<string, string>;
  /** Await this promise after each frame; lets a test hold a stream open. */
  gate?: Promise<void>;
  /** Defaults to the chat protocol; plain omits the AI SDK version header. */
  protocol?: "ai-sdk" | "plain";
}

/** Encode protocol frames as the AI SDK UI message stream the backend emits. */
export function sseResponse(frames: unknown[], options: SseOptions = {}): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      for (const frame of frames) {
        const line =
          frame === "[DONE]" ? "data: [DONE]\n\n" : `data: ${JSON.stringify(frame)}\n\n`;
        try {
          controller.enqueue(encoder.encode(line));
        } catch {
          // The reader cancelled the stream before the remaining frames arrived.
          return;
        }
        if (options.gate) {
          await options.gate;
        }
      }
      try {
        controller.close();
      } catch {
        // Already closed by a cancelled reader.
      }
    },
  });
  const headers: Record<string, string> = {
    "content-type": "text/event-stream",
  };
  if (options.protocol !== "plain") {
    headers["x-vercel-ai-ui-message-stream"] = "v1";
  }
  return new Response(stream, {
    status: 200,
    headers: { ...headers, ...options.headers },
  });
}
