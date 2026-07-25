import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ShareButton } from "@/components/ShareButton";

const STORY = { url: "/story/abc", title: "Kerala power crisis deepens" };

function stubNavigator(props: { share?: unknown; clipboard?: unknown }) {
  const nav: Record<string, unknown> = {};
  if ("share" in props) nav.share = props.share;
  if ("clipboard" in props) nav.clipboard = props.clipboard;
  vi.stubGlobal("navigator", nav);
}

async function clickShare() {
  await userEvent.click(screen.getByRole("button", { name: /share this story/i }));
}

describe("ShareButton", () => {
  it("opens the native sheet with the headline, not just a bare link", async () => {
    const share = vi.fn().mockResolvedValue(undefined);
    stubNavigator({ share });
    render(<ShareButton {...STORY} />);
    await clickShare();

    // Most chat apps ignore `title` and paste text+url, so `text` must carry the headline.
    expect(share).toHaveBeenCalledWith(
      expect.objectContaining({ text: STORY.title, url: `${window.location.origin}/story/abc` })
    );
  });

  it("does nothing when the reader dismisses the sheet", async () => {
    const share = vi.fn().mockRejectedValue(Object.assign(new Error("x"), { name: "AbortError" }));
    const writeText = vi.fn().mockResolvedValue(undefined);
    stubNavigator({ share, clipboard: { writeText } });
    render(<ShareButton {...STORY} />);
    await clickShare();

    // Cancelling is a decision — copying behind their back ignores it.
    expect(writeText).not.toHaveBeenCalled();
    expect(screen.queryByText(/link copied/i)).not.toBeInTheDocument();
  });

  it("falls back to copying when the sheet fails for a real reason", async () => {
    const share = vi.fn().mockRejectedValue(new Error("not allowed"));
    const writeText = vi.fn().mockResolvedValue(undefined);
    stubNavigator({ share, clipboard: { writeText } });
    render(<ShareButton {...STORY} />);
    await clickShare();

    expect(writeText).toHaveBeenCalledOnce();
    expect(await screen.findByText(/link copied/i)).toBeInTheDocument();
  });

  it("copies the link when the browser has no share sheet", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    stubNavigator({ clipboard: { writeText } });
    render(<ShareButton {...STORY} />);
    await clickShare();

    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/story/abc`);
    expect(await screen.findByText(/link copied/i)).toBeInTheDocument();
  });

  it("does not claim success when the clipboard write is denied", async () => {
    // Denied writes are routine: no document focus, permission refused, in-app
    // webviews. Reporting success there is the same lie as the bug below.
    const writeText = vi.fn().mockRejectedValue(new DOMException("denied", "NotAllowedError"));
    stubNavigator({ clipboard: { writeText } });
    render(<ShareButton {...STORY} />);
    await clickShare();

    expect(writeText).toHaveBeenCalledOnce();
    expect(screen.queryByText(/link copied/i)).not.toBeInTheDocument();
  });

  // REGRESSION: `nav?.clipboard?.writeText()` short-circuits to undefined when
  // the API is absent, and `await undefined` resolves — so the old code reported
  // success having copied nothing. Both APIs are secure-context-only, so this is
  // every plain-http origin, including LAN-IP dev on a phone.
  it("does not claim success when neither share nor clipboard exists", async () => {
    stubNavigator({});
    render(<ShareButton {...STORY} />);
    await clickShare();

    expect(screen.queryByText(/link copied/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /share this story/i })).toHaveTextContent("Share");
  });
});
