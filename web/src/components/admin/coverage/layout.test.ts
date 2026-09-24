import { describe, expect, it } from "vitest";

import { RIM, layout, type Point3 } from "./layout";

const dist = (p: Point3, q: Point3) => Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]);

describe("the coverage layout", () => {
  // Two islands: English outlets that share stories among themselves, Hindi
  // outlets likewise, and one thin bridge between them.
  const ids = ["en1", "en2", "en3", "hi1", "hi2", "hi3"];
  const links = [
    { a: "en1", b: "en2", shared: 40 },
    { a: "en2", b: "en3", shared: 30 },
    { a: "en1", b: "en3", shared: 35 },
    { a: "hi1", b: "hi2", shared: 25 },
    { a: "hi2", b: "hi3", shared: 20 },
    { a: "hi1", b: "hi3", shared: 22 },
    { a: "en1", b: "hi1", shared: 1 },
  ];

  it("draws outlets that share stories closer than outlets that do not", () => {
    const at = layout(ids, links);
    const within = dist(at.get("en2")!, at.get("en3")!);
    const across = dist(at.get("en2")!, at.get("hi2")!);
    expect(within).toBeLessThan(across / 2);
  });

  it("draws the same data the same way every time", () => {
    expect([...layout(ids, links).values()]).toEqual([...layout(ids, links).values()]);
  });

  it("never stacks two outlets on one point, linked or not", () => {
    const at = [...layout([...ids, "alone"], links).values()];
    for (let i = 0; i < at.length; i++) for (let j = i + 1; j < at.length; j++) expect(dist(at[i], at[j])).toBeGreaterThan(0.5);
  });

  it("keeps every outlet in view, a lone one beside a dense cluster included", () => {
    // Thirty outlets that all share stories, and one that shares none: the
    // push would leave the loner far outside the frame.
    const cluster = Array.from({ length: 30 }, (_, i) => `c${i}`);
    const dense = cluster.flatMap((a, i) => cluster.slice(i + 1).map((b) => ({ a, b, shared: 10 })));
    const at = layout([...cluster, "alone"], dense);
    // The camera looks at the origin and frames the rim.
    for (const p of at.values()) expect(Math.hypot(...p)).toBeLessThanOrEqual(RIM + 1e-9);
    expect(Math.hypot(...at.get("alone")!)).toBeGreaterThan(Math.hypot(...at.get("c0")!));
  });

  it("ignores a link to an outlet it was not given", () => {
    expect(() => layout(["a"], [{ a: "a", b: "gone", shared: 3 }])).not.toThrow();
  });
});
