import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import MarketingPage from "@/app/admin/marketing/page";

const fetchLinks = vi.hoisted(() => vi.fn());
const makeLink = vi.hoisted(() => vi.fn());
const setLinkArchived = vi.hoisted(() => vi.fn());
const fetchMetrics = vi.hoisted(() => vi.fn());
const fetchFeed = vi.hoisted(() => vi.fn());
const searchEvents = vi.hoisted(() => vi.fn());
const fetchEvent = vi.hoisted(() => vi.fn());
const ADMIN = vi.hoisted(() => ({ session: { token: "t", userId: "u", email: "f@example.test" }, email: "f@example.test" }));
vi.mock("@/components/admin/AdminShell", async (orig) => ({ ...(await orig<typeof import("@/components/admin/AdminShell")>()), useAdmin: () => ADMIN }));
vi.mock("@/lib/admin", async (orig) => ({ ...(await orig<typeof import("@/lib/admin")>()), fetchLinks, makeLink, setLinkArchived, fetchMetrics }));
vi.mock("@/lib/api", async (orig) => ({ ...(await orig<typeof import("@/lib/api")>()), fetchFeed, searchEvents, fetchEvent, fetchSources: async () => ({ outlets: 41 }) }));

const goals = (over = {}) => ({ read2: 0, signin: 0, account: 0, plus: 0, digest: 0, ...over });
const link = (code: string, over = {}) => ({
  code, path: "/story/abc", kind: "story", title: "Boeing 737 MAX software glitch", platform: "whatsapp", medium: "message",
  campaign: "launch-week", note: "", created_by: "f@example.test", created_at: "2026-09-29T08:30:00Z", archived_at: null,
  url: `https://www.readprism.news/story/abc?utm_source=whatsapp&utm_medium=message&utm_campaign=launch-week&utm_content=${code}`,
  short_url: `https://readprism.news/go/${code}`, visits: 0, goals: goals(), series: [null, 0, 0], ...over,
});
const payload = (links: unknown[]) => ({
  range: { days: 28, start: "2026-09-02", end: "2026-09-29", tz: "Asia/Kolkata" },
  platforms: { whatsapp: "message", x: "social", instagram: "social", linkedin: "social" },
  media: ["community", "email", "launch", "message", "social"],
  campaigns: ["launch-week"],
  links,
});

beforeEach(() => {
  fetchLinks.mockReset().mockResolvedValue(payload([
    link("k3f9qa", { visits: 12, goals: goals({ read2: 5, account: 1 }) }),
    link("m7p2xr", { platform: "x", medium: "social", campaign: "", visits: 3 }),
    link("q4w8zz", { archived_at: "2026-09-29T09:00:00Z" }),
  ]));
  fetchMetrics.mockReset().mockResolvedValue({ sections: [] });
  fetchFeed.mockReset().mockResolvedValue([{ id: "abc", title: "Boeing 737 MAX software glitch", source_count: 9 }]);
  searchEvents.mockReset().mockResolvedValue([]);
  fetchEvent.mockReset().mockResolvedValue({ title: "Boeing 737 MAX software glitch", sources: [{ publisher: "a" }, { publisher: "b" }], monitored_outlets: 41 });
  makeLink.mockReset().mockResolvedValue(link("n5t6vw", { platform: "x", medium: "social" }));
  setLinkArchived.mockReset().mockResolvedValue(link("k3f9qa", { archived_at: "2026-09-29T10:00:00Z" }));
});

