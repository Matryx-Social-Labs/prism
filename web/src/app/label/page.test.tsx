import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LabellerWorkspace from "@/app/label/page";

// @/lib/labeller's pure helpers stay real (labelTokenKey is the contract with the
// task page); only its network calls are stubbed.
const useSession = vi.hoisted(() => vi.fn());
const fetchLabellerMe = vi.hoisted(() => vi.fn());
const fetchLabellerBatches = vi.hoisted(() => vi.fn());
const applyAsLabeller = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn() }));
const fetchSpy = vi.hoisted(() => vi.fn());

vi.mock("@/lib/session", () => ({ useSession, authHeader: () => ({}) }));
vi.mock("@/lib/labeller", async (orig) => ({
  ...(await orig<typeof import("@/lib/labeller")>()),
  fetchLabellerMe,
  fetchLabellerBatches,
  applyAsLabeller,
}));
vi.mock("next/navigation", () => ({ useRouter: () => router }));

const SESSION = { token: "t", userId: "u", email: "a@example.test" };
const LANGS = [
  { code: "en", name: "English", native: "English" },
  { code: "kn", name: "Kannada", native: "ಕನ್ನಡ" },
];
const me = (status: string, languages_read: string[] = []) => ({ status, languages_read, note: "", languages_available: LANGS });

beforeEach(() => {
  localStorage.clear();
  useSession.mockReset().mockReturnValue(null);
  fetchLabellerMe.mockReset();
  fetchLabellerBatches.mockReset();
  applyAsLabeller.mockReset().mockResolvedValue({ status: "applied", languages_read: ["kn"] });
  router.push.mockReset();
  fetchSpy.mockReset();
  vi.stubGlobal("fetch", fetchSpy);
});

