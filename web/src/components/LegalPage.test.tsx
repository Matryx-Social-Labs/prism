import { render, screen } from "@testing-library/react";
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
    expect(hrefs).toEqual(["/terms", "/refunds"]);
  });
});