describe("Marketing — the links and what they brought", () => {
  it("lists live links with their counts, and adds them up by platform and by campaign", async () => {
    render(<MarketingPage />);
    const row = within((await screen.findByText("k3f9qa")).closest("tr")!);
    expect(row.getByText("12")).toBeInTheDocument();
    expect(row.getByText("5")).toBeInTheDocument();
    expect(row.getByText("launch-week")).toBeInTheDocument();
    expect(screen.queryByText("q4w8zz")).not.toBeInTheDocument(); // archived: hidden from Live
    expect(screen.getByRole("radio", { name: /Archived/ })).toHaveTextContent("1");
    const byPlatform = within(screen.getByRole("region", { name: "Founder links, by platform" }));
    expect(byPlatform.getByText("WhatsApp")).toBeInTheDocument();
    expect(byPlatform.getByText("X")).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Founder links, by campaign" })).getByText("no campaign")).toBeInTheDocument();
  });

  it("archives a link on request, and the list is read again", async () => {
    render(<MarketingPage />);
    const row = within((await screen.findByText("k3f9qa")).closest("tr")!);
    await userEvent.click(row.getByRole("button", { name: "Archive k3f9qa" }));
    expect(setLinkArchived).toHaveBeenCalledWith(ADMIN.session, "k3f9qa", true);
    expect(fetchLinks).toHaveBeenCalledTimes(2);
  });
});

describe("Marketing — making a link", () => {
  it("refuses a page that is not Prism's, in words, and makes nothing", async () => {
    render(<MarketingPage />);
    await userEvent.type(await screen.findByLabelText("A Prism page"), "https://evil.example/story/x");
    expect(screen.getByText(/That is not a public Prism page/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Make the WhatsApp link/ })).toBeDisabled();
  });

  it("makes no link to a page that is not there: the link would open an error", async () => {
    fetchEvent.mockRejectedValue(new Error("/api/v1/events/gone failed: 404"));
    render(<MarketingPage />);
    await userEvent.type(await screen.findByLabelText("A Prism page"), "/story/gone");
    expect(await screen.findByText(/No such page, or it could not be read/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Make the WhatsApp link/ })).toBeDisabled();
    expect(makeLink).not.toHaveBeenCalled();
  });

  it("never shows an older period's links over the one asked for last", async () => {
    let answer28: (v: unknown) => void = () => undefined;
    fetchLinks.mockReset()
      .mockImplementationOnce(() => new Promise((r) => { answer28 = r; }))
      .mockResolvedValue(payload([link("seven7", { visits: 7 })]));
    render(<MarketingPage />);
    await userEvent.click(await screen.findByRole("tab", { name: "7 days" }));
    expect(await screen.findByText("seven7")).toBeInTheDocument();
    answer28(payload([link("twenty", { visits: 28 })]));
    await new Promise((r) => setTimeout(r, 20));
    expect(screen.queryByText("twenty")).not.toBeInTheDocument();
    expect(screen.getByText("seven7")).toBeInTheDocument();
  });

  it("makes a link for the story picked and the platform chosen, then gives the short link, a post and the images", async () => {
    render(<MarketingPage />);
    const picks = within(await screen.findByRole("list", { name: "Today's top stories" }));
    await userEvent.click(await picks.findByRole("button", { name: /Boeing 737 MAX software glitch/ }));
    await userEvent.click(screen.getByRole("radio", { name: "X" }));
    await userEvent.type(screen.getByLabelText("Campaign"), "Launch Week");
    await screen.findByText("Boeing 737 MAX software glitch", { selector: ".font-semibold" });
    await userEvent.click(screen.getByRole("button", { name: "Make the X link" }));
    expect(makeLink).toHaveBeenCalledWith(ADMIN.session, {
      target: "/story/abc", platform: "x", medium: "social", campaign: "launch-week", title: "Boeing 737 MAX software glitch", note: "",
    });
    const made = within(await screen.findByRole("group", { name: "The X link" }));
    expect(made.getByText("https://readprism.news/go/n5t6vw")).toBeInTheDocument();
    expect((made.getByLabelText("The post for X") as HTMLTextAreaElement).value).toContain("Reported by 2 of 41 monitored outlets");
    expect(made.getByRole("link", { name: "Open in X" }).getAttribute("href")).toContain("x.com/intent/post");
    expect(made.getByRole("link", { name: /Instagram Story/ })).toHaveAttribute("href", "/card/story/story/abc");
  });
});
