import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { SourceRef, XPostOut } from "@/lib/api";
import { XPosts, firstOnX } from "@/components/XPosts";

const post = (over: Partial<XPostOut> = {}): XPostOut => ({
  post_id: "1001",
  handle: "RBI",
  name: "Reserve Bank of India",
  tier: "official",
  profile_image_url: "https://pbs.example/rbi.jpg",
  url: "https://x.com/RBI/status/1001",
  text: "RBI announces an OMO sale of Government of India securities\nfor ₹20,000 crore",
  created_at: "2026-09-21T09:00:00+00:00",
  method: "judge",
  score: 0.91,
  ...over,
});

const source = (published_at: string | null): SourceRef =>
  ({ article_id: "a", source_name: "Mint", source_slug: "livemint", url: "https://mint.example/a", title: "t", published_at } as unknown as SourceRef);

describe("the row X's display rules and the record agree on", () => {
  it("prints the author linking to the profile, the text as written, the time linking to the post, and View on X", () => {
    render(<XPosts posts={[post()]} sources={[source("2026-09-21T10:00:00+00:00")]} />);
    const name = screen.getByRole("link", { name: "Reserve Bank of India" });
    expect(name).toHaveAttribute("href", "https://x.com/RBI");
    expect(screen.getByRole("link", { name: "@RBI" })).toHaveAttribute("href", "https://x.com/RBI");
    // Verbatim, line break and all — never truncated, never "smartened".
    expect(screen.getByText(/OMO sale of Government of India securities/).textContent).toBe(post().text);
    expect(screen.getByRole("link", { name: "View on X ↗" })).toHaveAttribute("href", "https://x.com/RBI/status/1001");
    expect(document.querySelector("time")?.closest("a")).toHaveAttribute("href", "https://x.com/RBI/status/1001");
    expect(screen.getByLabelText("X")).toBeInTheDocument();
  });

  it("renders nothing for an empty list — a head with nothing under it would advertise absence", () => {
    const { container } = render(<XPosts posts={[]} sources={[]} />);
    expect(container.innerHTML).toBe("");
  });
});

describe("first on X", () => {
  const before = post({ created_at: "2026-09-21T06:00:00+00:00" });
  const after = post({ post_id: "1002", created_at: "2026-09-21T12:00:00+00:00" });

  it("is the earliest post strictly before the earliest report's own clock", () => {
    expect(firstOnX([after, before], [source("2026-09-21T10:00:00+00:00")])?.post_id).toBe("1001");
    expect(firstOnX([after], [source("2026-09-21T10:00:00+00:00")])).toBeNull();
    expect(firstOnX([post({ created_at: "2026-09-21T10:00:00+00:00" })], [source("2026-09-21T10:00:00+00:00")])).toBeNull();
  });

  it("never names a post that links a report we hold, and needs a dated report to compare against", () => {
    expect(firstOnX([post({ created_at: "2026-09-21T06:00:00+00:00", method: "url" })], [source("2026-09-21T10:00:00+00:00")])).toBeNull();
    expect(firstOnX([before], [source(null)])).toBeNull();
    expect(firstOnX([before], [])).toBeNull();
  });

  it("is printed as one mono line above the rows, and only then", () => {
    render(<XPosts posts={[before]} sources={[source("2026-09-21T10:00:00+00:00")]} />);
    expect(screen.getByText(/First on X · @RBI ·/)).toBeInTheDocument();
  });
});
