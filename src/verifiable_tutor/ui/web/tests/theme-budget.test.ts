import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";

import { describe, expect, it } from "vitest";

// The interface carries one neutral family, one accent family, and one
// semantic family. A stray hue is how a second identity leaks in, so the
// component tree is scanned rather than trusted.
//
// Neutral: the greys that carry text, surfaces, and borders.
// Accent: cobalt, used for interaction and for marking where a claim came from.
// Semantic: red, used only for failure and destructive actions.
const ALLOWED_HUES = new Set([
  "neutral",
  "zinc",
  "gray",
  "stone",
  "slate",
  "blue",
  "red",
]);

// Every hue Tailwind ships, so that an animation utility such as
// slide-in-from-bottom-10 is not mistaken for a colour utility.
const TAILWIND_HUES = new Set([
  "slate",
  "gray",
  "zinc",
  "neutral",
  "stone",
  "red",
  "orange",
  "amber",
  "yellow",
  "lime",
  "green",
  "emerald",
  "teal",
  "cyan",
  "sky",
  "blue",
  "indigo",
  "violet",
  "purple",
  "fuchsia",
  "pink",
  "rose",
]);

// Matches a Tailwind colour utility that names a hue and a shade, such as
// bg-emerald-600 or border-amber-500/40. Layout utilities (border-2, text-sm)
// and directional animation utilities do not match.
const COLOUR_UTILITY =
  /\b(?:bg|text|border|ring|fill|stroke|from|via|to|shadow|outline|decoration|divide|accent|caret|placeholder)-([a-z]+)-(\d{2,3})\b/g;

const SRC = join(process.cwd(), "src");

function sourceFiles(dir: string): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      found.push(...sourceFiles(path));
    } else if (/\.(ts|tsx)$/.test(entry.name) && !/\.test\./.test(entry.name)) {
      found.push(path);
    }
  }
  return found;
}

describe("theme colour budget", () => {
  it("uses only the neutral, accent, and semantic colour families", () => {
    const offenders: string[] = [];
    for (const file of sourceFiles(SRC)) {
      const lines = readFileSync(file, "utf8").split("\n");
      lines.forEach((line, index) => {
        for (const match of line.matchAll(COLOUR_UTILITY)) {
          if (TAILWIND_HUES.has(match[1]) && !ALLOWED_HUES.has(match[1])) {
            offenders.push(`${relative(SRC, file)}:${index + 1}  ${match[0]}`);
          }
        }
      });
    }
    expect(offenders).toEqual([]);
  });
});
