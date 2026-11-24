import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";

import PipelinePage from "@/app/admin/pipeline/page";
import { bound, duration, type Pipeline } from "@/lib/admin";

const fetchPipeline = vi.hoisted(() => vi.fn());
const ADMIN = vi.hoisted(() => ({ session: { token: "t", userId: "u", email: "f@example.test" }, email: "f@example.test" }));
vi.mock("@/components/admin/AdminShell", async (orig) => ({ ...(await orig<typeof import("@/components/admin/AdminShell")>()), useAdmin: () => ADMIN }));
vi.mock("@/lib/admin", async (orig) => ({ ...(await orig<typeof import("@/lib/admin")>()), fetchPipeline }));

const pipeline: Pipeline = {
  days: [
    {
      day: "2026-11-25",
      recorded: true,
      timings: [
        { name: "match_lock.held", n: 1234, p50_ms: 700, p95_ms: 1500 },
        { name: "analysis.queue_age", n: 40, p50_ms: 300_000, p95_ms: null },
        { name: "something.new", n: 3, p50_ms: 5, p95_ms: 10 },
      ],
      counters: [{ name: "dead.classified.items.rebill", n: 2 }],
    },
    { day: "2026-11-24", recorded: true, timings: [], counters: [] },
    { day: "2026-11-23", recorded: false, timings: [], counters: [] },
  ],
  sweeper: { due: 3, oldest_due_age_s: 12.4 },
  // API order: newest first.
  throughput: [
    { hour: "2026-11-25T09:00:00+00:00", observed: 120, classified: 118, enriched: 60, correlated: 59 },
    { hour: "2026-11-25T08:00:00+00:00", observed: 90, classified: 88, enriched: 40, correlated: 39 },
  ],
};

const region = async (name: string) => within(await screen.findByRole("region", { name }));

beforeEach(() => {
  fetchPipeline.mockReset().mockResolvedValue(pipeline);
});

describe("the pipeline page", () => {
  it("prints each timing as an upper bound under a plain-word name", async () => {
    render(<PipelinePage />);
    const day = within((await region("Timings by day")).getByRole("group", { name: "2026-11-25" }));
    const held = day.getByRole("row", { name: /Match lock — held/ });
    expect(held).toHaveTextContent("1,234");
    expect(held).toHaveTextContent("≤ 700 ms");
    expect(held).toHaveTextContent("≤ 1.5 s");
    expect(day.getByRole("row", { name: /something\.new/ })).toBeInTheDocument();
    expect(fetchPipeline).toHaveBeenCalledWith(ADMIN.session, 7);
  });

  it("says a percentile beyond the largest bucket is over 24 h", async () => {
    render(<PipelinePage />);
    const day = within((await region("Timings by day")).getByRole("group", { name: "2026-11-25" }));
    const queue = day.getByRole("row", { name: /Analysis queue — time past due/ });
    expect(queue).toHaveTextContent("≤ 5 min");
    expect(queue).toHaveTextContent("over 24 h");
  });

  it("says a day with nothing recorded was not recorded, never zero", async () => {
    render(<PipelinePage />);
    for (const name of ["Timings by day", "Counters by day"]) {
      const day = (await region(name)).getByRole("group", { name: "2026-11-23" });
      expect(day).toHaveTextContent("not recorded");
      expect(day).not.toHaveTextContent(/\b0\b/);
    }
  });

  it("lists counters by raw name, and none on a recorded day without any", async () => {
    render(<PipelinePage />);
    const counters = await region("Counters by day");
    expect(within(counters.getByRole("group", { name: "2026-11-25" })).getByRole("row", { name: /dead\.classified\.items\.rebill/ })).toHaveTextContent("2");
    expect(counters.getByRole("group", { name: "2026-11-24" })).toHaveTextContent("none");
  });

  it("shows the sweeper and the newest hour now", async () => {
    render(<PipelinePage />);
    const now = await region("Now");
    expect(now.getByRole("row", { name: /Sweeper/ })).toHaveTextContent("3 due · oldest 12.4 s");
    expect(now.getByRole("row", { name: /Newest hour/ })).toHaveTextContent("120");
  });

  it("says the sweeper is not available when the queue could not be read", async () => {
    fetchPipeline.mockResolvedValue({ ...pipeline, sweeper: null });
    render(<PipelinePage />);
    const sweeper = (await region("Now")).getByRole("row", { name: /Sweeper/ });
    expect(sweeper).toHaveTextContent("not available");
    expect(sweeper).not.toHaveTextContent(/\b0\b/);
  });

  it("says nothing is recorded yet instead of drawing empty tables", async () => {
    fetchPipeline.mockResolvedValue({ days: (pipeline.days ?? []).map((d) => ({ ...d, recorded: false, timings: [], counters: [] })), sweeper: null, throughput: [] });
    render(<PipelinePage />);
    expect(await screen.findByText("Nothing recorded yet")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Timings by day" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Articles per hour, last 24 hours" })).not.toBeInTheDocument();
  });

  it("says why when the API fails", async () => {
    fetchPipeline.mockRejectedValue(new Error("API 500"));
    render(<PipelinePage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("API 500");
  });

  it("says the timings are not available when the store could not be read, and still shows the hours", async () => {
    fetchPipeline.mockResolvedValue({ ...pipeline, days: null });
    render(<PipelinePage />);
    for (const name of ["Timings by day", "Counters by day"]) {
      const section = (await screen.findByRole("region", { name })) as HTMLElement;
      expect(section).toHaveTextContent("not available");
      expect(section).not.toHaveTextContent(/\b0\b|none|not recorded/);
    }
    expect(screen.queryByText("Nothing recorded yet")).not.toBeInTheDocument();
    expect((await region("Articles per hour, last 24 hours")).getAllByRole("row")).toHaveLength(3);
  });

  it("says the hours are not available when the hourly query failed, and still shows the days", async () => {
    fetchPipeline.mockResolvedValue({ ...pipeline, throughput: null });
    render(<PipelinePage />);
    const hours = (await screen.findByRole("region", { name: "Articles per hour, last 24 hours" })) as HTMLElement;
    expect(hours).toHaveTextContent("not available");
    expect(hours).not.toHaveTextContent(/\b0\b|No hours/);
    expect((await region("Now")).getByRole("row", { name: /Newest hour/ })).toHaveTextContent("not available");
    expect((await region("Timings by day")).getByRole("row", { name: /Match lock — held/ })).toBeInTheDocument();
    expect(screen.queryByText("Nothing recorded yet")).not.toBeInTheDocument();
  });

  it("lists the last 24 hours, newest first", async () => {
    render(<PipelinePage />);
    const rows = (await region("Articles per hour, last 24 hours")).getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent("120");
    expect(rows[0]).toHaveTextContent("59");
    expect(rows[1]).toHaveTextContent("90");
  });
});

describe("duration and bound", () => {
  it("picks ms, s, min or h and drops a trailing .0", () => {
    expect(duration(700)).toBe("700 ms");
    expect(duration(1500)).toBe("1.5 s");
    expect(duration(2000)).toBe("2 s");
    expect(duration(300_000)).toBe("5 min");
    expect(duration(7_200_000)).toBe("2 h");
    expect(bound(700)).toBe("≤ 700 ms");
    expect(bound(null)).toBe("over 24 h");
  });
});
