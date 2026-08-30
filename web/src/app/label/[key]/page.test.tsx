import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import LabelPage from "@/app/label/[key]/page";
import type { LabelTask } from "@/lib/api";

// The gold set this page produces is what every story-layer decision is measured
// against, so the failures worth pinning are the ones that still LOOK like a
// working page: an answer that never reaches the server, a selection that submits
// the wrong ids, or a judgement filed under the wrong kind.

const fetchLabelBatch = vi.hoisted(() => vi.fn());
const fetchLabelTask = vi.hoisted(() => vi.fn());
const postLabelAnswer = vi.hoisted(() => vi.fn());
const joinLabelBatch = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", () => ({
  fetchLabelBatch,
  fetchLabelTask,
  postLabelAnswer,
  joinLabelBatch,
}));

function task(over: Partial<LabelTask> = {}): LabelTask {
  return {
    id: "task-1",
    position: 0,
    sector: "sports",
    seed: {
      id: "seed-1",
      title: "Babar returns to captaincy and fails",
      at: "2026-08-14T05:30:00+00:00",
      source_count: 4,
      actors: ["Babar Azam"],
      signals: [],
    },
    candidates: [
      {
        id: "cand-1",
        title: "Shan Masood hits century after standing down",
        at: "2026-08-14T09:00:00+00:00",
        source_count: 3,
        actors: ["Shan Masood"],
        signals: ["actors", "embedding"],
      },
      {
        id: "cand-2",
        title: "Unrelated hockey result",
        at: "2026-08-15T09:00:00+00:00",
        source_count: 1,
        actors: [],
        signals: ["embedding"],
      },
    ],
    ...over,
  };
}

// jsdom does NOT route localStorage through Storage.prototype, so spying on the
// prototype silently never fires (recorded in CLAUDE.md). Stub the global.
function stubStorage(initial: Record<string, string> = {}) {
  const store = new Map(Object.entries(initial));
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
    removeItem: (k: string) => void store.delete(k),
    clear: () => store.clear(),
  });
  return store;
}

const params = Promise.resolve({ key: "batch-key" });

beforeEach(() => {
  fetchLabelBatch.mockResolvedValue({
    name: "Story boundaries",
    notes: null,
    open: true,
    self_join: true,
    labeller: "ana",
    total: 10,
    done: 3,
  });
  fetchLabelTask.mockResolvedValue({ task: task(), closed: false });
  postLabelAnswer.mockResolvedValue(undefined);
  joinLabelBatch.mockResolvedValue("tok-abc");
});

afterEach(() => {
  vi.unstubAllGlobals(); // restoreAllMocks does NOT undo a stubbed global
  vi.clearAllMocks();
});

