import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it } from "vitest";

import { EvidencePanel } from "@/components/chat/evidence-panel";
import { I18nProvider } from "@/lib/i18n";
import { PreviewProvider } from "@/lib/preview/context";
import {
  PREVIEW_CITATIONS,
  PREVIEW_SESSIONS,
} from "@/lib/preview/fixtures";
import { installMemoryStorage } from "./memory-storage";
import { renderRoute } from "./render-route";

const SESSION = `/chat/${PREVIEW_SESSIONS[0].id}`;
const NEXT_SESSION = `/chat/${PREVIEW_SESSIONS[1].id}`;
const WIDTH_KEY = "vt.evidence.width";
const COLLAPSED_KEY = "vt.evidence.collapsed";

function pane(): HTMLElement {
  return screen.getByTestId("evidence-pane");
}

function handle(): HTMLElement {
  return screen.getByRole("separator", {
    name: "Resize the evidence panel",
  });
}

function widthLimit(): number {
  return Math.min(640, Math.floor(window.innerWidth * 0.55));
}

beforeEach(() => {
  installMemoryStorage();
});

describe("evidence pane", () => {
  it("exposes a resizable separator with the default width and bounds", () => {
    renderRoute(SESSION);

    const separator = handle();

    expect(separator).toHaveAttribute("aria-orientation", "vertical");
    expect(separator).toHaveAttribute("aria-valuenow", "380");
    expect(separator).toHaveAttribute("aria-valuemin", "280");
    expect(separator).toHaveAttribute("aria-valuemax", String(widthLimit()));
    expect(separator).toHaveAttribute("tabindex", "0");
    expect(separator).toHaveClass("cursor-col-resize");
    expect(pane()).toHaveStyle({ width: "380px" });
  });

  it("resizes with the pointer and stores the width", () => {
    renderRoute(SESSION);

    const separator = handle();
    fireEvent.pointerDown(separator, { pointerId: 1, clientX: 1000 });
    fireEvent.pointerMove(separator, { pointerId: 1, clientX: 900 });
    fireEvent.pointerUp(separator, { pointerId: 1 });

    expect(pane()).toHaveStyle({ width: "480px" });
    expect(separator).toHaveAttribute("aria-valuenow", "480");
    expect(window.localStorage.getItem(WIDTH_KEY)).toBe("480");
  });

  it("clamps the pointer drag to the pane bounds", () => {
    renderRoute(SESSION);

    const separator = handle();
    fireEvent.pointerDown(separator, { pointerId: 1, clientX: 500 });
    fireEvent.pointerMove(separator, { pointerId: 1, clientX: 0 });

    expect(separator).toHaveAttribute("aria-valuenow", String(widthLimit()));

    fireEvent.pointerMove(separator, { pointerId: 1, clientX: 4000 });

    expect(separator).toHaveAttribute("aria-valuenow", "280");
    fireEvent.pointerUp(separator, { pointerId: 1 });
  });

  it("resizes with the keyboard and jumps to the bounds", async () => {
    const user = userEvent.setup();
    renderRoute(SESSION);

    act(() => handle().focus());

    await user.keyboard("{ArrowLeft}");
    expect(handle()).toHaveAttribute("aria-valuenow", "396");

    await user.keyboard("{ArrowRight}{ArrowRight}");
    expect(handle()).toHaveAttribute("aria-valuenow", "364");

    await user.keyboard("{Home}");
    expect(handle()).toHaveAttribute("aria-valuenow", "280");

    await user.keyboard("{End}");
    expect(handle()).toHaveAttribute("aria-valuenow", String(widthLimit()));
    expect(window.localStorage.getItem(WIDTH_KEY)).toBe(String(widthLimit()));
  });

  it("restores the width with a double click", () => {
    renderRoute(SESSION);

    const separator = handle();
    fireEvent.pointerDown(separator, { pointerId: 1, clientX: 1000 });
    fireEvent.pointerMove(separator, { pointerId: 1, clientX: 900 });
    fireEvent.pointerUp(separator, { pointerId: 1 });
    expect(separator).toHaveAttribute("aria-valuenow", "480");

    fireEvent.doubleClick(separator);

    expect(separator).toHaveAttribute("aria-valuenow", "380");
    expect(pane()).toHaveStyle({ width: "380px" });
  });

  it("collapses to a narrow rail and expands again", async () => {
    const user = userEvent.setup();
    renderRoute(SESSION);

    await user.click(
      screen.getByRole("button", { name: "Collapse the evidence panel" }),
    );

    expect(pane()).toHaveAttribute("data-collapsed", "true");
    expect(pane()).toHaveStyle({ width: "44px" });
    expect(window.localStorage.getItem(COLLAPSED_KEY)).toBe("true");
    expect(screen.queryByRole("separator")).not.toBeInTheDocument();
    expect(
      within(pane()).queryByText("Open a citation"),
    ).not.toBeInTheDocument();

    const expand = screen.getByRole("button", {
      name: "Expand the evidence panel",
    });
    expect(expand).toHaveAttribute("title");

    await user.click(expand);

    expect(pane()).toHaveAttribute("data-collapsed", "false");
    expect(pane()).toHaveStyle({ width: "380px" });
    expect(window.localStorage.getItem(COLLAPSED_KEY)).toBe("false");
    expect(within(pane()).getByText("Open a citation")).toBeInTheDocument();
  });

  it("restores the stored width and collapsed state on mount", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem(WIDTH_KEY, "520");
    window.localStorage.setItem(COLLAPSED_KEY, "true");
    renderRoute(SESSION);

    expect(pane()).toHaveAttribute("data-collapsed", "true");

    await user.click(
      screen.getByRole("button", { name: "Expand the evidence panel" }),
    );

    expect(pane()).toHaveStyle({ width: "520px" });
  });

  it("ignores a malformed stored width", () => {
    window.localStorage.setItem(WIDTH_KEY, "not-a-number");
    renderRoute(SESSION);

    expect(pane()).toHaveStyle({ width: "380px" });
  });

  it("keeps the width when switching conversations", async () => {
    const router = renderRoute(SESSION);

    fireEvent.pointerDown(handle(), { pointerId: 1, clientX: 1000 });
    fireEvent.pointerMove(handle(), { pointerId: 1, clientX: 920 });
    fireEvent.pointerUp(handle(), { pointerId: 1 });
    expect(handle()).toHaveAttribute("aria-valuenow", "460");

    await act(async () => {
      await router.navigate(NEXT_SESSION);
    });

    expect(handle()).toHaveAttribute("aria-valuenow", "460");
    expect(pane()).toHaveStyle({ width: "460px" });
  });

  it("expands a collapsed pane when a citation chip is clicked", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem(COLLAPSED_KEY, "true");
    renderRoute(SESSION);

    expect(pane()).toHaveAttribute("data-collapsed", "true");

    await user.click(screen.getByRole("button", { name: "Open page 12" }));

    expect(pane()).toHaveAttribute("data-collapsed", "false");
    expect(
      within(pane()).getByText("Page 12 of ACS_lecture_2_2026F"),
    ).toBeInTheDocument();
    expect(
      within(pane()).getAllByText(
        "MPI_Allreduce combines values from all ranks and distributes the result to all ranks.",
      ).length,
    ).toBeGreaterThan(0);
  });

  it("shows an honest preview notice instead of a loading page image", async () => {
    const user = userEvent.setup();
    renderRoute(SESSION);

    await user.click(screen.getByRole("button", { name: "Open page 12" }));

    const panel = pane();
    expect(within(panel).getByText(/Preview build/)).toBeInTheDocument();
    expect(
      within(panel).queryByText("Loading the page image"),
    ).not.toBeInTheDocument();
    expect(
      within(panel).queryByText(/\/api\/corpus\//),
    ).not.toBeInTheDocument();
    expect(
      within(panel).getByText("Page 12 of ACS_lecture_2_2026F"),
    ).toBeInTheDocument();
  });

  it("resets the page image error when the citation changes outside preview", async () => {
    const user = userEvent.setup();

    function Harness() {
      const [index, setIndex] = useState(0);
      return (
        <>
          <EvidencePanel
            citations={PREVIEW_CITATIONS}
            activeIndex={index}
            onSelect={setIndex}
          />
        </>
      );
    }

    render(
      <I18nProvider initialLang="en">
        <PreviewProvider
          isPreview={false}
          role="student"
          pageState="normal"
          setRole={() => {}}
          setPageState={() => {}}
        >
          <Harness />
        </PreviewProvider>
      </I18nProvider>,
    );

    const image = screen.getByRole("img", {
      name: "Page 12 of ACS_lecture_2_2026F",
    });
    fireEvent.error(image);

    expect(
      screen.getByText(
        "The page image is not available in the local corpus mirror.",
      ),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next page" }));

    expect(
      screen.getByRole("img", { name: "Page 1 of course_project" }),
    ).toBeInTheDocument();
  });
});
