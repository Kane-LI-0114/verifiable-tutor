import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Markdown } from "@/components/ai/markdown";

describe("Markdown", () => {
  it("renders formulas through KaTeX", () => {
    const { container } = render(<Markdown>{"$E = mc^2$"}</Markdown>);

    expect(container.querySelector(".katex")).not.toBeNull();
  });

  it("renders a fenced code block as code", () => {
    const { container } = render(
      <Markdown>{"```python\nprint('hi')\n```"}</Markdown>,
    );

    expect(container.querySelector("pre code, code")).not.toBeNull();
    expect(container.textContent).toContain("print('hi')");
  });
});
