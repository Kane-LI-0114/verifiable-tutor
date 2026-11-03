import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { I18nProvider, useI18n } from "@/lib/i18n";
import { en } from "@/lib/i18n/en";
import { zh } from "@/lib/i18n/zh";

function flattenedKeys(value: unknown, prefix = ""): string[] {
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => flattenedKeys(item, `${prefix}[${index}]`));
  }
  if (value !== null && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>).flatMap(
      ([key, child]) => flattenedKeys(child, prefix ? `${prefix}.${key}` : key),
    );
  }
  return [prefix];
}

function Probe() {
  const { t, lang, toggleLang } = useI18n();
  return (
    <div>
      <span>{t.nav.chat}</span>
      <span>{lang}</span>
      <button type="button" onClick={toggleLang}>
        switch
      </button>
    </div>
  );
}

describe("translations", () => {
  it("defines the same keys in both languages", () => {
    const english = flattenedKeys(en).sort();
    const chinese = flattenedKeys(zh).sort();

    expect(chinese).toEqual(english);
  });

  it("switches language, copy, and the document language attribute", async () => {
    const user = userEvent.setup();

    render(
      <I18nProvider initialLang="en">
        <Probe />
      </I18nProvider>,
    );

    expect(screen.getByText("Chat")).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("en");

    await user.click(screen.getByRole("button", { name: "switch" }));

    expect(screen.getByText("对话")).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("zh-CN");
  });
});
