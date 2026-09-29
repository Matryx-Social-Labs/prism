import { describe, expect, it } from "vitest";
import { entityHref } from "@/lib/entities";
import { STATE_HUBS, regionLabel, stateByCode, stateBySlug, stateSlug } from "@/lib/regions";

// The state hubs (audit 02, P1-1) are addressed by slug, never by the ISO code,
// and the code is what the API filters on: the two must round-trip for all 33.
describe("state hub slugs", () => {
  it("round-trips every hub between its slug and its ISO code", () => {
    expect(STATE_HUBS).toHaveLength(33);
    for (const hub of STATE_HUBS) {
      expect(stateBySlug(hub.slug)?.code).toBe(hub.code);
      expect(stateByCode(hub.code)?.slug).toBe(hub.slug);
    }
    expect(new Set(STATE_HUBS.map((h) => h.slug)).size).toBe(33);
  });

  it("spells an ampersand and spaces the way the entity folder does", () => {
    expect(stateSlug("Jammu & Kashmir")).toBe("jammu-and-kashmir");
    expect(stateSlug("Andhra Pradesh")).toBe("andhra-pradesh");
    expect(stateByCode("IN-JK")?.slug).toBe("jammu-and-kashmir");
  });

  it("uses the API's code for Uttarakhand (IN-UK), so its records find their hub and their label", () => {
    expect(stateByCode("IN-UK")?.slug).toBe("uttarakhand");
    expect(regionLabel(["IN", "IN-UK"])).toBe("Uttarakhand");
  });

  it("names union territories as such, and lists the hubs by name, not by volume", () => {
    expect(stateBySlug("delhi")?.kind).toBe("Union territory");
    expect(stateBySlug("karnataka")?.kind).toBe("State");
    const names = STATE_HUBS.map((h) => h.name);
    expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b)));
  });

  it("knows no hub for an unknown slug or code", () => {
    expect(stateBySlug("bengaluru")).toBeNull();
    expect(stateByCode("IN-BLR")).toBeNull();
  });
});

// /entity/karnataka and /state/karnataka competed for "Karnataka news": a
// state's own name links straight to its hub, every other actor to its page.
describe("entityHref", () => {
  it("sends a state's own name to its hub and anyone else to their page", () => {
    expect(entityHref("karnataka")).toBe("/state/karnataka");
    expect(entityHref("jammu-and-kashmir")).toBe("/state/jammu-and-kashmir");
    expect(entityHref("dk-shivakumar")).toBe("/entity/dk-shivakumar");
    expect(entityHref("new-delhi")).toBe("/entity/new-delhi");
  });
});