describe("the labeller workspace", () => {
  it("asks a stranger to sign in, and brings them back here afterwards", async () => {
    render(<LabellerWorkspace />);
    const link = await screen.findByRole("link", { name: "Sign in to apply" });
    expect(link).toHaveAttribute("href", "/signin?next=/label");
  });

  it("applies with the languages the reader ticks", async () => {
    useSession.mockReturnValue(SESSION);
    fetchLabellerMe.mockResolvedValueOnce(me("none")).mockResolvedValue(me("applied", ["kn"]));
    render(<LabellerWorkspace />);
    await userEvent.click(await screen.findByRole("checkbox", { name: /Kannada/ }));
    await userEvent.click(screen.getByRole("button", { name: "Apply" }));
    expect(applyAsLabeller).toHaveBeenCalledWith(SESSION, ["kn"], "");
    expect(await screen.findByText("Your application is in")).toBeInTheDocument();
  });

  it("cannot apply without choosing a language", async () => {
    useSession.mockReturnValue(SESSION);
    fetchLabellerMe.mockResolvedValue(me("none"));
    render(<LabellerWorkspace />);
    expect(await screen.findByRole("button", { name: "Apply" })).toBeDisabled();
  });

  it("shows an approved labeller their batches with their own progress, never others' answers", async () => {
    useSession.mockReturnValue(SESSION);
    fetchLabellerMe.mockResolvedValue(me("active", ["en", "kn"]));
    fetchLabellerBatches.mockResolvedValue({
      status: "active",
      ready: [{ key: "k1", name: "Cross-language", kind: "event_identity", notes: "", eligible: 40, answered: 12, labellers: 3 }],
      done: [],
    });
    render(<LabellerWorkspace />);
    const row = within((await screen.findByText("Cross-language")).closest("li")!);
    expect(row.getByText("Is this the same happening?")).toBeInTheDocument();
    expect(row.getByText("12 of 40 done · 3 labellers")).toBeInTheDocument();
    expect(row.getByRole("button", { name: "Continue" })).toBeInTheDocument();
    expect(row.getByRole("link", { name: "How this task works" })).toHaveAttribute("href", "/label/learn/event_identity");
  });

  it("starting a batch stores the credential where the task page reads it, then opens it", async () => {
    useSession.mockReturnValue(SESSION);
    fetchLabellerMe.mockResolvedValue(me("active", ["en"]));
    fetchLabellerBatches.mockResolvedValue({
      status: "active",
      ready: [{ key: "k1", name: "Batch", kind: "claim_attribution", notes: "", eligible: 5, answered: 0, labellers: 0 }],
      done: [],
    });
    fetchSpy.mockResolvedValue(new Response(JSON.stringify({ token: "tok-123" }), { status: 200 }));
    render(<LabellerWorkspace />);
    await userEvent.click(await screen.findByRole("button", { name: "Start" }));
    await waitFor(() => expect(router.push).toHaveBeenCalledWith("/label/k1"));
    // The exact key the task page (web/src/app/label/[key]) looks for.
    expect(localStorage.getItem("prism.label.token.k1")).toBe("tok-123");
  });

  it("tells a paused labeller who to ask, and offers no batches", async () => {
    useSession.mockReturnValue(SESSION);
    fetchLabellerMe.mockResolvedValue(me("paused", ["en"]));
    render(<LabellerWorkspace />);
    expect(await screen.findByText("Your labelling is paused")).toBeInTheDocument();
    expect(fetchLabellerBatches).not.toHaveBeenCalled();
  });

  it("tells a removed labeller their labelling has ended, and offers no batches", async () => {
    useSession.mockReturnValue(SESSION);
    fetchLabellerMe.mockResolvedValue(me("removed", ["en"]));
    render(<LabellerWorkspace />);
    expect(await screen.findByText("Your labelling has ended")).toBeInTheDocument();
    expect(fetchLabellerBatches).not.toHaveBeenCalled();
  });

  it("lets anyone read how each task works, before applying or being approved", async () => {
    render(<LabellerWorkspace />);
    const link = await screen.findByRole("link", { name: "Who said this?" });
    expect(link).toHaveAttribute("href", "/label/learn/claim_attribution");
  });

  describe("learn and qualify (phase 3)", () => {
    const kind = (over: Record<string, unknown>) => ({
      kind: "claim_attribution", qualified: false, best_score: null, attempts: 0,
      can_practise: true, can_test: true, retake_at: null, has_work: true, ...over,
    });
    const board = (k: Record<string, unknown>) => {
      useSession.mockReturnValue(SESSION);
      fetchLabellerMe.mockResolvedValue(me("active", ["en"]));
      fetchLabellerBatches.mockResolvedValue({ status: "active", ready: [], done: [], kinds: [kind(k)] });
      render(<LabellerWorkspace />);
    };
    const section = async () => within((await screen.findByRole("heading", { name: "Learn and qualify" })).closest("section")!);

    it("offers practice and the test to someone who has not taken it, and the test opens its task page", async () => {
      board({});
      const s = await section();
      expect(s.getByText("Not taken yet")).toBeInTheDocument();
      expect(s.getByRole("button", { name: "Practise" })).toBeInTheDocument();
      fetchSpy.mockResolvedValue(new Response(JSON.stringify({ key: "q1", token: "tok-q" }), { status: 200 }));
      await userEvent.click(s.getByRole("button", { name: "Take the test" }));
      await waitFor(() => expect(router.push).toHaveBeenCalledWith("/label/q1"));
      expect(String(fetchSpy.mock.calls[0][0])).toContain("/api/v1/labeller/qualify/claim_attribution/start");
      expect(localStorage.getItem("prism.label.token.q1")).toBe("tok-q");
    });

    it("says when a failed test can be retaken, and offers no test until then", async () => {
      board({ attempts: 1, best_score: 0.8667, can_test: false, retake_at: "2026-09-24T12:00:00+00:00" });
      const s = await section();
      expect(s.getByText(/Best so far 87% · you can retake it after/)).toBeInTheDocument();
      expect(s.queryByRole("button", { name: "Take the test" })).not.toBeInTheDocument();
      expect(s.getByRole("button", { name: "Practise" })).toBeInTheDocument();
    });

    it("marks a passed kind as passed", async () => {
      board({ qualified: true, best_score: 1, attempts: 1, can_test: false });
      expect((await section()).getByText("Passed")).toBeInTheDocument();
    });
  });
});

