import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import { Markdown } from "@/components/ai/markdown";
import { I18nProvider } from "@/lib/i18n";
import type { CitationSource } from "@/lib/types";

const COURSE_SOURCE: CitationSource = {
  marker: 2,
  kind: "course",
  title: "Lecture 2: Collectives",
  summary: "MPI_Allreduce combines values from all ranks.",
  doc_id: "ACS_lecture_2_2026F",
  page_no: 12,
  url: null,
  chunk_id: "ACS_lecture_2_2026F:p012:c00",
};

const WEB_SOURCE: CitationSource = {
  marker: 3,
  kind: "web",
  title: "DeepSeek API documentation",
  summary: "Search and fetch API reference.",
  doc_id: null,
  page_no: null,
  url: "https://api-docs.deepseek.com/guides/search",
  chunk_id: null,
};

function renderMarkdown(
  content: string,
  sources: CitationSource[],
): ReturnType<typeof render> {
  return render(
    <I18nProvider initialLang="en">
      <MemoryRouter>
        <Markdown sources={sources}>{content}</Markdown>
      </MemoryRouter>
    </I18nProvider>,
  );
}

describe("citation markers", () => {
  it("renders a course marker as a link to the knowledge page", () => {
    renderMarkdown("Allreduce is a collective [ref_2].", [COURSE_SOURCE]);

    const link = screen.getByRole("link", {
      name: "Citation 2: Lecture 2: Collectives",
    });

    expect(link).toHaveAttribute(
      "href",
      "/knowledge/docs/ACS_lecture_2_2026F?page=12",
    );
    expect(link).toHaveTextContent(/^2$/);
  });

  it("renders a web marker as a new-tab source link", () => {
    renderMarkdown("The release is external news [ref_3].", [WEB_SOURCE]);

    const link = screen.getByRole("link", {
      name: "Citation 3: DeepSeek API documentation",
    });

    expect(link).toHaveAttribute(
      "href",
      "https://api-docs.deepseek.com/guides/search",
    );
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("shows the same source row in the marker preview", async () => {
    const user = userEvent.setup();
    renderMarkdown("Allreduce is a collective [ref_2].", [COURSE_SOURCE]);

    await user.hover(
      screen.getByRole("link", { name: "Citation 2: Lecture 2: Collectives" }),
    );

    expect(
      await screen.findByText("MPI_Allreduce combines values from all ranks."),
    ).toBeInTheDocument();
    const preview = document.querySelector(
      '[data-slot="hover-card-content"]',
    );
    expect(preview).not.toBeNull();
    expect(within(preview as HTMLElement).getByText("Course page 12")).toBeInTheDocument();
    expect(within(preview as HTMLElement).getByText("2")).toBeInTheDocument();
  });

  it("leaves an unresolved marker as plain text", () => {
    renderMarkdown("A marker without a source [ref_9].", [COURSE_SOURCE]);

    expect(screen.queryByRole("link", { name: /Citation 9/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /\[9\]/ })).toBeNull();
    expect(screen.getByText(/\[ref_9\]/)).toBeInTheDocument();
  });

  it("leaves an ordinary bracketed number alone", () => {
    renderMarkdown("A literal [1] and a citation [ref_2].", [COURSE_SOURCE]);

    expect(screen.getByText(/\[1\]/)).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /Citation 1/ }),
    ).toBeNull();
    expect(
      screen.getByRole("link", { name: "Citation 2: Lecture 2: Collectives" }),
    ).toHaveTextContent(/^2$/);
  });

  it("leaves an ordinary markdown link on Streamdown's default renderer", () => {
    renderMarkdown("[The docs](https://example.com/guide) are external.", [
      COURSE_SOURCE,
    ]);

    expect(screen.getByRole("button", { name: "The docs" })).toHaveAttribute(
      "data-streamdown",
      "link",
    );
  });
});
