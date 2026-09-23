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
  // The primer gates the FIRST task, so every test that is about something else
  // must start past it — otherwise each one silently becomes a test of the
  // primer. The primer's own tests pass `primer: false` to opt back in.
  const { primer, ...rest } = initial as Record<string, string> & { primer?: boolean };
  const seeded: Record<string, string> =
    primer === false ? rest : { "prism.label.primer.batch-key": "1", ...rest };
  const store = new Map(Object.entries(seeded));
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

describe("an invited labeller's link", () => {
  // `tools/gold_candidates.py invite` hands out /label/<batch>#<token>. The
  // fragment carries the credential because browsers never send it to the server
  // — it stays out of access logs and Referer headers, unlike a path or query
  // segment. Until this was wired up the page ignored it entirely, so an invited
  // person fell through to the join form and self-joined as a STRANGER: their
  // answers were filed under a new anonymous identity while the named invite
  // minted for them sat unused. Nothing about that looks broken from either end.

  function withHash(hash: string) {
    window.location.hash = hash;
    window.history.replaceState(null, "", "/label/batch-key" + hash);
  }

  afterEach(() => {
    window.location.hash = "";
  });

  it("claims the credential from the fragment instead of asking who you are", async () => {
    const store = stubStorage();
    withHash("#invited-token");
    render(<LabelPage params={params} />);

    await waitFor(() => expect(fetchLabelTask).toHaveBeenCalled());
    expect(fetchLabelTask).toHaveBeenCalledWith("batch-key", "invited-token");
    expect(store.get("prism.label.token.batch-key")).toBe("invited-token");
    expect(screen.queryByLabelText("Your first name")).not.toBeInTheDocument();
  });

  it("clears the credential out of the address bar once claimed", async () => {
    stubStorage();
    withHash("#invited-token");
    render(<LabelPage params={params} />);

    await waitFor(() => expect(fetchLabelTask).toHaveBeenCalled());
    // A working session gets screenshotted and shared; the URL on screen must not
    // be enough for someone else to label as this person.
    expect(window.location.hash).toBe("");
  });

  it("greets the invited labeller by the name bound to their invite", async () => {
    stubStorage({ "prism.labeller": "someone else entirely" });
    withHash("#invited-token");
    fetchLabelBatch.mockResolvedValue({
      name: "Story boundaries",
      notes: null,
      open: true,
      self_join: false,
      labeller: "Priya",
      total: 10,
      done: 0,
    });
    // Driven to the finished state, which is the only screen that says the name
    // out loud — asserting on a screen that never renders it would pass for the
    // wrong reason.
    fetchLabelTask.mockResolvedValue({ task: null, closed: false });
    render(<LabelPage params={params} />);

    // The server knows whose credential this is; localStorage only knows what was
    // last typed on this device. Disagreeing would thank one person for another
    // person's judgements.
    expect(await screen.findByText(/Priya/)).toBeInTheDocument();
  });
});

