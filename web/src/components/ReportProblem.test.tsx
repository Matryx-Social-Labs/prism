import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { expect, test, vi } from "vitest";

const links = vi.hoisted(() => [] as { href: string; prefetch?: boolean | null }[]);
vi.mock("next/link", () => ({
  default: ({ href, prefetch, rel, children }: { href: string; prefetch?: boolean | null; rel?: string; children: ReactNode }) => {
    links.push({ href, prefetch });
    return <a href={href} rel={rel}>{children}</a>;
  },
}));

import { PROBLEMS, ReportProblem } from "@/components/ReportProblem";

// Each link is /grievance?kind=…&record=<this story>: a different address per
// story, and /grievance renders on the server for every one. Followed by
// crawlers (mostly Claude-SearchBot) and prefetched by browsers, every story
// view cost four renders nobody asked for: 43% of all Vercel requests on
// 2026-11-02. (Prefetch is asserted on the prop: outside the app router,
// next/link observes every link whether or not it prefetches.)
test("the report links are neither prefetched nor followed", () => {
  render(<ReportProblem path="/story/abc" />);
  const anchors = PROBLEMS.map((kind) => screen.getByRole("link", { name: kind }));
  expect(anchors).toHaveLength(4);
  expect(anchors.map((a) => a.getAttribute("rel"))).toEqual(["nofollow", "nofollow", "nofollow", "nofollow"]);
  expect(links).toHaveLength(4);
  expect(links[0].href).toContain("record=%2Fstory%2Fabc");
  expect(links.map((l) => l.prefetch)).toEqual([false, false, false, false]);
});
