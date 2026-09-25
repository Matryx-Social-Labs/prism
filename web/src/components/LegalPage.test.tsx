import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LegalPage } from "@/components/LegalPage";
import { CONTACT_EMAIL, LEGAL_DOCS, LEGAL_ENTITY } from "@/lib/legal";

describe("LegalPage", () => {
  it.each(LEGAL_DOCS)("renders $slug with its title, every section and a way to reach us", (doc) => {
    render(<LegalPage doc={doc} />);
    expect(screen.getByRole("heading", { level: 1, name: doc.title })).toBeInTheDocument();
    for (const s of doc.sections) expect(screen.getByRole("heading", { level: 2, name: s.heading })).toBeInTheDocument();
    expect(document.body.textContent).toContain(CONTACT_EMAIL);
  });

  it("links each document to the other two", () => {
    render(<LegalPage doc={LEGAL_DOCS[0]} />);
    const hrefs = screen.getAllByRole("link").map((a) => a.getAttribute("href"));
    expect(hrefs).toContain("/terms");
    expect(hrefs).toContain("/refunds");
  });

  it("carries 'On this page' with an anchor per section, and each section's one-sentence version", () => {
    render(<LegalPage doc={LEGAL_DOCS[0]} />);
    const rail = screen.getByRole("navigation", { name: "On this page" });
    const chips = screen.getByRole("navigation", { name: "Sections" });
    for (const [i, s] of LEGAL_DOCS[0].sections.entries()) {
      // Numbered, in order: the rail prints 01, 02 … beside each heading.
      const a = within(rail).getByRole("link", { name: (name) => name.endsWith(s.heading) });
      expect(a.textContent).toBe(`${String(i + 1).padStart(2, "0")}${s.heading}`);
      expect(within(chips).getByRole("link", { name: s.heading })).toHaveAttribute("href", a.getAttribute("href"));
      expect(a.getAttribute("href")).toMatch(/^#[a-z0-9-]+$/);
      expect(document.getElementById(a.getAttribute("href")!.slice(1))).toBeInTheDocument();
      if (s.short) expect(screen.getAllByText(s.short).length).toBeGreaterThan(0);
    }
    expect(screen.getAllByText("In short").length).toBeGreaterThan(0);
    // The first section is the one marked until the reader scrolls.
    expect(within(rail).getAllByRole("link")[0]).toHaveAttribute("aria-current", "true");
  });

  it("names who is behind it and never rewrites the legal text", () => {
    const doc = LEGAL_DOCS[2];
    render(<LegalPage doc={doc} />);
    expect(screen.getAllByText(LEGAL_ENTITY).length).toBeGreaterThan(0);
    expect(document.body.textContent).toContain(doc.lede);
    for (const s of doc.sections) for (const b of s.blocks) for (const line of typeof b === "string" ? [b] : b) expect(document.body.textContent).toContain(line);
  });
});
