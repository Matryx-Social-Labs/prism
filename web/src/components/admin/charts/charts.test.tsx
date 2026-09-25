import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { BarList, Funnel } from "./Bars";
import { ChartPanel } from "./ChartPanel";
import { CohortGrid, step } from "./CohortGrid";
import { DotPlot } from "./DotPlot";
import { change, figure, share } from "./format";
import { KpiTile, Sparkline } from "./KpiTile";
import { stackKeys, StackedBars } from "./StackedBars";
import { TrendChart, isolated, trendTable, uncountedSpan } from "./TrendChart";

// Recharts measures its container with getBoundingClientRect, which jsdom
// answers with zeros — and a chart with no width draws nothing at all.
beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({ width: 640, height: 180, top: 0, left: 0, right: 640, bottom: 180, x: 0, y: 0, toJSON: () => ({}) });
});
afterEach(() => vi.restoreAllMocks());

describe("the numbers' rules", () => {
  it("prints a small share as a count and a large one as a percentage", () => {
    // A percentage of four readers reads as a fact about a market.
    expect(share(3, 4)).toBe("3 of 4");
    expect(share(29, 29)).toBe("29 of 29");
    expect(share(12, 40)).toBe("30%");
  });

  it("prints what was not counted as a dash, never a zero", () => {
    expect(figure(null)).toBe("—");
    expect(figure(0)).toBe("0");
    expect(figure(249, "inr")).toBe("₹249");
  });

  it("gives a change off a small base as a count, off a large one as a percentage", () => {
    expect(change(7, 4)).toEqual({ text: "+3 from 4", dir: "up" });
    expect(change(88, 100)).toEqual({ text: "−12%", dir: "down" });
    expect(change(5, 5)).toEqual({ text: "±0 from 5", dir: "flat" });
    expect(change(40, 40)).toEqual({ text: "±0%", dir: "flat" });
    // Nothing counted before: no change to claim.
    expect(change(5, null)).toBeNull();
  });
});

describe("the trend", () => {
  it("hatches the days before counting began and says so in the key", () => {
    const { container } = render(<TrendChart series={[null, null, 3, 4]} start="2031-01-27" label="Views" />);
    expect(screen.getByText("Hatched: not counted yet, never zero")).toBeInTheDocument();
    expect(container.querySelector("pattern")).not.toBeNull();
    // Counted from the first day: nothing hatched, nothing in the key about it.
    render(<TrendChart series={[1, 2, 3, 4]} start="2031-01-27" label="Clicks" />);
    expect(screen.getAllByText("Hatched: not counted yet, never zero")).toHaveLength(1);
  });

  it("shades only the leading days with no record, and none once counting began", () => {
    const pts = (xs: Array<number | null>) => xs.map((now, i) => ({ label: `d${i}`, now }));
    expect(uncountedSpan(pts([null, null, 0, 3]))).toEqual(["d0", "d1"]);
    // A counted zero is a record: nothing to shade.
    expect(uncountedSpan(pts([0, 0, 3]))).toBeNull();
    expect(uncountedSpan(pts([null, null]))).toEqual(["d0", "d1"]);
  });

  it("draws the period and, with a legend, the period before", () => {
    const { container } = render(<TrendChart series={[1, 4, 2]} prev={[2, 2, 2]} start="2031-01-27" label="Views" />);
    expect(container.querySelector(".recharts-area")).not.toBeNull();
    expect(container.querySelector(".recharts-line")).not.toBeNull();
    expect(screen.getByText("Period before")).toBeInTheDocument();
  });

  it("draws no period-before line when nothing was counted then", () => {
    const { container } = render(<TrendChart series={[1, 4, 2]} prev={[null, null, null]} start="2031-01-27" label="Views" />);
    expect(container.querySelector(".recharts-line")).toBeNull();
    expect(screen.queryByText("Period before")).not.toBeInTheDocument();
  });

  it("marks a counted day with no neighbour on record, which no line would show", () => {
    // Counting began on the last day of the period: one point, no line.
    expect(isolated([null, null, 6], 2)).toBe(true);
    expect(isolated([null, 3, 6], 2)).toBe(false);
    expect(isolated([null, null, 6], 1)).toBe(false);
  });

  it("has a table twin that keeps an uncounted day as no number", () => {
    const t = trendTable([null, 2, 5], [1, 1, 1], "2031-01-27", "Views");
    expect(t.columns).toEqual(["Day (IST)", "Views", "Period before"]);
    expect(t.rows[0]).toEqual(["27 Jan", null, 1]);
  });
});

describe("stacked bars", () => {
  const daily = (n: number) => [n, n];

  it("folds past six words into Other, so no two words share a colour", () => {
    const series = Object.fromEntries(["a", "b", "c", "d", "e", "f", "g", "h"].map((k, i) => [k, daily(10 - i)]));
    const { keys, series: drawn } = stackKeys(series);
    expect(keys).toEqual(["a", "b", "c", "d", "e", "Other"]);
    expect(drawn.Other).toEqual([5 + 4 + 3, 5 + 4 + 3]);
  });

  it("keeps a day no word was counted on as no record, not a zero", () => {
    const series = Object.fromEntries(["a", "b", "c", "d", "e", "f", "g"].map((k) => [k, [null, 1]]));
    expect(stackKeys(series).series.Other).toEqual([null, 2]);
  });

  it("keeps the given order and names every colour with its total", () => {
    render(<StackedBars series={{ pending: [1, 0], relevant: [5, 4] }} order={["relevant", "pending"]} names={{ relevant: "Kept" }} start="2031-01-27" />);
    const legend = screen.getByText("Kept").closest("ul")!;
    expect(within(legend).getAllByRole("listitem").map((li) => li.textContent)).toEqual(["Kept9", "pending1"]);
  });
});