describe("a claim task", () => {
  // The judgement the verbatim check cannot make: a sentence can be copied
  // exactly from the article and still be put in the wrong mouth. The quote
  // matches, the attribution is a lie, and nothing automatic can tell.

  const CLAIM = {
    article_id: "a1",
    title: "Minister announces road outlay",
    source: "The Hindu",
    speaker: "The minister",
    quote_text: "double its outlay on rural roads",
    context_before: "Speaking in Bengaluru, the minister said the state would ",
    context_after: " before the monsoon.",
    target: null,
    stance: "neutral",
  };

  function claimTask() {
    return { id: "task-c1", position: 0, kind: "claim_attribution" as const, claim: CLAIM };
  }

  it("shows the quote inside its surrounding sentences, not alone", async () => {
    stubStorage({ "prism.label.token.batch-key": "t", "prism.labeller": "ana" });
    fetchLabelTask.mockResolvedValue({ task: claimTask(), closed: false });
    render(<LabelPage params={params} />);

    // Attribution usually lives in the words either side ("said the minister").
    // Shown alone the question is unanswerable and the labeller would guess.
    expect(await screen.findByText(/Speaking in Bengaluru/)).toBeInTheDocument();
    expect(screen.getByText(CLAIM.quote_text)).toBeInTheDocument();
    expect(screen.getByText(/before the monsoon/)).toBeInTheDocument();
  });

  it("records a yes as a definite answer, not an empty one", async () => {
    stubStorage({ "prism.label.token.batch-key": "t", "prism.labeller": "ana" });
    fetchLabelTask.mockResolvedValue({ task: claimTask(), closed: false });
    render(<LabelPage params={params} />);

    await userEvent.click(await screen.findByRole("button", { name: /Yes —/ }));
    await waitFor(() => expect(postLabelAnswer).toHaveBeenCalled());
    const body = postLabelAnswer.mock.calls[0][1];
    // "Yes" and "No" must be distinguishable in the stored row. An empty
    // selection for both would make every claim read as unattributed.
    expect(body.selected).toEqual(["task-c1"]);
    expect(body.unsure).toBe(false);
    expect(body.skipped).toBe(false);
  });

  it("records a no as definite-but-empty, distinct from unsure and skip", async () => {
    stubStorage({ "prism.label.token.batch-key": "t", "prism.labeller": "ana" });
    fetchLabelTask.mockResolvedValue({ task: claimTask(), closed: false });
    render(<LabelPage params={params} />);

    await userEvent.click(await screen.findByRole("button", { name: /No —/ }));
    await waitFor(() => expect(postLabelAnswer).toHaveBeenCalled());
    const body = postLabelAnswer.mock.calls[0][1];
    expect(body.selected).toEqual([]);
    expect(body.unsure).toBe(false);
    expect(body.skipped).toBe(false);
  });

  it("explains the right-quote-wrong-mouth case before they start", async () => {
    stubStorage({ "prism.label.token.batch-key": "t", "prism.labeller": "ana" });
    fetchLabelTask.mockResolvedValue({ task: claimTask(), closed: false });
    render(<LabelPage params={params} />);

    // "Attribution" is abstract, and abstract lost last time — a careful person
    // grouped stories by shared organisation in good faith. Show the mistake.
    expect(await screen.findByText(/RIGHT QUOTE, WRONG MOUTH/)).toBeInTheDocument();
  });
});

describe("the claims guide actually reaches the labeller", () => {
  // The test above asserts the guide's TEXT is in the document. <details> keeps
  // its children in the DOM when collapsed, so that assertion passes whether or
  // not anyone can read them. This one checks the disclosure is actually OPEN.

  const CLAIM = {
    article_id: "a1",
    title: "Router vendor responds",
    source: "The Hacker News",
    speaker: "Zbtlink",
    quote_text: "This component has never been used for unauthorized access",
    context_before: "in a statement on its website. ",
    context_after: ", the company said.",
    target: "ENDLESSDOORS",
    stance: "defensive",
  };

  function taskAt(position: number) {
    return { id: `task-c${position}`, position, kind: "claim_attribution" as const, claim: CLAIM };
  }

  it("opens the guide on the first question", async () => {
    // An invited claims labeller never sees the landing screen where the story
    // flow shows its guide open — their token takes them straight to a task. So
    // if it is collapsed here, the tutorial was written and shown to nobody.
    stubStorage({ "prism.label.token.batch-key": "t", "prism.labeller": "ana" });
    fetchLabelTask.mockResolvedValue({ task: taskAt(0), closed: false });
    const { container } = render(<LabelPage params={params} />);

    await screen.findByText(/RIGHT QUOTE, WRONG MOUTH/);
    const details = container.querySelector("details");
    expect(details).not.toBeNull();
    expect(details!.open).toBe(true);
  });

  it("collapses it once they are past the first question", async () => {
    // Reading it once is the point; re-reading it above every question is noise
    // that pushes the actual task off a phone screen.
    stubStorage({ "prism.label.token.batch-key": "t", "prism.labeller": "ana" });
    fetchLabelTask.mockResolvedValue({ task: taskAt(1), closed: false });
    const { container } = render(<LabelPage params={params} />);

    await screen.findByText(/RIGHT QUOTE, WRONG MOUTH/);
    expect(container.querySelector("details")!.open).toBe(false);
  });
});

