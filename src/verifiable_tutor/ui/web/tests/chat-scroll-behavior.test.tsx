import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";

import { ChatSessionShell } from "@/components/chat/chat-session-shell";
import { I18nProvider } from "@/lib/i18n";
import type { ConversationTurn } from "@/lib/types";

import { installMemoryStorage } from "./memory-storage";

const USER_ID = "turn-user";
const ANSWER_ID = "turn-answer";
const VIEWPORT_HEIGHT = 400;
/** Where the answer starts in the scrollable content, measured from its top. */
const ANSWER_TOP = 120;

function makeTurn(
  id: string,
  role: "user" | "assistant",
  content: string,
): ConversationTurn {
  return {
    message: {
      id,
      sequence: 1,
      role,
      content,
      provider: "deepseek",
      tier: "flash",
      created_at: "2026-11-09T00:00:00+00:00",
      reasoning: null,
      model: null,
      thinking: null,
      work_steps: [],
      citations: [],
      tool_calls: [],
      events: [],
    },
  };
}

function view(
  generatingMessageId: string | null,
  content = "Hello",
  scrollKey?: string,
  handoffOnFinish = false,
) {
  const turns = [
    makeTurn(USER_ID, "user", "How does the halo exchange work?"),
    makeTurn(ANSWER_ID, "assistant", content),
  ];
  return (
    <I18nProvider initialLang="en">
      <ChatSessionShell
        title="Test conversation"
        scrollKey={scrollKey}
        turns={turns}
        generatingMessageId={generatingMessageId}
        handoffOnFinish={handoffOnFinish}
        showEvidence={false}
      />
    </I18nProvider>
  );
}

function rect(top: number, bottom: number): DOMRect {
  return {
    top,
    bottom,
    left: 0,
    right: 800,
    x: 0,
    y: top,
    width: 800,
    height: bottom - top,
    toJSON: () => ({}),
  } as DOMRect;
}

/**
 * jsdom does not implement Element.scrollTo, which the headless scroller uses
 * for its own positioning. Map it to scrollTop so geometry stays measurable.
 */
let originalScrollTo: typeof Element.prototype.scrollTo | undefined;
beforeAll(() => {
  originalScrollTo = Element.prototype.scrollTo;
  Object.defineProperty(Element.prototype, "scrollTo", {
    configurable: true,
    writable: true,
    value: function (this: Element, options?: ScrollToOptions | number, y?: number) {
      const top =
        typeof options === "number" ? (y ?? 0) : (options?.top ?? undefined);
      if (typeof top === "number") {
        this.scrollTop = top;
      }
    },
  });
});
afterAll(() => {
  Object.defineProperty(Element.prototype, "scrollTo", {
    configurable: true,
    writable: true,
    value: originalScrollTo,
  });
});

/** The jsdom thread has no layout, so the tests supply the measured geometry. */
const geometry = { answerHeight: 200, scrollHeight: 450 };

/** A short answer (200px in a 400px viewport) and one that overflows it. */
function shortAnswer(): void {
  geometry.answerHeight = 200;
  geometry.scrollHeight = 450;
}
function longAnswer(): void {
  geometry.answerHeight = 900;
  geometry.scrollHeight = 1100;
}

function viewportOf(container: HTMLElement): HTMLElement {
  const element = container.querySelector<HTMLElement>(
    '[data-slot="message-scroller-viewport"]',
  );
  expect(element).not.toBeNull();
  return element as HTMLElement;
}

function answerItem(container: HTMLElement): HTMLElement {
  const element = container.querySelector<HTMLElement>(
    `[data-message-id="${ANSWER_ID}"]`,
  );
  expect(element).not.toBeNull();
  return element as HTMLElement;
}

function buttonOf(container: HTMLElement): HTMLButtonElement {
  const element = container.querySelector<HTMLButtonElement>(
    '[data-slot="message-scroller-button"]',
  );
  expect(element).not.toBeNull();
  return element as HTMLButtonElement;
}

function installGeometry(viewport: HTMLElement): void {
  Object.defineProperty(viewport, "clientHeight", {
    configurable: true,
    value: VIEWPORT_HEIGHT,
  });
  Object.defineProperty(viewport, "scrollHeight", {
    configurable: true,
    get: () => geometry.scrollHeight,
  });
  viewport.getBoundingClientRect = () => rect(0, VIEWPORT_HEIGHT);

  const content = viewport.querySelector<HTMLElement>(
    '[data-slot="message-scroller-content"]',
  );
  expect(content).not.toBeNull();
  for (const child of Array.from(content?.children ?? [])) {
    if (!(child instanceof HTMLElement) || !child.hasAttribute("data-message-id")) {
      continue;
    }
    const isAnswer = child.getAttribute("data-message-id") === ANSWER_ID;
    const top = isAnswer ? ANSWER_TOP : 0;
    // A real rect moves with the scroll offset and grows with the streamed
    // answer, so read the current height on every call rather than snapshot it.
    child.getBoundingClientRect = () => {
      const height = isAnswer ? geometry.answerHeight : 80;
      return rect(
        top - viewport.scrollTop,
        top + height - viewport.scrollTop,
      );
    };
  }
}

