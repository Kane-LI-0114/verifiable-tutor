import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WorkChain } from "@/components/chat/work-chain";
import { I18nProvider } from "@/lib/i18n";
import type { WorkStep } from "@/lib/types";

function step(name: WorkStep["step"]): WorkStep {
  return { step: name, status: "done", duration_ms: 1 };
}

describe("work chain", () => {
  it("orders step rail nodes by phase, not by insertion order", () => {
    render(
      <I18nProvider initialLang="en">
        <WorkChain
          steps={[step("generate"), step("retrieve")]}
          policy="active"
          events={[]}
        />
      </I18nProvider>,
    );

    const retrieve = screen.getByTitle(/Retrieve course pages/);
    const generate = screen.getByTitle(/Write the answer/);
    expect(
      retrieve.compareDocumentPosition(generate) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });
});
