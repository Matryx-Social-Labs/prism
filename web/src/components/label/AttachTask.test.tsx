import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AttachTask } from "@/components/label/AttachTask";
import type { LabelAttachPair } from "@/lib/api";

// The attach check's answers become the gold the attach thresholds are scored
// against, so what is pinned is what a labeller must SEE to judge (both the
// record and the report, the title in its own script) and that each button
// files the answer its words say.

const PAIR: LabelAttachPair = {
  record: {
    headline: "High Court disqualifies MLA",
    summary: "The court set aside the election over an undisclosed case.",
    first_reported: "2026-09-21 10:00",
  },
  article: {
    outlet: "sakshi",
    published: "2026-09-27 08:00",
    language: "te",
    title: "ఎమ్మెల్యే అనర్హత",
    headline_english: "Supreme Court upholds MLA disqualification",
    summary_english: "The Supreme Court dismissed the MLA's appeal.",
  },
};

function renderTask(onAnswer = vi.fn(), over: Partial<Parameters<typeof AttachTask>[0]> = {}) {
  render(<AttachTask pair={PAIR} saving={false} onAnswer={onAnswer} {...over} />);
  return onAnswer;
}

describe("AttachTask", () => {
  it("shows the record and the report, the title as printed in its own language", () => {
    renderTask();
    expect(screen.getByRole("heading", { name: "Is this report about the record's happening?" })).toBeInTheDocument();
    expect(screen.getByText("High Court disqualifies MLA")).toBeInTheDocument();
    expect(screen.getByText(PAIR.record.summary)).toBeInTheDocument();
    expect(screen.getByText("first reported 2026-09-21 10:00")).toBeInTheDocument();
    expect(screen.getByText("sakshi · Telugu · 2026-09-27 08:00")).toBeInTheDocument();
    // Shaped by the script's own face, and read out in its own language.
    expect(screen.getByText("ఎమ్మెల్యే అనర్హత")).toHaveAttribute("lang", "te");
    expect(screen.getByText("Supreme Court upholds MLA disqualification")).toBeInTheDocument();
    expect(screen.getByText(PAIR.article.summary_english)).toBeInTheDocument();
  });

  it("does not print an English report's headline twice", () => {
    render(
      <AttachTask
        pair={{ ...PAIR, article: { ...PAIR.article, language: "en", title: "MLA disqualified", headline_english: "MLA disqualified" } }}
        saving={false}
        onAnswer={vi.fn()}
      />
    );
    expect(screen.getAllByText("MLA disqualified")).toHaveLength(1);
  });

  it.each([
    ["Same happening", "same"],
    ["Later development", "follow_up"],
    ["Different happening", "different"],
    ["Not sure", "unsure"],
  ])("files %s as %s", async (name, expected) => {
    const onAnswer = renderTask();
    await userEvent.click(screen.getByRole("button", { name }));
    expect(onAnswer).toHaveBeenCalledTimes(1);
    expect(onAnswer).toHaveBeenCalledWith(expected);
  });

  it("says Saving… on the answer pressed, and lets none be pressed while it saves", () => {
    renderTask(vi.fn(), { saving: true, pending: "follow_up" });
    expect(screen.getByRole("button", { name: "Saving…" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Later development" })).toBeNull();
    expect(screen.getByRole("button", { name: "Same happening" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Not sure" })).toBeDisabled();
  });

  it("shows a practice answer's verdict in place of the answers", () => {
    renderTask(vi.fn(), { feedback: <p>Verdict here</p> });
    expect(screen.getByText("Verdict here")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Same happening" })).toBeNull();
  });
});
