import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { BranchTree } from "@/components/BranchTree";
import type { BranchNode, BranchTreeData, StoryDevelopment } from "@/lib/api";

function dev(id: string, title: string, occurred_at: string | null = "2026-07-20"): StoryDevelopment {
  return { id, title, sector: null, occurred_at, image_url: null, is_current: false, why: null };
}
function node(id: string, parent_id: string | null, depth: number, off_spine = false): BranchNode {
  return { id, parent_id, off_spine, depth };
}
function tree(nodes: BranchNode[], shape?: Partial<BranchTreeData["shape"]>): BranchTreeData {
  return {
    root_id: nodes[0].id,
    nodes,
    shape: {
      developments: nodes.length,
      branches: 0,
      satellites: nodes.filter((n) => n.off_spine).length,
      max_depth: Math.max(...nodes.map((n) => n.depth)),
      ...shape,
    },
  };
}

const rowText = () =>
  screen
    .getByLabelText("Storyline structure")
    .innerText?.split("\n")
    .filter(Boolean) ?? [];

describe("BranchTree — TRUNK is the flat timeline", () => {
  // The design's central call: a reader who doesn't care about structure must
  // see exactly the old flat page plus one counted line. Most storylines here
  // are 2-4 developments deep, so this is the common case, not the edge.
  it("shows a shallow storyline as a plain list with no branch rows", () => {
    render(
      <BranchTree
        tree={tree([node("a", null, 0), node("b", "a", 1)])}
        developments={[dev("a", "Root development"), dev("b", "Second development")]}
      />,
    );
    expect(screen.getByText("Root development")).toBeInTheDocument();
    expect(screen.getByText("Second development")).toBeInTheDocument();
    expect(screen.queryByText(/developments$/)).not.toBeInTheDocument(); // no "↳ N developments"
  });

  it("marks the root and prints the counted shape verbatim", () => {
    render(
      <BranchTree
        tree={tree([node("a", null, 0), node("b", "a", 1)], {
          developments: 14,
          branches: 3,
          satellites: 1,
          max_depth: 2,
        })}
        developments={[dev("a", "Root development"), dev("b", "Second")]}
      />,
    );
    // Counted, never summarised — these are the partitioner's numbers.
    expect(screen.getByText(/14 DEVELOPMENTS · 3 BRANCHES · 1 SATELLITE · DEPTH 2/)).toBeInTheDocument();
    expect(screen.getByText(/ROOT/)).toBeInTheDocument();
  });

  it("follows the LONGEST on-spine chain, not the first child", () => {
    // a → b (dead end) and a → c → d. The spine must take c/d.
    render(
      <BranchTree
        tree={tree([node("a", null, 0), node("b", "a", 1), node("c", "a", 1), node("d", "c", 2)])}
        developments={[dev("a", "Root"), dev("b", "Short branch"), dev("c", "Long one"), dev("d", "Long two")]}
      />,
    );
    expect(screen.getByText("Long one")).toBeInTheDocument();
    expect(screen.getByText("Long two")).toBeInTheDocument();
    // The dead end is collapsed into the branch row instead.
    expect(screen.queryByText("Short branch")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^1 development,/ })).toBeInTheDocument();
  });
});

describe("BranchTree — branches collapse in place", () => {
  const t = tree([node("a", null, 0), node("b", "a", 1), node("c", "a", 1), node("d", "a", 1)]);
  const devs = [
    dev("a", "Root development"),
    dev("b", "Off-spine one", "2026-07-11"),
    dev("c", "Off-spine two", "2026-07-23"),
    dev("d", "Spine second", "2026-07-12"),
  ];

  it("collapses the siblings the spine did not take, with their date span", async () => {
    render(<BranchTree tree={t} developments={devs} />);
    const row = screen.getByRole("button", { name: /developments/ });
    expect(row).toHaveTextContent("↳");
    // Three leaf children: the spine takes the EARLIEST (11 JUL), the other two
    // collapse. Same month reads "12–23 JUL", not "12 JUL – 23 JUL".
    expect(row).toHaveTextContent(/12–23 JUL/);
    expect(screen.getByText("Off-spine one")).toBeInTheDocument(); // promoted to the spine
    expect(screen.queryByText("Off-spine two")).not.toBeInTheDocument(); // collapsed
  });

  it("expands the branch in place and flips the chevron", async () => {
    render(<BranchTree tree={t} developments={devs} />);
    await userEvent.click(screen.getByRole("button", { name: /developments/ }));
    expect(screen.getByText("Off-spine two")).toBeInTheDocument();
    expect(screen.getByText("Spine second")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /developments/ })).toHaveTextContent("▾");
  });

  it("collapses again on a second tap", async () => {
    render(<BranchTree tree={t} developments={devs} />);
    const row = () => screen.getByRole("button", { name: /developments/ });
    await userEvent.click(row());
    expect(screen.getByText("Off-spine two")).toBeInTheDocument();
    await userEvent.click(row());
    expect(screen.queryByText("Off-spine two")).not.toBeInTheDocument();
  });
});

