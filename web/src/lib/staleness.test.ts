import { describe, expect, it } from "vitest";
import { staleSince } from "@/lib/staleness";

const now = Date.parse("2026-09-17T10:00:00Z");
const row = (iso: string) => ({ latest_published_at: iso, last_updated_at: iso });

describe("staleSince — the chart says when it went quiet", () => {
  it("is null while the newest report is under twelve hours old", () => {
    expect(staleSince([row("2026-09-17T09:00:00Z"), row("2026-09-16T20:00:00Z")], now)).toBeNull();
  });
  it("names the newest report once nothing has arrived for twelve hours", () => {
    expect(staleSince([row("2026-09-16T21:00:00Z"), row("2026-09-16T20:00:00Z")], now)).toBe("2026-09-16T21:00:00.000Z");
  });
  it("is null with no rows", () => {
    expect(staleSince([], now)).toBeNull();
  });
});