describe("the article opening", () => {
  // Indian news names an official ONCE — "District Collector S. Venkateswar said" —
  // and then calls them "the Collector" for the rest of the piece. Measured on the
  // first batch: the claimed speaker's name was visible in only 79% of tasks
  // without it, 95% with it. Where it is missing the honest answer is "not sure",
  // and a task nobody can answer teaches us nothing.

  const BASE = {
    article_id: "a1",
    title: "Avoid paddy sowing, farmers told",
    source: "The Hindu",
    speaker: "S. Venkateswar",
    quote_text: "there is only 10-12 tmc of water available",
    context_before: "not to go for paddy cultivation as it could be too risky. ",
    context_after: ", the Collector said. He urged them to save every drop.",
    target: null,
    stance: "neutral",
  };

  it("shows the opening when the quote sits deep in the article", async () => {
    stubStorage({ "prism.label.token.batch-key": "t", "prism.labeller": "ana" });
    fetchLabelTask.mockResolvedValue({
      task: {
        id: "t1", position: 0, kind: "claim_attribution" as const,
        claim: { ...BASE, lead: "District Collector S. Venkateswar reviewed kharif preparations on Tuesday" },
      },
      closed: false,
    });
    render(<LabelPage params={params} />);

    // Without this the labeller sees "the Collector said" and cannot tell whether
    // that is the person named in the question.
    expect(
      await screen.findByText(/District Collector S. Venkateswar reviewed/)
    ).toBeInTheDocument();
  });

  it("omits it when the context already reaches the top of the article", async () => {
    // Repeating the same sentence twice reads as a bug and costs screen space on
    // a phone, which is where most of this labelling actually happens.
    stubStorage({ "prism.label.token.batch-key": "t", "prism.labeller": "ana" });
    fetchLabelTask.mockResolvedValue({
      task: { id: "t2", position: 0, kind: "claim_attribution" as const, claim: { ...BASE, lead: "" } },
      closed: false,
    });
    render(<LabelPage params={params} />);

    await screen.findByText(/the Collector said/);
    expect(screen.queryByText(/HOW THE ARTICLE OPENS/)).not.toBeInTheDocument();
  });
});

describe("the whole article is reachable", () => {
  // Measured on a UNIFORM sample of the corpus: at ANY window width the speaker is
  // named near the quote only ~75% of the time. A wider window does not fix it —
  // Indian news names an official once, then calls them "the Collector" for the
  // rest of the piece. So the article travels with the task, behind a disclosure:
  // the common case stays a ten-second read, the hard case stays answerable.

  const CLAIM = {
    article_id: "a1",
    title: "Inquiry ordered into hospital complications",
    source: "The Hindu",
    speaker: "M. Vijay Bhaskar",
    quote_text: "A preliminary report has already been submitted",
    context_before: "others were reported to be recovering. ",
    context_after: ", he added.",
    target: null,
    stance: "neutral",
  };

  function renderWith(claim: Record<string, unknown>) {
    stubStorage({ "prism.label.token.batch-key": "t", "prism.labeller": "ana" });
    fetchLabelTask.mockResolvedValue({
      task: { id: "t1", position: 0, kind: "claim_attribution" as const, claim },
      closed: false,
    });
    return render(<LabelPage params={params} />);
  }

  it("carries the full article so a role reference can still be resolved", async () => {
    renderWith({
      ...CLAIM,
      article_text:
        "The Telangana government constituted a four-member committee headed by " +
        "M. Vijay Bhaskar to investigate the complications reported at the hospital.",
    });
    expect(await screen.findByText(/Read the whole article/)).toBeInTheDocument();
    expect(screen.getByText(/four-member committee headed by/)).toBeInTheDocument();
  });

  it("offers nothing to open when the article did not travel with the task", async () => {
    // An empty disclosure is a promise the page cannot keep.
    renderWith(CLAIM);
    await screen.findByText(/, he added/);
    expect(screen.queryByText(/Read the whole article/)).not.toBeInTheDocument();
  });
});

