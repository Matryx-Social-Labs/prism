import { describe, expect, it } from "vitest";
import { monitoredText } from "@/lib/coverage";

describe("monitoredText — the denominator on every count", () => {
  it("prints the count out of the monitored set", () => {
    expect(monitoredText(2, 27)).toBe("2 of 27 monitored outlets");
    expect(monitoredText(1, 27)).toBe("1 of 27 monitored outlets");
  });

  it("falls back to the bare count without a set size, or when the set is smaller than the count", () => {
    expect(monitoredText(1, null)).toBe("1 outlet");
    expect(monitoredText(3, undefined)).toBe("3 outlets");
    expect(monitoredText(5, 4)).toBe("5 outlets");
  });
});