describe("label page", () => {
  it("asks who you are before serving any task", async () => {
    stubStorage();
    render(<LabelPage params={params} />);
    expect(await screen.findByLabelText("Your first name")).toBeInTheDocument();
    expect(fetchLabelTask).not.toHaveBeenCalled();
  });

  it("remembers a returning labeller and resumes their queue", async () => {
    stubStorage({ "prism.label.token.batch-key": "tok-abc", "prism.labeller": "ana" });
    render(<LabelPage params={params} />);
    await waitFor(() => expect(fetchLabelTask).toHaveBeenCalledWith("batch-key", "tok-abc"));
    expect(await screen.findByText(/Babar returns to captaincy/)).toBeInTheDocument();
  });

  it("submits exactly the events the labeller picked", async () => {
    stubStorage({ "prism.label.token.batch-key": "tok-abc", "prism.labeller": "ana" });
    render(<LabelPage params={params} />);
    const pick = await screen.findByRole("button", { name: /Shan Masood/ });
    await userEvent.click(pick);
    await userEvent.click(screen.getByRole("button", { name: /1 selected/ }));
    await waitFor(() => expect(postLabelAnswer).toHaveBeenCalled());
    const body = postLabelAnswer.mock.calls[0][1];
    expect(body.selected).toEqual(["cand-1"]);
    expect(body.unsure).toBe(false);
    expect(body.token).toBe("tok-abc");
  });

  it("records an empty selection as a real answer, not a skip", async () => {
    // "None of these" is a valuable negative. Treating it as unanswered would
    // serve the same task forever and put nothing in the gold set.
    stubStorage({ "prism.label.token.batch-key": "tok-abc", "prism.labeller": "ana" });
    render(<LabelPage params={params} />);
    await userEvent.click(await screen.findByRole("button", { name: "None of these" }));
    await waitFor(() => expect(postLabelAnswer).toHaveBeenCalled());
    const body = postLabelAnswer.mock.calls[0][1];
    expect(body.selected).toEqual([]);
    expect(body.unsure).toBe(false);
  });

  it("keeps 'not sure' distinct from 'none of these'", async () => {
    // Collapsing them would file coin-flips as confident negatives, which is what
    // the gold set's AMBIGUOUS list exists to prevent.
    stubStorage({ "prism.label.token.batch-key": "tok-abc", "prism.labeller": "ana" });
    render(<LabelPage params={params} />);
    await userEvent.click(await screen.findByRole("button", { name: "Not sure" }));
    await waitFor(() => expect(postLabelAnswer).toHaveBeenCalled());
    expect(postLabelAnswer.mock.calls[0][1].unsure).toBe(true);
  });

  it("toggles with number keys so a long session stays on the keyboard", async () => {
    stubStorage({ "prism.label.token.batch-key": "tok-abc", "prism.labeller": "ana" });
    render(<LabelPage params={params} />);
    await screen.findByText(/Babar returns to captaincy/);
    await userEvent.keyboard("2");
    expect(await screen.findByRole("button", { name: /1 selected/ })).toBeInTheDocument();
    await userEvent.keyboard("{Enter}");
    await waitFor(() => expect(postLabelAnswer).toHaveBeenCalled());
    expect(postLabelAnswer.mock.calls[0][1].selected).toEqual(["cand-2"]);
  });

  it("marks selection with aria-pressed, not colour alone", async () => {
    // DESIGN.md: chrome is monochrome, colour only ever means a lens is speaking.
    // Selection is a rule and ink weight — which also means the state must be
    // exposed to assistive tech, since there is no colour cue to perceive.
    stubStorage({ "prism.label.token.batch-key": "tok-abc", "prism.labeller": "ana" });
    render(<LabelPage params={params} />);
    const row = await screen.findByRole("button", { name: /Shan Masood/ });
    expect(row).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(row);
    await waitFor(() => expect(row).toHaveAttribute("aria-pressed", "true"));
  });

  it("says thank you rather than erroring when the queue is empty", async () => {
    stubStorage({ "prism.label.token.batch-key": "tok-abc", "prism.labeller": "ana" });
    fetchLabelTask.mockResolvedValue({ task: null, closed: false });
    render(<LabelPage params={params} />);
    expect(await screen.findByText(/That's everything/)).toBeInTheDocument();
  });

  it("tells the labeller when the batch is closed", async () => {
    stubStorage({ "prism.label.token.batch-key": "tok-abc", "prism.labeller": "ana" });
    fetchLabelTask.mockResolvedValue({ task: null, closed: true });
    render(<LabelPage params={params} />);
    expect(await screen.findByText(/batch is closed/)).toBeInTheDocument();
  });

  it("mints a credential on first visit and stores it per batch", async () => {
    // One shared link, a distinct identity per person. The name is a caption —
    // two labellers called Ana must not collapse into one opinion, which is what
    // the previous name-keyed design did silently.
    const store = stubStorage();
    render(<LabelPage params={params} />);
    await userEvent.type(await screen.findByLabelText("Your first name"), "Ana");
    await userEvent.click(screen.getByRole("button", { name: "Start" }));
    await waitFor(() => expect(joinLabelBatch).toHaveBeenCalledWith("batch-key", "Ana"));
    await waitFor(() => expect(store.get("prism.label.token.batch-key")).toBe("tok-abc"));
    expect(await screen.findByText(/Babar returns to captaincy/)).toBeInTheDocument();
  });

  it("never puts the credential in the URL", async () => {
    // A token in the address bar leaks through browser history, Referer headers
    // and any screenshot a labeller shares. The batch key is a join capability
    // only; the write credential lives in storage and the request body.
    stubStorage({ "prism.label.token.batch-key": "tok-abc" });
    render(<LabelPage params={params} />);
    await screen.findByText(/Babar returns to captaincy/);
    expect(window.location.href).not.toContain("tok-abc");
  });

  it("shows an error rather than a blank screen when joining fails", async () => {
    stubStorage();
    joinLabelBatch.mockRejectedValue(new Error("403"));
    render(<LabelPage params={params} />);
    await userEvent.type(await screen.findByLabelText("Your first name"), "Ana");
    await userEvent.click(screen.getByRole("button", { name: "Start" }));
    expect(await screen.findByText(/Something went wrong/)).toBeInTheDocument();
  });
});