describe("the primer is read before the first judgement", () => {
  // The first round shipped its guidance as a collapsed <details>. 30% of 123
  // tasks came back with the two labellers disagreeing, with OPPOSITE systematic
  // biases — one ticked on any shared word ("Monsoon Marathon" with "Monsoon
  // Session"), the other missed one cricket ban reported in English and Kannada.
  // Neither had opened the guidance, because nothing made them.

  const CLAIM = {
    article_id: "a1", title: "T", source: "The Hindu", speaker: "The minister",
    quote_text: "double its outlay", context_before: "said the state would ",
    context_after: " before the monsoon.", target: null, stance: "neutral",
  };

  function ready(kind: string, task: Record<string, unknown>) {
    stubStorage({
      "prism.label.token.batch-key": "t", "prism.labeller": "ana", primer: false,
    } as never);
    fetchLabelBatch.mockResolvedValue({
      name: "B", notes: "", open: true, self_join: false, labeller: "ana",
      kind, total: 10, done: 0,
    });
    fetchLabelTask.mockResolvedValue({ task, closed: false });
    return render(<LabelPage params={params} />);
  }

  it("blocks the first story task until it is acknowledged", async () => {
    ready("story_boundary", {
      id: "t1", position: 0, sector: "news",
      seed: { id: "s", title: "Seed headline", at: null, source_count: 1, actors: [], signals: [] },
      candidates: [],
    });
    // The task itself must NOT be reachable yet.
    expect(await screen.findByText(/READ THIS FIRST/)).toBeInTheDocument();
    expect(screen.queryByText("Seed headline")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /I have read this/ }));
    expect(await screen.findByText("Seed headline")).toBeInTheDocument();
  });

  it("teaches the STORY rule with the mistakes that were actually made", async () => {
    ready("story_boundary", {
      id: "t1", position: 0, sector: "news",
      seed: { id: "s", title: "Seed", at: null, source_count: 1, actors: [], signals: [] },
      candidates: [],
    });
    await screen.findByText(/READ THIS FIRST/);
    // Over-ticking: the round-1 error.
    expect(screen.getByText(/Monsoon Session/)).toBeInTheDocument();
    expect(screen.getByText(/shared word is not a shared story/i)).toBeInTheDocument();

    // UNDER-ticking: the round-2 error, and the reason this primer was rebalanced.
    // Round 1 taught "same topic is not the same story" so well that a labeller
    // stopped grouping several outlets covering ONE incident — which cut true
    // pairs by two thirds. Both directions have to be taught or the fix to one
    // becomes the cause of the other.
    expect(screen.getByText(/one breach reported twice/i)).toBeInTheDocument();
    expect(screen.getByText(/two languages/i)).toBeInTheDocument();
    expect(screen.getByText(/five reports of one/i)).toBeInTheDocument();
  });

  it("teaches the CLAIM rule instead when the batch is claims", async () => {
    ready("claim_attribution", { id: "t1", position: 0, kind: "claim_attribution", claim: CLAIM });
    await screen.findByText(/READ THIS FIRST/);
    expect(screen.getByText(/right quote, wrong mouth/i)).toBeInTheDocument();
    // Story guidance must not leak into the claim primer; they ask opposite things.
    expect(screen.queryByText(/Monsoon Session/)).not.toBeInTheDocument();
  });

  it("teaches topic relation as a third, narrower judgement", async () => {
    ready("topic_relation", {
      id: "t1", position: 0, sector: "news",
      seed: { id: "s", title: "Seed headline", at: null, source_count: 1, actors: [], signals: [] },
      candidates: [{
        id: "c", title: "Candidate headline", at: null,
        source_count: 1, actors: [], signals: ["embedding"],
      }],
    });

    expect(await screen.findByText(/already agreed these are/i)).toBeInTheDocument();
    expect(screen.getByText(/useful related context/i)).toBeInTheDocument();
    expect(screen.getByText(/same person, place, organisation/i)).toBeInTheDocument();
    expect(screen.queryByText(/same unfolding story/i)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /I have read this/ }));
    expect((await screen.findAllByText(/genuinely useful context/i)).length).toBeGreaterThan(0);
  });

  it("does not show again once acknowledged", async () => {
    stubStorage({
      "prism.label.token.batch-key": "t", "prism.labeller": "ana",
      "prism.label.primer.batch-key": "1",
    });
    fetchLabelBatch.mockResolvedValue({
      name: "B", notes: "", open: true, self_join: false, labeller: "ana",
      kind: "claim_attribution", total: 10, done: 3,
    });
    fetchLabelTask.mockResolvedValue({
      task: { id: "t1", position: 0, kind: "claim_attribution", claim: CLAIM }, closed: false,
    });
    render(<LabelPage params={params} />);
    expect((await screen.findAllByText(/double its outlay/)).length).toBeGreaterThan(0);
    expect(screen.queryByText(/READ THIS FIRST/)).not.toBeInTheDocument();
  });
});