describe("BranchTree — satellites are a deliberate detour", () => {
  const t = tree([node("a", null, 0), node("b", "a", 1), node("s", "a", 1, true)]);
  const devs = [dev("a", "Root"), dev("b", "On spine"), dev("s", "Loosely attached")];

  it("hides satellites in TRUNK", () => {
    render(<BranchTree tree={t} developments={devs} />);
    expect(screen.queryByText("Loosely attached")).not.toBeInTheDocument();
    expect(screen.getByText(/TRUNK · \d+ ON THE SPINE/)).toBeInTheDocument();
  });

  it("adds them in ALL, tagged so the reader is told they are loose", async () => {
    render(<BranchTree tree={t} developments={devs} />);
    await userEvent.click(screen.getByRole("button", { name: "ALL" }));
    expect(screen.getByText("Loosely attached")).toBeInTheDocument();
    // The shape readout also says "1 SATELLITE" — assert the ROW's own tag.
    expect(screen.getByText(/^\d{2} [A-Z]{3} · SATELLITE$/)).toBeInTheDocument();
    expect(screen.getByText(/ALL · \d+ SHOWN/)).toBeInTheDocument();
  });

  it("keeps the pressed state on the active view", async () => {
    render(<BranchTree tree={t} developments={devs} />);
    expect(screen.getByRole("button", { name: "TRUNK" })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByRole("button", { name: "ALL" }));
    expect(screen.getByRole("button", { name: "ALL" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "TRUNK" })).toHaveAttribute("aria-pressed", "false");
  });
});

describe("BranchTree — degenerate real-world data", () => {
  // The live corpus has a storyline with 19 children on the root and five
  // parentless orphans. Nothing may be silently dropped: the flat timeline was
  // already listing every one of them.
  it("surfaces orphans the frozen member set cut loose", async () => {
    const t = tree([node("a", null, 0), node("b", "a", 1), node("orphan", null, 0)]);
    render(
      <BranchTree
        tree={t}
        developments={[dev("a", "Root"), dev("b", "Child"), dev("orphan", "Re-attached orphan")]}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /^1 development,/ }));
    expect(screen.getByText("Re-attached orphan")).toBeInTheDocument();
  });

  it("renders a single-development storyline without a branch row", () => {
    render(<BranchTree tree={tree([node("a", null, 0)])} developments={[dev("a", "The only one")]} />);
    expect(screen.getByText("The only one")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /developments/ })).not.toBeInTheDocument();
  });

  it("survives a node with no matching development rather than crashing", () => {
    render(
      <BranchTree tree={tree([node("a", null, 0), node("ghost", "a", 1)])} developments={[dev("a", "Root")]} />,
    );
    expect(screen.getByText("Root")).toBeInTheDocument();
  });

  it("does not hang on a parent/child cycle in the stored tree", () => {
    // A REAL cycle: a's parent is b and b's parent is a. branch_parent_id is
    // written per partition run and never validated, so nothing guarantees the
    // stored edges are acyclic — without the seen-set this recurses until the
    // stack blows and takes the whole page with it.
    render(
      <BranchTree
        tree={tree([node("a", "b", 0), node("b", "a", 1)])}
        developments={[dev("a", "Root"), dev("b", "Child")]}
      />,
    );
    expect(screen.getByText("Root")).toBeInTheDocument();
    expect(screen.getByText("Child")).toBeInTheDocument();
  });
});

describe("BranchTree — every development is reachable", () => {
  // The story page is the only place a reader can move between developments:
  // the event page dropped its timeline in 0.0.81.1, so nothing else links a
  // story's members together. This tree listed them as plain <div>s, which made
  // /trending/[slug] a dead end — titles that look tappable and aren't.
  it("links each spine development to its own page", () => {
    render(
      <BranchTree
        tree={tree([node("a", null, 0), node("b", "a", 1)])}
        developments={[dev("a", "Root"), dev("b", "Second")]}
      />,
    );
    expect(screen.getByRole("link", { name: /Root/ })).toHaveAttribute("href", "/story/a");
    expect(screen.getByRole("link", { name: /Second/ })).toHaveAttribute("href", "/story/b");
  });

  it("links developments revealed by expanding a branch", async () => {
    // Three leaf children: the spine takes the earliest, the other two collapse
    // behind the toggle. Collapsed developments are the ones most at risk of
    // being unreachable, since nothing else in the app links to them.
    render(
      <BranchTree
        tree={tree([node("a", null, 0), node("b", "a", 1), node("c", "a", 1), node("d", "a", 1)])}
        developments={[
          dev("a", "Root"),
          dev("b", "Spine took me", "2026-07-11"),
          dev("c", "Collapsed one", "2026-07-23"),
          dev("d", "Collapsed two", "2026-07-12"),
        ]}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /developments/ }));

    expect(screen.getByRole("link", { name: /Collapsed one/ })).toHaveAttribute("href", "/story/c");
    expect(screen.getByRole("link", { name: /Collapsed two/ })).toHaveAttribute("href", "/story/d");
  });

  it("leaves the development you are already on inert", () => {
    render(
      <BranchTree
        tree={tree([node("a", null, 0), node("b", "a", 1)])}
        developments={[dev("a", "Root"), dev("b", "Second")]}
        currentId="b"
      />,
    );
    // Root still navigates; "you are here" is not a link to itself.
    expect(screen.getByRole("link", { name: /Root/ })).toHaveAttribute("href", "/story/a");
    expect(screen.queryByRole("link", { name: /Second/ })).not.toBeInTheDocument();
    expect(screen.getByText("Second")).toBeInTheDocument();
  });

  it("keeps the branch toggle a button, not a link", async () => {
    render(
      <BranchTree
        tree={tree([node("a", null, 0), node("b", "a", 1), node("c", "a", 1), node("d", "a", 1)])}
        developments={[
          dev("a", "Root"),
          dev("b", "Spine took me", "2026-07-11"),
          dev("c", "Collapsed one", "2026-07-23"),
          dev("d", "Collapsed two", "2026-07-12"),
        ]}
      />,
    );
    const toggle = screen.getByRole("button", { name: /developments/ });
    expect(toggle).not.toHaveAttribute("href");
    // Still toggles — swapping the tag must not break the expand.
    await userEvent.click(toggle);
    expect(screen.getByText("Collapsed one")).toBeInTheDocument();
  });
});
