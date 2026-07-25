import { describe, expect, it, vi, beforeEach } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AskPanel } from "@/components/AskPanel";
import type { AskCallbacks } from "@/lib/api";

const askQuestion = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", () => ({ askQuestion }));

const PROPS = { eventId: "e1", sourceCount: 4, suggestedQuestions: ["What led to this?"] };

// Hand back the callbacks so a test can drive the stream by hand.
function streamController() {
  let cb: AskCallbacks;
  let release: () => void;
  const started = new Promise<void>((r) => (release = r));
  askQuestion.mockImplementation(async (_id, _q, _s, callbacks: AskCallbacks) => {
    cb = callbacks;
    release();
    await new Promise(() => {}); // never resolves — stream stays open
  });
  return { started, cb: () => cb };
}

beforeEach(() => askQuestion.mockReset());

describe("AskPanel — controlled mode", () => {
  it("renders nothing when closed and the launcher is suppressed", () => {
    const { container } = render(<AskPanel {...PROPS} open={false} onOpenChange={() => {}} launcher={false} />);
    expect(container.querySelector("button")).toBeNull();
  });

  it("shows the chat when the parent opens it", () => {
    render(<AskPanel {...PROPS} open onOpenChange={() => {}} launcher={false} />);
    expect(screen.getByText("Ask this story")).toBeInTheDocument();
  });

  it("asks the parent to close rather than closing itself", async () => {
    const onOpenChange = vi.fn();
    render(<AskPanel {...PROPS} open onOpenChange={onOpenChange} launcher={false} />);
    await userEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("manages its own open state when uncontrolled", async () => {
    render(<AskPanel {...PROPS} />);
    await userEvent.click(screen.getByRole("button", { name: /ask this story/i }));
    expect(screen.getByPlaceholderText(/ask anything/i)).toBeInTheDocument();
  });

  it("states which sources the answers are grounded in", () => {
    render(<AskPanel {...PROPS} open onOpenChange={() => {}} launcher={false} />);
    expect(screen.getByText(/only from this story's 4 sources/i)).toBeInTheDocument();
  });
});

describe("AskPanel — submitting", () => {
  it("ignores an empty question", async () => {
    render(<AskPanel {...PROPS} open onOpenChange={() => {}} launcher={false} />);
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    expect(askQuestion).not.toHaveBeenCalled();
  });

  it("sends a suggested question", async () => {
    askQuestion.mockResolvedValue(undefined);
    render(<AskPanel {...PROPS} open onOpenChange={() => {}} launcher={false} />);
    await userEvent.click(screen.getByRole("button", { name: "What led to this?" }));
    expect(askQuestion).toHaveBeenCalledWith("e1", "What led to this?", null, expect.anything(), expect.anything());
  });

  it("renders streamed tokens and their citations", async () => {
    const s = streamController();
    render(<AskPanel {...PROPS} open onOpenChange={() => {}} launcher={false} />);
    await userEvent.type(screen.getByPlaceholderText(/ask anything/i), "why?{Enter}");
    await s.started;

    // The stream fires outside React's event loop, so flush the updates.
    act(() => {
      s.cb().onToken("Because ");
      s.cb().onToken("of the contracts.");
      s.cb().onCitations([{ number: 1, source_name: "The Hindu", url: "https://x" } as never]);
      // Citations are deliberately withheld until the answer finishes, so the
      // reader never sees a half-formed claim with sources attached.
      s.cb().onDone();
    });
    expect(await screen.findByText(/Because of the contracts\./)).toBeInTheDocument();
    expect(await screen.findByText(/\[1\] The Hindu/)).toBeInTheDocument();
  });

  // REGRESSION: `busy` was read from a render closure, so two taps in one React
  // batch both saw false. Both answers then targeted prev.length - 1, so the
  // first answer's tokens landed in the second's bubble and the second's
  // citations overwrote them — one answer's text under another's sources.
  it("collapses two taps in the same batch into one question", async () => {
    streamController();
    render(<AskPanel {...PROPS} open onOpenChange={() => {}} launcher={false} />);
    const input = screen.getByPlaceholderText(/ask anything/i);
    fireEvent.change(input, { target: { value: "why?" } });

    // Must be synchronous and unawaited: awaiting between clicks lets React
    // flush `busy`, which hides the bug. Two chips or Enter+Send land in one
    // batch on a touch screen, and both used to pass the state guard.
    const send = screen.getByRole("button", { name: /send/i });
    act(() => {
      fireEvent.click(send);
      fireEvent.click(send);
    });

    expect(askQuestion).toHaveBeenCalledTimes(1);
  });

  // REGRESSION: for Devanagari/Tamil/Telugu IMEs, Enter confirms the candidate.
  it("does not submit on the Enter that confirms an IME candidate", async () => {
    askQuestion.mockResolvedValue(undefined);
    render(<AskPanel {...PROPS} open onOpenChange={() => {}} launcher={false} />);
    const input = screen.getByPlaceholderText(/ask anything/i);
    fireEvent.change(input, { target: { value: "क्या" } });

    // Only the composing Enter — submitting anything first would leave the busy
    // guard to block this, and the test would pass with the IME guard removed.
    fireEvent.keyDown(input, { key: "Enter", isComposing: true });
    expect(askQuestion).not.toHaveBeenCalled();

    // The confirming Enter that follows composition does submit.
    fireEvent.keyDown(input, { key: "Enter" });
    expect(askQuestion).toHaveBeenCalledTimes(1);
  });

  it("surfaces a stream error in the answer bubble", async () => {
    askQuestion.mockImplementation(async (_i, _q, _s, cb: AskCallbacks) => {
      cb.onError("The agent is unavailable.");
    });
    render(<AskPanel {...PROPS} open onOpenChange={() => {}} launcher={false} />);
    await userEvent.type(screen.getByPlaceholderText(/ask anything/i), "why?{Enter}");
    expect(await screen.findByText("The agent is unavailable.")).toBeInTheDocument();
  });

  it("recovers when the request itself throws", async () => {
    askQuestion.mockRejectedValue(new Error("network"));
    render(<AskPanel {...PROPS} open onOpenChange={() => {}} launcher={false} />);
    await userEvent.type(screen.getByPlaceholderText(/ask anything/i), "why?{Enter}");
    expect(await screen.findByText("Connection failed.")).toBeInTheDocument();
  });

  // REGRESSION: navigating away mid-answer used to leave the read loop running —
  // metered data, a held connection, and tokens generated for nobody.
  it("aborts the stream when it unmounts", async () => {
    const s = streamController();
    const { unmount } = render(<AskPanel {...PROPS} open onOpenChange={() => {}} launcher={false} />);
    await userEvent.type(screen.getByPlaceholderText(/ask anything/i), "why?{Enter}");
    await s.started;

    const signal = askQuestion.mock.calls[0][4] as AbortSignal;
    expect(signal.aborted).toBe(false);
    unmount();
    await waitFor(() => expect(signal.aborted).toBe(true));
  });
});
