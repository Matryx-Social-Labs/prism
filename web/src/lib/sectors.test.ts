import { describe, expect, it } from "vitest";
import { SECTOR_GROUPS, sectorCode, sectorGroup, sectorParam } from "./sectors";

describe("the six sectors", () => {
  it("are six, and none of them is 'other'", () => {
    expect(SECTOR_GROUPS).toHaveLength(6);
    expect(SECTOR_GROUPS.flatMap((g) => g.sectors)).not.toContain("other");
  });

  it("cover every pipeline sector except 'other' exactly once", () => {
    const all = SECTOR_GROUPS.flatMap((g) => g.sectors).sort();
    expect(all).toEqual(
      ["business", "cybersecurity", "entertainment", "finance", "health", "politics", "science", "sports", "technology"],
    );
  });

  it("keeps old sector URLs working by mapping a pipeline slug to its group", () => {
    expect(sectorGroup("finance")?.slug).toBe("business");
    expect(sectorGroup("cybersecurity")?.slug).toBe("tech");
    expect(sectorGroup("science")?.slug).toBe("health");
    expect(sectorGroup("politics")?.slug).toBe("politics");
  });

  it("returns null for 'other' and for junk, so nothing is printed for them", () => {
    expect(sectorGroup("other")).toBeNull();
    expect(sectorGroup("nope")).toBeNull();
    expect(sectorCode("other")).toBe("");
    expect(sectorCode(null)).toBe("");
  });

  it("builds the comma-separated ?sector= the API expects", () => {
    expect(sectorParam(sectorGroup("business")!)).toBe("business,finance");
    expect(sectorParam(sectorGroup("sports")!)).toBe("sports");
  });

  it("prints the group's code for any of its pipeline sectors", () => {
    expect(sectorCode("finance")).toBe("BIZ");
    expect(sectorCode("cybersecurity")).toBe("TEC");
  });
});
