import { describe, expect, it } from "vitest";
import { spineLength } from "@/lib/spine";

const node = (id: string, parent_id: string | null, off_spine = false) => ({ id, parent_id, off_spine, depth: 0 });
const tree = (nodes: ReturnType<typeof node>[]) => ({ root_id: "r", nodes, shape: { developments: nodes.length, branches: 0, satellites: 0, max_depth: 0 } });

describe("spineLength — the trunk, as BranchTree counts it", () => {
  it("is the longest on-spine chain from the root, not the number of developments", () => {
    // 25 developments hanging off the root as branches make a spine of one.
    const wide = tree([node("r", null), ...Array.from({ length: 24 }, (_, i) => node(`b${i}`, "r"))]);
    expect(spineLength(wide)).toBe(2); // root and one branch child: the longest chain is two long
    const flat = tree([node("r", null), ...Array.from({ length: 24 }, (_, i) => node(`s${i}`, "r", true))]);
    expect(spineLength(flat)).toBe(1); // satellites are off the spine
    const long = tree([node("r", null), node("a", "r"), node("b", "a"), node("c", "b"), node("x", "r")]);
    expect(spineLength(long)).toBe(4);
  });

  it("is 0 for no tree and survives a cycle", () => {
    expect(spineLength(null)).toBe(0);
    expect(spineLength(tree([node("r", null), node("a", "r"), node("r", "a")]))).toBe(2);
  });
});
