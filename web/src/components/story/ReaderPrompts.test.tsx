import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ArrivalNote, ReaderQuestion } from "@/components/story/ReaderPrompts";

const send = vi.hoisted(() => vi.fn());
vi.mock("@/lib/analytics", () => ({ send }));

// The slot asks only once the reader reaches it. Keyed on the element observed,
// so next/link's own prefetch observers never answer for it.
const observed = new Map<Element, IntersectionObserverCallback>();
class IO {
  constructor(private cb: IntersectionObserverCallback) {}
  observe(el: Element) { observed.set(el, this.cb); }
  unobserve() {}
  disconnect() {}
  takeRecords() { return []; }
}

function slot() {
  const { container } = render(<ReaderQuestion />);
  return container.firstElementChild!;
}
function reach(el: Element) {
  act(() => observed.get(el)!([{ isIntersecting: true, target: el } as IntersectionObserverEntry], {} as IntersectionObserver));
}
const HEARD_Q = "Where did you hear about Prism?";
const CHECK_Q = "Could you check this story for yourself?";
const DAY = 24 * 60 * 60 * 1000;

beforeEach(() => {
  send.mockReset();
  observed.clear();
  vi.stubGlobal("IntersectionObserver", IO);
});

describe("the one question at the foot of a story", () => {
  it("asks nothing until the reader has scrolled to it", () => {
    const el = slot();
    expect(screen.queryByRole("group")).toBeNull();
    reach(el);
    expect(screen.getByRole("group", { name: CHECK_Q })).toBeInTheDocument();
  });

  it("asks where they heard of Prism on the 2nd story of a visit, counts the pick, and never asks it again", async () => {
    sessionStorage.setItem("prism.depth", "2");
    reach(slot());
    expect(screen.queryByText(CHECK_Q)).toBeNull(); // one question a page
    await userEvent.click(screen.getByRole("button", { name: "Product Hunt or a launch site" }));
    expect(send.mock.calls).toEqual([["heard", "launch"]]);
    expect(screen.getByRole("status")).toHaveTextContent("Thank you.");
    cleanup();
    reach(slot());
    expect(screen.queryByText(HEARD_Q)).toBeNull();
  });

  it("does not ask where they heard on any other story of the visit", () => {
    sessionStorage.setItem("prism.depth", "3");
    reach(slot());
    expect(screen.queryByText(HEARD_Q)).toBeNull();
  });

  it("closes for good on Not now, counting nothing", async () => {
    sessionStorage.setItem("prism.depth", "2");
    reach(slot());
    await userEvent.click(screen.getByRole("button", { name: "Not now" }));
    expect(screen.queryByRole("group")).toBeNull();
    expect(send).not.toHaveBeenCalled();
    cleanup();
    reach(slot());
    expect(screen.queryByText(HEARD_Q)).toBeNull();
  });

  it("asks whether the story could be checked at most once in 14 days, and counts the answer as a word", async () => {
    reach(slot());
    await userEvent.click(screen.getByRole("button", { name: "Partly" }));
    expect(send.mock.calls).toEqual([["survey", "check:partly"]]);
    cleanup();
    reach(slot()); // the next story of the visit
    expect(screen.queryByText(CHECK_Q)).toBeNull();
    cleanup();
    localStorage.setItem("prism.check.at", String(Date.now() - 13 * DAY));
    reach(slot());
    expect(screen.queryByText(CHECK_Q)).toBeNull();
    cleanup();
    localStorage.setItem("prism.check.at", String(Date.now() - 14 * DAY - 1000));
    reach(slot());
    expect(screen.getByText(CHECK_Q)).toBeInTheDocument();
  });

  it("asks nothing when the browser keeps no memory of having asked", () => {
    vi.stubGlobal("localStorage", { getItem: () => { throw new Error("blocked"); }, setItem: () => { throw new Error("blocked"); } });
    reach(slot());
    expect(screen.queryByRole("group")).toBeNull();
  });
});

describe("the note for a first visit by a shared link", () => {
  afterEach(() => {
    document.cookie = "prism.returning=; max-age=0; path=/";
    window.history.replaceState(null, "", "/");
  });

  it("says what the page is to a reader a shared link brought, and stays closed once closed", async () => {
    window.history.replaceState(null, "", "/story/e1?s=story");
    render(<ArrivalNote />);
    expect(await screen.findByRole("note")).toHaveTextContent("one record per news event");
    expect(screen.getByRole("link", { name: "Today’s record →" })).toHaveAttribute("href", "/feed");
    await userEvent.click(screen.getByRole("button", { name: "Close this note" }));
    expect(screen.queryByRole("note")).toBeNull();
    cleanup();
    render(<ArrivalNote />);
    await act(async () => {});
    expect(screen.queryByRole("note")).toBeNull();
  });

  it("is not shown to a reader who has reached the chart before", async () => {
    window.history.replaceState(null, "", "/story/e1?s=story");
    document.cookie = "prism.returning=1; path=/";
    render(<ArrivalNote />);
    await act(async () => {});
    expect(screen.queryByRole("note")).toBeNull();
  });

  it("is not shown without the share marker", async () => {
    window.history.replaceState(null, "", "/story/e1?s=made-up");
    render(<ArrivalNote />);
    await act(async () => {});
    expect(screen.queryByRole("note")).toBeNull();
  });
});
