import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import PressPage, { metadata } from "@/app/press/page";
import type { MonitoredFeed } from "@/lib/api";

const fetchSources = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", async () => ({ ...(await vi.importActual<typeof import("@/lib/api")>("@/lib/api")), fetchSources }));

const web = (p: string) => path.resolve(__dirname, "../../..", p);
const llms = readFileSync(web("public/llms.txt"), "utf8").split("\n");
const feed = (slug: string, language: string): MonitoredFeed => ({
  slug, name: slug, publisher: slug, code: "XX", origin: "national", language, state: null, sector: null,
  domain: null, official: false, checked_at: null, ok_at: null, reachable: true,
});

beforeEach(() => fetchSources.mockReset());

describe("/press — the press kit", () => {
  it("says what Prism is and how to cite it in /llms.txt's own words", async () => {
    fetchSources.mockResolvedValue(null);
    render(await PressPage());
    const page = document.body.textContent ?? "";
    const paragraph = llms.find((l) => l.startsWith("> "))!.slice(2);
    expect(paragraph).toMatch(/India's verifiable news record/);
    expect(page).toContain(paragraph);
    for (const start of ["- Cite a record as:", "- A quote has its own address"]) {
      expect(page).toContain(llms.find((l) => l.startsWith(start))!.slice(2));
    }
  });

  it("links how it works, the rules, who answers for it, the press contact and, apart, the Grievance Officer", async () => {
    fetchSources.mockResolvedValue(null);
    render(await PressPage());
    expect(screen.getByRole("heading", { level: 1, name: "Press" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /One real story/ })).toHaveAttribute("href", "/about");
    expect(screen.getByRole("link", { name: /Each rule/ })).toHaveAttribute("href", "/about#refuses");
    expect(screen.getByRole("link", { name: /Who writes a record/ })).toHaveAttribute("href", "/about#accountability");
    expect(screen.getByRole("link", { name: "hello@readprism.news" })).toHaveAttribute("href", "mailto:hello@readprism.news");
    expect(screen.getByRole("link", { name: "Grievances" })).toHaveAttribute("href", "/grievance");
    expect(document.body.textContent).toContain("Prism Media Intelligence LLP");
    expect(screen.getByText("No invented numbers.")).toBeInTheDocument();
    expect(metadata.alternates?.canonical).toBe("/press");
    expect(metadata.openGraph?.url).toBe("/press");
  });

  it("offers the lockup and the mark as SVG and PNG for light and dark grounds, every file present", async () => {
    fetchSources.mockResolvedValue(null);
    render(await PressPage());
    const downloads = screen.getAllByRole("link").filter((a) => a.hasAttribute("download")).map((a) => a.getAttribute("href")!);
    expect(downloads.sort()).toEqual(
      ["prism-mark", "readprism-lockup"].flatMap((f) => ["dark", "light"].flatMap((g) => ["png", "svg"].map((x) => `/brand/${f}-on-${g}.${x}`))).sort(),
    );
    for (const href of downloads) expect(existsSync(web(`public${href}`)), href).toBe(true);
    // The lockup is the address; the retired "Prism"-only lockup is not offered.
    expect(downloads.some((h) => h.startsWith("/brand/prism-lockup"))).toBe(false);
  });

  it("counts the monitored list from the API, and leaves the line out when the API is down", async () => {
    fetchSources.mockResolvedValue({ outlets: 3, checked_at: null, feeds: [feed("a", "en"), feed("b", "hi"), feed("c", "en")] });
    const { unmount } = render(await PressPage());
    expect(screen.getByRole("link", { name: "3 monitored outlets · 2 languages" })).toHaveAttribute("href", "/sources");
    unmount();
    fetchSources.mockResolvedValue(null);
    render(await PressPage());
    expect(document.body.textContent).not.toMatch(/monitored outlets ·/);
  });
});
