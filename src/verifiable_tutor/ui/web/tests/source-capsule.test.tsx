import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SourceCapsule } from "@/components/chat/source-capsule";
import { I18nProvider } from "@/lib/i18n";
import type { CitationSource } from "@/lib/types";

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
    marker: 2,
    kind: "course",
    title: "Lecture 3: Attention",
    summary: "Subtracting the row maximum keeps softmax stable.",
    doc_id: "ACS_lecture_3_2026F",
    page_no: 9,
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

function renderCapsule(
  sources: CitationSource[],
  open = false,
  onToggle = vi.fn(),
) {
  render(
    <I18nProvider initialLang="en">
      <SourceCapsule sources={sources} open={open} onToggle={onToggle} />
    </I18nProvider>,
  );
  return onToggle;
}

describe("source capsule", () => {
  it("summarizes course pages and web pages", () => {
    renderCapsule(SOURCES);

    const capsule = screen.getByRole("button", {
      name: /Show this answer's citation sources/,
    });

    expect(capsule).toHaveTextContent("2 course pages · 1 web page");
    expect(capsule).toHaveAttribute("aria-expanded", "false");
    expect(capsule).toHaveAttribute("aria-controls", "source-pane");
  });

  it("caps the thumbnail stack and counts the rest", () => {
    renderCapsule([
      ...SOURCES,
      {
        marker: 5,
        kind: "web",
        title: "MPI standard",
        summary: "The MPI standard defines the collective operations.",
        doc_id: null,
        page_no: null,
        url: "https://www.mpi-forum.org/docs/",
      },
    ]);

    expect(screen.getByText("+1")).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: /Show this answer's citation sources/,
      }),
    ).toHaveTextContent("2 course pages · 2 web pages");
  });

  it("toggles the pane from the capsule", async () => {
    const user = userEvent.setup();
    const onToggle = renderCapsule(SOURCES);

    await user.click(
      screen.getByRole("button", {
        name: /Show this answer's citation sources/,
      }),
    );

    expect(onToggle).toHaveBeenCalledTimes(1);
  });
});
