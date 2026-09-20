import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LegalPage } from "@/components/LegalPage";
import { CONTACT_EMAIL, LEGAL_DOCS } from "@/lib/legal";

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
    const rail = screen.getByRole("complementary", { name: "On this page" });
    for (const s of LEGAL_DOCS[0].sections) {
      const a = within(rail).getByRole("link", { name: s.heading });
      expect(a.getAttribute("href")).toMatch(/^#[a-z0-9-]+$/);
      expect(document.getElementById(a.getAttribute("href")!.slice(1))).toBeInTheDocument();
      if (s.short) expect(screen.getAllByText(s.short).length).toBeGreaterThan(0);
    }
    expect(screen.getAllByText("In short").length).toBeGreaterThan(0);
  });
});