describe("the panel", () => {
  it("says why it is empty instead of drawing a flat zero", () => {
    render(
      <ChartPanel title="Views" source="usage_daily" empty="Not counted yet." table={{ columns: ["Day"], rows: [] }}>
        <p>chart</p>
      </ChartPanel>,
    );
    expect(screen.getByText("Not counted yet.")).toBeInTheDocument();
    expect(screen.queryByText("chart")).not.toBeInTheDocument();
    // Nothing to tabulate either.
    expect(screen.queryByRole("button", { name: "Table" })).not.toBeInTheDocument();
  });

  it("turns into its table, and keeps where the numbers come from", async () => {
    render(
      <ChartPanel title="Views" source="usage_daily · counting since 28 Jan" table={{ columns: ["Day", "Views"], rows: [["27 Jan", null], ["28 Jan", 4]] }}>
        <p>chart</p>
      </ChartPanel>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Where Views is counted" }));
    expect(screen.getByText("Counted in:")).toBeInTheDocument();
    expect(screen.getByText("usage_daily · counting since 28 Jan")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Table" }));
    expect(screen.queryByText("chart")).not.toBeInTheDocument();
    expect(screen.getByRole("row", { name: /27 Jan/ })).toHaveTextContent("—");
    expect(screen.getByRole("row", { name: /28 Jan/ })).toHaveTextContent("4");
  });
});

describe("the headline tile", () => {
  it("prints an uncounted measure as a dash and says so", () => {
    render(<KpiTile label="Visitor-days" current={null} previous={null} source="usage_daily" />);
    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.getByText("Not counted yet")).toBeInTheDocument();
  });

  it("says how it moved in words", () => {
    render(<KpiTile label="New accounts" current={7} previous={4} source="users" />);
    expect(screen.getByText("+3 from 4")).toBeInTheDocument();
    expect(screen.getByText("+3 from 4").parentElement).toHaveTextContent(/^up\+3 from 4$/);
  });

  it("claims no change only against a period that was counted", async () => {
    // Nothing before to compare with is not "no change" (the design's KpiTile bug).
    const { rerender } = render(<KpiTile label="MRR" current={2086} previous={null} source="subscriptions" />);
    expect(screen.queryByText(/no change/)).not.toBeInTheDocument();
    expect(screen.getByText("Earlier period not counted yet")).toBeInTheDocument();
    rerender(<KpiTile label="Visitor-days" current={1284} previous={null} source="usage_daily" countedSince="2031-01-12" />);
    expect(screen.getByText("Earlier period not counted yet")).toBeInTheDocument();
    expect(screen.queryByText(/no change/)).not.toBeInTheDocument();
    // When counting began is behind the ⓘ, with the source.
    await userEvent.click(screen.getByRole("button", { name: "Where Visitor-days is counted" }));
    expect(screen.getByText(/Counting began 12 Jan/)).toBeInTheDocument();
    rerender(<KpiTile label="Visitor-days" current={40} previous={40} source="usage_daily" countedSince="2031-01-12" />);
    expect(screen.getByText("±0%").parentElement).toHaveTextContent(/^no change±0%$/);
    expect(screen.queryByText("Earlier period not counted yet")).not.toBeInTheDocument();
  });

  it("breaks the sparkline where there is no record rather than dipping to zero", () => {
    const { container } = render(<Sparkline values={[1, 2, null, 3, 4]} />);
    const d = container.querySelector("path")!.getAttribute("d")!;
    expect(d.match(/M/g)).toHaveLength(2);
  });
});

describe("the cohort grid", () => {
  it("shades by share but prints the count, and leaves an unfinished week blank", () => {
    render(<CohortGrid rows={[{ week: "2031-01-06", accounts: 4, by_week: [3, 1, null] }]} />);
    const row = screen.getByRole("row", { name: /6 Jan/ });
    expect(row).toHaveTextContent("4");
    expect(within(row).getByTitle("Week 1 after: 3 of 4 came back")).toHaveTextContent("3");
    expect(within(row).getByLabelText("Week 3 after: no record yet")).toHaveTextContent("");
  });

  it("steps the shade by the share of the cohort", () => {
    expect(step(0, 4)).toBe(0);
    expect(step(1, 100)).toBe(1);
    expect(step(4, 4)).toBe(5);
    expect(step(3, 0)).toBe(0);
  });
});

describe("lists and the way to paying", () => {
  it("gives shares only once there are thirty to share", () => {
    const { rerender } = render(<BarList rows={[{ label: "story", current: 3 }, { label: "feed", current: 1 }]} />);
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
    rerender(<BarList rows={[{ label: "story", current: 30 }, { label: "feed", current: 10 }]} />);
    expect(screen.getByText(/75%/)).toBeInTheDocument();
  });

  it("counts how many went on from each step", () => {
    render(<Funnel steps={[{ label: "Saw the prompt", current: 2 }, { label: "Paid", current: 1 }]} />);
    expect(screen.getByText("1 of 2 went on")).toBeInTheDocument();
  });

  it("puts each outlet at its median and says how often it was first", () => {
    render(<DotPlot rows={[{ outlet: "The Hindu", stories: 3, first: 2, median_hours: 1.5 }]} />);
    expect(screen.getByText("1.5 h · first 2 of 3")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "The Hindu: 1.5 h behind the first, on 3 stories" })).toBeInTheDocument();
  });
});