beforeEach(() => {
  installMemoryStorage();
  shortAnswer();
});

afterEach(() => {
  cleanup();
});

describe("conversation scroll during an answer", () => {
  it("leaves a short answer at the bottom instead of the viewport top", () => {
    const { container, rerender } = render(view(ANSWER_ID));
    const viewport = viewportOf(container);
    installGeometry(viewport);

    rerender(view(ANSWER_ID, "Hello world"));

    // 450px of content in a 400px viewport: the natural end is 50px down.
    expect(viewport.scrollTop).toBe(50);
    // The answer is still below the viewport top, with no blank space forced
    // underneath it to make a top alignment possible.
    expect(answerItem(container).getBoundingClientRect().top).toBeGreaterThan(0);
  });

  it("aligns to the answer top only once the answer exceeds the viewport", () => {
    const { container, rerender } = render(view(ANSWER_ID));
    const viewport = viewportOf(container);
    installGeometry(viewport);
    rerender(view(ANSWER_ID, "Hello"));
    expect(viewport.scrollTop).toBe(50);

    longAnswer();
    rerender(view(ANSWER_ID, "Hello world, with a much longer answer"));
    expect(viewport.scrollTop).toBe(ANSWER_TOP);

    // The answer keeps growing; the top stays level with the viewport top.
    geometry.answerHeight = 1200;
    geometry.scrollHeight = 1400;
    rerender(view(ANSWER_ID, "Hello world, longer still"));
    expect(viewport.scrollTop).toBe(ANSWER_TOP);
  });

  it("follows the answer to the bottom after the scroll-to-end button is clicked", () => {
    const { container, rerender } = render(view(ANSWER_ID));
    const viewport = viewportOf(container);
    installGeometry(viewport);
    longAnswer();
    rerender(view(ANSWER_ID, "Hello"));
    expect(viewport.scrollTop).toBe(ANSWER_TOP);
    fireEvent.scroll(viewport);

    const button = buttonOf(container);
    expect(button.getAttribute("data-active")).toBe("true");
    fireEvent.click(button);
    expect(viewport.scrollTop).toBe(700);

    geometry.answerHeight = 1200;
    geometry.scrollHeight = 1400;
    rerender(view(ANSWER_ID, "Hello world, longer still"));
    expect(viewport.scrollTop).toBe(1000);
  });

  it("follows the answer again after the reader scrolls back to the bottom", () => {
    const { container, rerender } = render(view(ANSWER_ID));
    const viewport = viewportOf(container);
    installGeometry(viewport);
    longAnswer();
    rerender(view(ANSWER_ID, "Hello"));
    expect(viewport.scrollTop).toBe(ANSWER_TOP);

    // The reader scrolls up, which stops the follow.
    fireEvent.wheel(viewport, { deltaY: -120 });
    viewport.scrollTop = 300;
    fireEvent.scroll(viewport);

    // Scrolling back down to the end of the thread is the arrow's request too:
    // the answer is followed again from there.
    fireEvent.wheel(viewport, { deltaY: 400 });
    viewport.scrollTop = 700;
    fireEvent.scroll(viewport);

    geometry.answerHeight = 1200;
    geometry.scrollHeight = 1400;
    rerender(view(ANSWER_ID, "Hello world, longer still"));
    expect(viewport.scrollTop).toBe(1000);
  });

  it("keeps following when the reader stops a scroll tick short of the end", () => {
    const { container, rerender } = render(view(ANSWER_ID));
    const viewport = viewportOf(container);
    installGeometry(viewport);
    longAnswer();
    rerender(view(ANSWER_ID, "Hello"));
    expect(viewport.scrollTop).toBe(ANSWER_TOP);

    // 698px of 700px: rounding and momentum leave the reader a pixel or two
    // short of the end, which still reads as the end.
    viewport.scrollTop = 698;
    fireEvent.scroll(viewport);

    geometry.answerHeight = 1200;
    geometry.scrollHeight = 1400;
    rerender(view(ANSWER_ID, "Hello world, longer still"));
    expect(viewport.scrollTop).toBe(1000);
  });

  it("does not follow when the reader stops well above the end", () => {
    const { container, rerender } = render(view(ANSWER_ID));
    const viewport = viewportOf(container);
    installGeometry(viewport);
    longAnswer();
    rerender(view(ANSWER_ID, "Hello"));
    expect(viewport.scrollTop).toBe(ANSWER_TOP);

    viewport.scrollTop = 690;
    fireEvent.scroll(viewport);

    geometry.answerHeight = 1200;
    geometry.scrollHeight = 1400;
    rerender(view(ANSWER_ID, "Hello world, longer still"));
    expect(viewport.scrollTop).toBe(690);
  });

  it("keeps following when the wheel keeps turning at the end", () => {
    const { container, rerender } = render(view(ANSWER_ID));
    const viewport = viewportOf(container);
    installGeometry(viewport);
    longAnswer();
    rerender(view(ANSWER_ID, "Hello"));
    expect(viewport.scrollTop).toBe(ANSWER_TOP);

    // The reader wheels to the end of the thread and keeps turning with nowhere
    // left to scroll, which fires wheel events but no scroll events.
    fireEvent.wheel(viewport, { deltaY: 320 });
    viewport.scrollTop = 700;
    fireEvent.scroll(viewport);
    fireEvent.wheel(viewport, { deltaY: 60 });
    fireEvent.wheel(viewport, { deltaY: 24 });

    geometry.answerHeight = 1200;
    geometry.scrollHeight = 1400;
    rerender(view(ANSWER_ID, "Hello world, longer still"));
    expect(viewport.scrollTop).toBe(1000);
  });

  it("stops moving the thread once the reader scrolls during generation", () => {
    const { container, rerender } = render(view(ANSWER_ID));
    const viewport = viewportOf(container);
    installGeometry(viewport);
    longAnswer();
    rerender(view(ANSWER_ID, "Hello"));
    expect(viewport.scrollTop).toBe(ANSWER_TOP);

    fireEvent.wheel(viewport, { deltaY: 140 });
    viewport.scrollTop = 300;
    fireEvent.scroll(viewport);

    geometry.answerHeight = 1200;
    geometry.scrollHeight = 1400;
    rerender(view(ANSWER_ID, "Hello world, longer still"));
    expect(viewport.scrollTop).toBe(300);
  });

  it("does not re-anchor a short answer the reader already scrolled away from", () => {
    const { container, rerender } = render(view(ANSWER_ID));
    const viewport = viewportOf(container);
    installGeometry(viewport);
    rerender(view(ANSWER_ID, "Hello"));
    expect(viewport.scrollTop).toBe(50);

    fireEvent.wheel(viewport, { deltaY: 40 });
    viewport.scrollTop = 20;
    fireEvent.scroll(viewport);

    longAnswer();
    rerender(view(ANSWER_ID, "Hello world, with a much longer answer"));
    expect(viewport.scrollTop).toBe(20);
  });

  it("treats a scrollbar drag as reader scrolling", () => {
    const { container, rerender } = render(view(ANSWER_ID));
    const viewport = viewportOf(container);
    installGeometry(viewport);
    longAnswer();
    rerender(view(ANSWER_ID, "Hello"));
    expect(viewport.scrollTop).toBe(ANSWER_TOP);

    // Dragging the scrollbar produces scroll events but no wheel or touch.
    viewport.scrollTop = 260;
    fireEvent.scroll(viewport);

    geometry.answerHeight = 1200;
    geometry.scrollHeight = 1400;
    rerender(view(ANSWER_ID, "Hello world, longer still"));
    expect(viewport.scrollTop).toBe(260);
  });

  it("does not jump to the bottom when the answer finishes", () => {
    const { container, rerender } = render(view(ANSWER_ID));
    const viewport = viewportOf(container);
    installGeometry(viewport);
    longAnswer();
    rerender(view(ANSWER_ID, "Hello"));
    expect(viewport.scrollTop).toBe(ANSWER_TOP);

    geometry.answerHeight = 1200;
    geometry.scrollHeight = 1400;
    rerender(view(null, "Hello world, the finished answer"));
    expect(viewport.scrollTop).toBe(ANSWER_TOP);
  });

  it("keeps the read position when the finished answer opens the new conversation", () => {
    const { container, rerender } = render(view(ANSWER_ID, "Hello", undefined, true));
    const first = viewportOf(container);
    installGeometry(first);
    longAnswer();
    rerender(view(ANSWER_ID, "Hello", undefined, true));
    expect(first.scrollTop).toBe(ANSWER_TOP);

    // The first answer navigates, which remounts the thread with a scroll key.
    cleanup();
    const secondRender = render(view(null, "Hello", "session-1"));
    const second = viewportOf(secondRender.container);
    installGeometry(second);
    expect(second.scrollTop).toBe(ANSWER_TOP);
  });
});
