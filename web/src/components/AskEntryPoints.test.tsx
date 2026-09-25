import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AskBar } from "@/components/AskBar";
import { AskContext } from "@/components/AskContext";
import { SelectionAsk } from "@/components/SelectionAsk";
import { Said } from "@/components/Said";
import { EntityMark } from "@/components/EntityText";

/**
 * The four ways into Ask besides the sheet itself. Each hands the panel a
 * question (AskContext) and says where it came from; none renders where no
 * panel is mounted, so the landing and the explainer stay as they were.
 */
const claim = { article_id: "a1", speaker: "Priya Rao", quote_text: "The bridge was inspected in March.", source_name: "The Hindu", url: "https://h/x", published_at: null } as never;
const speakers = [{ speaker: "Priya Rao", role: "engineer", claims: [claim] }] as never;
const entity = { name: "Priya Rao", kind: "person", role: null } as never;

describe("Ask entry points", () => {
  it("the bar sends what is typed, marked as sent from the bar", async () => {
    const open = vi.fn();
    render(<AskContext.Provider value={open}><AskBar suggestions={["Why now?"]} sourceCount={3} /></AskContext.Provider>);
    const input = screen.getByRole("textbox", { name: "Ask this story" });
    await userEvent.type(input, "Who paid?{Enter}");
    expect(open).toHaveBeenCalledWith({ prefill: "Who paid?", submit: true, via: "bar" });
    expect(input).toHaveValue("");
  });

  // The design (v2 · AskBar) prints the story's questions under the bar at
  // the foot of the record; one tap sends it, marked as a chip.
  it("the bar offers the story's suggested questions and sends one as a chip", async () => {
    const open = vi.fn();
    render(<AskContext.Provider value={open}><AskBar suggestions={["Why now?"]} sourceCount={3} /></AskContext.Provider>);
    await userEvent.click(screen.getByRole("button", { name: "Why now?" }));
    expect(open).toHaveBeenCalledWith({ prefill: "Why now?", submit: true, via: "chip" });
  });

  it("the bar sends nothing for an empty question", async () => {
    const open = vi.fn();
    render(<AskContext.Provider value={open}><AskBar suggestions={[]} sourceCount={3} /></AskContext.Provider>);
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
    expect(open).not.toHaveBeenCalled();
  });

  it("a quote card offers to ask about the quote, with the quote and speaker in the question", async () => {
    const open = vi.fn();
    render(<AskContext.Provider value={open}><Said claims={speakers} sourceIndex={new Map([["a1", 1]])} /></AskContext.Provider>);
    await userEvent.click(screen.getByRole("button", { name: "Ask about this quote" }));
    const q = open.mock.calls[0][0];
    expect(q.via).toBe("quote");
    expect(q.prefill).toContain("The bridge was inspected in March.");
    expect(q.prefill).toContain("Priya Rao");
    expect(q.submit).toBeUndefined();
  });

  it("an entity card offers to ask about the entity on this story", async () => {
    const open = vi.fn();
    render(<AskContext.Provider value={open}><p><EntityMark label="Priya Rao" entity={entity} /></p></AskContext.Provider>);
    await userEvent.click(screen.getByText("Priya Rao"));
    await userEvent.click(await screen.findByRole("button", { name: /Ask about Priya Rao on this story/ }));
    expect(open).toHaveBeenCalledWith({ prefill: "What do the reports say about Priya Rao on this story?", via: "entity" });
  });

  it("without a panel mounted, none of the entry points render", () => {
    render(<><AskBar suggestions={[]} sourceCount={1} /><Said claims={speakers} sourceIndex={new Map([["a1", 1]])} /><SelectionAsk /></>);
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("button", { name: "Ask about this quote" })).toBeNull();
  });

  it("selecting a line of the brief offers to ask about it, quoted into the question", async () => {
    const open = vi.fn();
    render(
      <AskContext.Provider value={open}>
        <p data-askable>The bridge was inspected in March and cleared for traffic.</p>
        <p>Chrome text that is not part of the record at all.</p>
        <SelectionAsk />
      </AskContext.Provider>,
    );
    // jsdom has no layout: give ranges a rectangle so the chip can be placed.
    Range.prototype.getBoundingClientRect = () => ({ left: 100, top: 200, width: 120, height: 20, right: 220, bottom: 220, x: 100, y: 200, toJSON: () => ({}) });
    const select = (el: Element) => {
      const range = document.createRange();
      range.selectNodeContents(el);
      const sel = document.getSelection()!;
      sel.removeAllRanges();
      sel.addRange(range);
      act(() => { document.dispatchEvent(new Event("selectionchange")); });
    };
    // Outside the record: nothing.
    select(screen.getByText(/Chrome text/));
    await act(async () => { await new Promise((r) => requestAnimationFrame(() => r(null))); });
    expect(screen.queryByRole("button", { name: /Ask about this/ })).toBeNull();
    // Inside it: the chip, and the line goes into the question.
    select(screen.getByText(/The bridge/));
    await act(async () => { await new Promise((r) => requestAnimationFrame(() => r(null))); });
    fireEvent.click(await screen.findByRole("button", { name: /Ask about this/ }));
    expect(open).toHaveBeenCalledWith({ prefill: "About this line: “The bridge was inspected in March and cleared for traffic.” — ", via: "selection" });
  });
});
