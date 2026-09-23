import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
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
    expect(await screen.findByText("Cross-language")).toBeInTheDocument();
    expect(screen.getByText("Is this the same happening?")).toBeInTheDocument();
    expect(screen.getByText("12 of 40 done · 3 labellers")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue" })).toBeInTheDocument();
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
});
