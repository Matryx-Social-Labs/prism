import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import ForPublishersPage, { metadata } from "@/app/for-publishers/page";

describe("/for-publishers — for the outlets Prism reads", () => {
  it("says what Prism takes, what it sends back, and the ways in to correct or remove", () => {
    render(<ForPublishersPage />);
    expect(screen.getByRole("heading", { level: 1, name: "For the outlets Prism reads" })).toBeInTheDocument();
    for (const name of ["What Prism reads", "What a record shows from your report", "What it sends back", "Corrections and removal", "The list"]) {
      expect(screen.getByRole("heading", { level: 2, name })).toBeInTheDocument();
    }
    const page = document.body.textContent ?? "";
    // The limits the code enforces (api/routes/events.py CONTEXT_CHARS, lib/images.ts, lib/ogCard.tsx).
    expect(page).toContain("at most 220 characters of the article either side");
    expect(page).toContain("Prism does not keep a copy");
    expect(page).toContain("Share cards never carry one");
    expect(page).toContain("No page on Prism prints your article");
    expect(screen.getByRole("link", { name: "grievance form" }).getAttribute("href")).toMatch(/^\/grievance\?kind=.+#complain$/);
    expect(screen.getByRole("link", { name: "grievance@readprism.news" })).toHaveAttribute("href", "mailto:grievance@readprism.news");
    expect(screen.getByRole("link", { name: "hello@readprism.news" })).toHaveAttribute("href", "mailto:hello@readprism.news");
    expect(screen.getByRole("link", { name: "Corrections" })).toHaveAttribute("href", "/corrections");
    expect(screen.getByRole("link", { name: /The outlets Prism reads/ })).toHaveAttribute("href", "/sources");
    expect(metadata.alternates?.canonical).toBe("/for-publishers");
    expect(metadata.openGraph?.url).toBe("/for-publishers");
  });
});
