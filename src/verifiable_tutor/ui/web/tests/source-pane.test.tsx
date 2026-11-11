import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SourcePane } from "@/components/chat/source-pane";
import { I18nProvider } from "@/lib/i18n";
import type { CitationSource } from "@/lib/types";

import { installMemoryStorage } from "./memory-storage";

const SOURCES: CitationSource[] = [
  {
    marker: 1,
    kind: "course",
    title: "Lecture 2: Collectives",
    summary: "MPI_Allreduce combines values from all ranks.",
    doc_id: "ACS_lecture_2_2026F",
    page_no: 12,
    url: null,
  },
  {
    marker: 4,
    kind: "web",
    title: "DeepSeek API documentation",
    summary: "Search and fetch API reference.",
    doc_id: null,
    page_no: null,
    url: "https://api-docs.deepseek.com/guides/search",
  },
];

function renderPane(onClose = vi.fn()) {
  render(
    <I18nProvider initialLang="en">
      <MemoryRouter>
        <SourcePane sources={SOURCES} onClose={onClose} />
      </MemoryRouter>
    </I18nProvider>,
  );
  return onClose;
}

beforeEach(() => {
  installMemoryStorage();
});

describe("source pane", () => {
  it("lists one row per retrieved source with its marker and target", () => {
    renderPane();

    const pane = screen.getByTestId("source-pane");

    expect(pane).toHaveAttribute("id", "source-pane");
    expect(within(pane).getByText("Sources")).toBeInTheDocument();
    expect(within(pane).getByText("2 sources")).toBeInTheDocument();
    expect(within(pane).getByText("Lecture 2: Collectives")).toBeInTheDocument();
    expect(
      within(pane).getByText("MPI_Allreduce combines values from all ranks."),
    ).toBeInTheDocument();
    expect(within(pane).getByText("[1]")).toBeInTheDocument();
    expect(within(pane).getByText("[4]")).toBeInTheDocument();
    expect(within(pane).getByText("Course page 12")).toBeInTheDocument();
    expect(
      within(pane).getByText("Web page · api-docs.deepseek.com"),
    ).toBeInTheDocument();

    expect(
      within(pane).getByRole("link", { name: /Lecture 2: Collectives/ }),
    ).toHaveAttribute("href", "/knowledge/docs/ACS_lecture_2_2026F?page=12");

    const web = within(pane).getByRole("link", {
      name: /DeepSeek API documentation/,
    });
    expect(web).toHaveAttribute(
      "href",
      "https://api-docs.deepseek.com/guides/search",
    );
    expect(web).toHaveAttribute("target", "_blank");
    expect(web).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("closes from the pane header button", async () => {
    const user = userEvent.setup();
    const onClose = renderPane();

    await user.click(
      screen.getByRole("button", { name: "Collapse citation sources" }),
    );

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("starts at the default width and remembers a pointer resize", () => {
    renderPane();

    const handle = screen.getByRole("separator", {
      name: "Resize the citation sources pane",
    });
    expect(handle).toHaveAttribute("aria-valuenow", "380");

    fireEvent.pointerDown(handle, { pointerId: 1, clientX: 1000 });
    fireEvent.pointerMove(handle, { pointerId: 1, clientX: 900 });
    fireEvent.pointerUp(handle, { pointerId: 1 });

    expect(handle).toHaveAttribute("aria-valuenow", "480");
    expect(window.localStorage.getItem("vt.sources.width")).toBe("480");
  });

  it("resizes with the keyboard and resets with a double click", async () => {
    const user = userEvent.setup();
    renderPane();

    const handle = screen.getByRole("separator", {
      name: "Resize the citation sources pane",
    });
    act(() => handle.focus());

    await user.keyboard("{ArrowLeft}");
    expect(handle).toHaveAttribute("aria-valuenow", "396");

    fireEvent.doubleClick(handle);
    expect(handle).toHaveAttribute("aria-valuenow", "380");
  });
});
