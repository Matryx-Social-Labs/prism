import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Brand } from "@/components/Brand";

/**
 * The wordmark is the address (Design System v2 · screens/Wordmark.html, adopted
 * 2026-09-28). prism.news belongs to someone else, so a lockup reading "Prism"
 * alone teaches readers to type the bare name and land on a parked page — the
 * getdropbox.com problem. The lockup spells readprism.news; Prism carries the weight.
 */
describe("Brand", () => {
  it("names the link by its visible text, the address, with no aria-label hiding it", () => {
    render(<Brand />);
    const link = screen.getByRole("link", { name: "readPrism.news" });
    expect(link).toHaveAttribute("href", "/");
    expect(link).not.toHaveAttribute("aria-label");
  });

  it("sets read and .news quiet (regular, ink-3) around a full-ink Prism", () => {
    render(<Brand />);
    const word = screen.getByRole("link").querySelector("span")!;
    const [read, news] = [...word.querySelectorAll("span")];
    for (const [el, text] of [[read, "read"], [news, ".news"]] as const) {
      expect(el).toHaveTextContent(text);
      expect(el.style.color).toBe("var(--ink-3)");
      expect(el).toHaveClass("font-normal");
    }
    expect(word).toHaveClass("font-semibold");
    expect(word.style.color).toBe("");
  });
});