describe("practice rounds and tests (labeller workspace, phase 3)", () => {
  const CLAIM = {
    article_id: "a1", title: "Minister announces road outlay", source: "The Hindu",
    speaker: "The minister", quote_text: "double its outlay on rural roads",
    context_before: "the minister said the state would ", context_after: " before the monsoon.",
    target: null, stance: "neutral",
  };
  const claim = { id: "task-c1", position: 0, kind: "claim_attribution" as const, claim: CLAIM };

  it("marks a practice answer straight away, and waits for Next before moving on", async () => {
    stubStorage({ "prism.label.token.batch-key": "t", "prism.labeller": "ana" });
    fetchLabelTask.mockResolvedValue({ task: claim, closed: false });
    postLabelAnswer.mockResolvedValue({
      ok: true,
      feedback: { correct: false, expected: ["task-c1"], explanation: "The words either side name the minister." },
    });
    render(<LabelPage params={params} />);
    await userEvent.click(await screen.findByRole("button", { name: /No —/ }));

    expect(await screen.findByText("Not quite.")).toBeInTheDocument();
    expect(screen.getByText(/Yes — the article credits these words to The minister/)).toBeInTheDocument();
    expect(screen.getByText("The words either side name the minister.")).toBeInTheDocument();
    // The question cannot be answered twice while its answer is on screen.
    expect(screen.queryByRole("button", { name: /No —/ })).not.toBeInTheDocument();
    const loadsBefore = fetchLabelTask.mock.calls.length;
    await userEvent.click(screen.getByRole("button", { name: "Next question" }));
    await waitFor(() => expect(fetchLabelTask.mock.calls.length).toBeGreaterThan(loadsBefore));
  });

  it("moves straight on after a test answer — a test says nothing until the end", async () => {
    stubStorage({ "prism.label.token.batch-key": "t", "prism.labeller": "ana" });
    fetchLabelTask.mockResolvedValue({ task: claim, closed: false });
    postLabelAnswer.mockResolvedValue({ ok: true });
    render(<LabelPage params={params} />);
    const loadsBefore = (await screen.findByRole("button", { name: /Yes —/ }), fetchLabelTask.mock.calls.length);
    await userEvent.click(screen.getByRole("button", { name: /Yes —/ }));
    await waitFor(() => expect(fetchLabelTask.mock.calls.length).toBeGreaterThan(loadsBefore));
    expect(screen.queryByText("Not quite.")).not.toBeInTheDocument();
  });

  it("ends a failed test with the score, the pass mark and the reasons for what was missed", async () => {
    stubStorage({ "prism.label.token.batch-key": "t", "prism.labeller": "ana" });
    fetchLabelTask.mockResolvedValue({
      task: null, closed: false,
      result: {
        right: 13, total: 15, score: 13 / 15, passed: false, pass_mark: 0.9, purpose: "qualify",
        missed: [{ position: 4, about: "S: “q4”", explanation: "Somebody else is named before the quote." }],
      },
    });
    render(<LabelPage params={params} />);
    expect(await screen.findByText("Not this time.")).toBeInTheDocument();
    expect(screen.getByText(/13 of 15 right/)).toBeInTheDocument();
    expect(screen.getByText(/You need 90%/)).toBeInTheDocument();
    expect(screen.getByText("Somebody else is named before the quote.")).toBeInTheDocument();
  });
});

