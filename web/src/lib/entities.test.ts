import { describe, expect, it } from "vitest";
import { entityKind, markBlocks, markEntities } from "@/lib/entities";

const E = (name: string, entity_type = "government") => ({ name, entity_type, role: "affected" });

describe("markEntities — the record's named entities, marked for reading", () => {
  it("marks the first mention only, whole words, longest name first", () => {
    const segs = markEntities("India and the Indian Navy; India again. Indiana is not India.", [E("India"), E("Indian Navy", "organization")]);
    const marked = segs.filter((s) => s.entity).map((s) => s.text);
    // "Indian Navy" wins over "India" inside it; "India" is marked once; "Indiana" is untouched
    expect(marked).toEqual(["India", "Indian Navy"]);
    expect(segs.map((s) => s.text).join("")).toBe("India and the Indian Navy; India again. Indiana is not India.");
  });

  it("is case-sensitive for short names so US never marks us", () => {
    expect(markEntities("tell us what the US said", [E("US")]).filter((s) => s.entity).map((s) => s.text)).toEqual(["US"]);
    expect(markEntities("modi said", [E("Modi", "person")]).filter((s) => s.entity)).toHaveLength(1); // long names match case-insensitively
  });

  it("marks once per passage across blocks, and is pure — the same input marks the same words twice", () => {
    const blocks = ["India acted.", "India replied; China watched."];
    const first = markBlocks(blocks, [E("India"), E("China")]);
    expect(first[0].filter((s) => s.entity).map((s) => s.text)).toEqual(["India"]);
    expect(first[1].filter((s) => s.entity).map((s) => s.text)).toEqual(["China"]);
    // React's strict mode renders twice; a mark that vanishes on the second
    // render is a hydration mismatch (seen live on 2026-09-18).
    expect(markBlocks(blocks, [E("India"), E("China")])).toEqual(first);
  });

  it("returns the text untouched when nothing matches or there are no entities", () => {
    expect(markEntities("nothing here", [])).toEqual([{ text: "nothing here" }]);
    expect(markEntities("nothing here", [E("Kerala")])).toEqual([{ text: "nothing here" }]);
  });

  it("names the kind in the reader's words", () => {
    expect(entityKind(E("India", "government|subject"))).toBe("Government");
    expect(entityKind(E("X", "political_party"))).toBe("Political party");
    expect(entityKind(E("X", ""))).toBe("Named");
  });
});
