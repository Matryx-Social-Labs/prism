import { describe, expect, it } from "vitest";
import { routeShape } from "@/lib/route";

const dev = (id: string, day: number, title = id) => ({ id, title, sector: null, occurred_at: new Date(Date.UTC(2026, 7, 27 + day)).toISOString(), image_url: null, is_current: false, why: null, source_count: 3 });
const node = (id: string, parent_id: string | null, off_spine = false) => ({ id, parent_id, off_spine, depth: 0 });
const tree = (nodes: ReturnType<typeof node>[]) => ({ root_id: "r", nodes, shape: { developments: nodes.length, branches: 0, satellites: 0, max_depth: 0 } });

describe("routeShape — the map's reading of the branch tree", () => {
  it("draws the longest on-spine chain as the main line, a short side chain as a branch, a long one as a branch line, and off-spine as satellites", () => {
    const devs = [dev("r", 0), dev("a", 1), dev("b", 3), dev("c", 5), dev("x1", 1), dev("x2", 2), dev("y1", 5), dev("y2", 7), dev("y3", 9), dev("s", 2)];
    const t = tree([node("r", null), node("a", "r"), node("b", "a"), node("c", "b"), node("x1", "a"), node("x2", "x1"), node("y1", "c"), node("y2", "y1"), node("y3", "y2"), node("s", "r", true)]);
    const shape = routeShape(t, devs);
    // r → a → b → c → y1 → y2 → y3 is the longest chain: the branch line under c is the trunk's tail.
    expect(shape.trunk.map((s) => s.id)).toEqual(["r", "a", "b", "c", "y1", "y2", "y3"]);
    expect(shape.lines.map((l) => [l.kind, l.from, l.stations.map((s) => s.id)])).toEqual([["branch", "a", ["x1", "x2"]]]);
    expect(shape.satellites.map((s) => s.id)).toEqual(["s"]);
    expect(shape.days).toBe(10);
  });

  it("calls a side chain of three or more a branch line, not a branch", () => {
    const devs = [dev("r", 0), dev("a", 1), dev("b", 2), dev("c", 3), dev("d", 4), dev("p", 1), dev("q", 2), dev("t", 3)];
    // trunk r a b c d (5); side chain p q t (3) off r
    const t = tree([node("r", null), node("a", "r"), node("b", "a"), node("c", "b"), node("d", "c"), node("p", "r"), node("q", "p"), node("t", "q")]);
    const shape = routeShape(t, devs);
    expect(shape.trunk.map((s) => s.id)).toEqual(["r", "a", "b", "c", "d"]);
    expect(shape.lines[0].kind).toBe("line");
    expect(shape.lines[0].stations.map((s) => s.id)).toEqual(["p", "q", "t"]);
  });

  it("orders siblings earliest first so the same story draws the same map every time", () => {
    const devs = [dev("r", 0), dev("late", 5), dev("early", 1)];
    const t = tree([node("r", null), node("late", "r"), node("early", "r")]);
    expect(routeShape(t, devs).trunk.map((s) => s.id)).toEqual(["r", "early"]);
    expect(routeShape(t, devs).lines[0].stations[0].id).toBe("late");
  });

  it("survives a cycle and an empty tree", () => {
    const devs = [dev("r", 0), dev("a", 1)];
    expect(routeShape(tree([node("r", null), node("a", "r"), node("r", "a")]), devs).trunk.map((s) => s.id)).toEqual(["r", "a"]);
    expect(routeShape(tree([]), devs).trunk).toEqual([]);
  });
});

describe("routeShape — what the record actually holds", () => {
  const dev = (id: string, day: number) => ({ id, title: id, sector: null, occurred_at: new Date(Date.UTC(2026, 7, 27 + day)).toISOString(), image_url: null, is_current: false, why: null, source_count: 1 });
  const node = (id: string, parent_id: string | null, off_spine = false) => ({ id, parent_id, off_spine, depth: 0 });
  const tree = (nodes: ReturnType<typeof node>[]) => ({ root_id: "r", nodes, shape: { developments: nodes.length, branches: 0, satellites: 0, max_depth: 0 } });

  it("reads through a satellite to the nearest on-spine ancestor, so an on-spine node under a satellite is still drawn", () => {
    // r → s(off) → a(on) → b(on): a and b hang from the root, not from s.
    const devs = [dev("r", 0), dev("s", 1), dev("a", 2), dev("b", 3)];
    const shape = routeShape(tree([node("r", null), node("s", "r", true), node("a", "s"), node("b", "a")]), devs);
    expect(shape.trunk.map((s) => s.id)).toEqual(["r", "a", "b"]);
    expect(shape.satellites.map((s) => s.id)).toEqual(["s"]);
  });

  it("draws every development of a branch, not only its longest chain", () => {
    // r → a → b (trunk); x under r with two children y and z: all three are the branch.
    const devs = [dev("r", 0), dev("a", 1), dev("b", 2), dev("x", 1), dev("y", 2), dev("z", 3)];
    const shape = routeShape(tree([node("r", null), node("a", "r"), node("b", "a"), node("x", "r"), node("y", "x"), node("z", "x")]), devs);
    expect(shape.lines.map((l) => [l.kind, l.stations.map((s) => s.id)])).toEqual([["line", ["x", "y", "z"]]]);
  });

  it("puts a parentless member on a branch from the root, never on the trunk", () => {
    const devs = [dev("r", 0), dev("o", 1), dev("p", 2)];
    const shape = routeShape(tree([node("r", null), node("o", null), node("p", null, true)]), devs);
    expect(shape.trunk.map((s) => s.id)).toEqual(["r"]);
    expect(shape.lines).toEqual([expect.objectContaining({ from: "r", kind: "branch" })]);
    expect(shape.lines[0].stations.map((s) => s.id)).toEqual(["o"]);
    expect(shape.satellites.map((s) => s.id)).toEqual(["p"]);
  });
});