describe("a quote-rendering task (phase 4)", () => {
  const A = { speaker: "Donald Trump", quote: "ಯುದ್ಧ ತಡೆದಿದ್ದೇನೆ", language: "Kannada", code: "kn", outlet: "TV9 Kannada" };
  const B = { speaker: "Donald Trump", quote: "I stopped a war", language: "English", code: "en", outlet: "Mint" };
  const spoken = { id: "task-r1", position: 0, kind: "quote_rendering" as const,
    rendering: { kind: "quote_rendering" as const, question: "spoken" as const, speaker: "Donald Trump", story: "Trump at the UN", a: A, b: null } };

  it("asks whether it was spoken in the language printed, and shapes the quote in its own script", async () => {
    stubStorage({ "prism.label.token.batch-key": "t", "prism.labeller": "ana" });
    fetchLabelTask.mockResolvedValue({ task: spoken, closed: false });
    render(<LabelPage params={params} />);
    expect(await screen.findByRole("heading", { name: "Did Donald Trump say this in Kannada?" })).toBeInTheDocument();
    expect(screen.getByText(/ಯುದ್ಧ ತಡೆದಿದ್ದೇನೆ/).closest("blockquote")).toHaveAttribute("lang", "kn");
    expect(screen.getByRole("button", { name: "I can't read Kannada" })).toBeInTheDocument();
  });

  it("files 'translated' as a definite no and 'spoken so' as a yes", async () => {
    stubStorage({ "prism.label.token.batch-key": "t", "prism.labeller": "ana" });
    fetchLabelTask.mockResolvedValue({ task: spoken, closed: false });
    render(<LabelPage params={params} />);
    await userEvent.click(await screen.findByRole("button", { name: "No — the outlet translated it" }));
    await waitFor(() => expect(postLabelAnswer).toHaveBeenCalled());
    expect(postLabelAnswer.mock.calls[0][1]).toMatchObject({ selected: [], unsure: false, skipped: false });
  });

  it("shows both quotes when asking whether they are the same statement", async () => {
    stubStorage({ "prism.label.token.batch-key": "t", "prism.labeller": "ana" });
    fetchLabelTask.mockResolvedValue({ task: { ...spoken, rendering: { ...spoken.rendering, question: "same" as const, b: B } }, closed: false });
    render(<LabelPage params={params} />);
    expect(await screen.findByRole("heading", { name: "Is this the same statement by Donald Trump?" })).toBeInTheDocument();
    expect(screen.getByText(/I stopped a war/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Yes — the same statement" }));
    await waitFor(() => expect(postLabelAnswer).toHaveBeenCalled());
    expect(postLabelAnswer.mock.calls[0][1].selected).toEqual(["task-r1"]);
  });
});
