import { vi } from "vitest";

/** Minimal Web Audio platform stub for the answer read-aloud tests. */
export function installAudioContextStub() {
  const sources: Array<{
    buffer: unknown;
    start: ReturnType<typeof vi.fn>;
    stop: ReturnType<typeof vi.fn>;
    connect: ReturnType<typeof vi.fn>;
    onended: (() => void) | null;
  }> = [];
  const starts: number[] = [];
  const buffers: Array<{
    duration: number;
    copyToChannel: ReturnType<typeof vi.fn>;
  }> = [];

  const context = {
    currentTime: 0,
    destination: {},
    createBuffer: vi.fn(
      (_channels: number, length: number, rate: number) => {
        const buffer = {
          duration: length / rate,
          copyToChannel: vi.fn(),
        };
        buffers.push(buffer);
        return buffer;
      },
    ),
    createBufferSource: vi.fn(() => {
      const source = {
        buffer: null as unknown,
        start: vi.fn((when = 0) => {
          starts.push(when);
        }),
        stop: vi.fn(),
        connect: vi.fn(),
        onended: null as (() => void) | null,
      };
      sources.push(source);
      return source;
    }),
    resume: vi.fn(async () => {}),
    close: vi.fn(async () => {}),
  };

  vi.stubGlobal(
    "AudioContext",
    vi.fn(function () {
      return context;
    }),
  );

  return {
    context,
    sources,
    starts,
    buffers,
    finish() {
      sources[sources.length - 1]?.onended?.();
    },
    finishAll() {
      for (const source of sources) {
        source.onended?.();
      }
    },
    restore() {
      vi.unstubAllGlobals();
    },
  };
}
