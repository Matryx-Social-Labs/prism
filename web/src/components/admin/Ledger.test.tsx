import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";

import { BarStrip, LedgerSection, figure, share } from "@/components/admin/Ledger";
import type { MetricSection } from "@/lib/admin";

describe("the ledger's rules", () => {
  it("prints a small share as a count and a large one as a percentage", () => {
    // A percentage of four readers reads as a fact about a market.
    expect(share(3, 4)).toBe("3 of 4");
    expect(share(29, 29)).toBe("29 of 29");
    expect(share(12, 40)).toBe("30%");
  });

  it("prints what was not counted as a dash, never a zero", () => {
    expect(figure(null, "count")).toBe("—");
    expect(figure(0, "count")).toBe("0");
    expect(figure(249, "inr")).toBe("₹249");
  });

  it("leaves a day before counting began empty, and draws a counted zero", () => {
    const { container } = render(<BarStrip series={[null, null, 0, 3, 5]} start="2031-01-27" label="Views" />);
    const painted = container.querySelectorAll('rect[fill^="var(--ink"]');
    expect(painted).toHaveLength(3); // the zero stub, 3 and 5 — nothing for the two uncounted days
    expect(container.querySelector("svg")!.getAttribute("aria-label")).toBe("Views: 8 in all, most on 31 Jan (5)");
    // Every bar answers on hover, uncounted days included.
    expect(Array.from(container.querySelectorAll("title")).map((t) => t.textContent)).toContain("27 Jan: not counted");
    // The latest day is the one in full ink.
    expect(painted[painted.length - 1].getAttribute("fill")).toBe("var(--ink)");
  });

  it("sums a long period into weeks rather than drawing bars thinner than their gaps", () => {
    const { container } = render(<BarStrip series={Array(90).fill(1)} start="2030-11-03" label="Views" />);
    expect(container.querySelectorAll('rect[fill^="var(--ink"]')).toHaveLength(13);
  });

  it("names where every figure was counted, and keeps each day readable without hovering", () => {
    const section: MetricSection = {
      key: "visits",
      title: "Visits",
      rows: [
        { key: "views", label: "Page views", current: 7, previous: null, series: [null, 2, 5], unit: "count", source: "usage_daily · counting since 28 Jan", note: null },
      ],
      breakdowns: [{ key: "pages", title: "Views by kind of page", rows: [{ label: "story", current: 5, previous: null }], source: "usage_daily" }],
    };
    render(<LedgerSection section={section} start="2031-01-27" />);
    expect(screen.getByText("usage_daily · counting since 28 Jan")).toBeInTheDocument();
    const days = within(screen.getByText("Day by day").closest("details")!);
    expect(days.getByRole("row", { name: /27 Jan/ })).toHaveTextContent("—");
    expect(days.getByRole("row", { name: /29 Jan/ })).toHaveTextContent("5");
  });
});
