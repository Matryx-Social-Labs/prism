import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import GrievancePage, { metadata } from "@/app/grievance/page";

const fetchGrievanceReport = vi.hoisted(() => vi.fn());
const fileGrievance = vi.hoisted(() => vi.fn());
vi.mock("@/lib/grievance", async () => ({ ...(await vi.importActual<typeof import("@/lib/grievance")>("@/lib/grievance")), fetchGrievanceReport, fileGrievance }));

const month = (m: string, over = {}) => ({ month: m, received: 0, resolved: 0, rejected: 0, open: 0, median_days: null, ...over });
const page = async (q: Record<string, string> = {}) => render(await GrievancePage({ searchParams: Promise.resolve(q) }));

beforeEach(() => {
  fetchGrievanceReport.mockReset().mockResolvedValue({
    since: "2026-09-01",
    decide_within_days: 15,
    months: [month("2026-10", { received: 3, resolved: 1, rejected: 1, open: 1, median_days: 4.5 }), month("2026-09")],
  });
  fileGrievance.mockReset();
});
afterEach(() => vi.clearAllMocks());

describe("/grievance — the IT Rules grievance page", () => {
  it("names the officer with designation, organisation, email and address, never an invented one", async () => {
    await page();
    const officer = within(screen.getByRole("region", { name: "Grievance Officer" }));
    expect(officer.getByText("Tejas ShylaShashidhara")).toBeInTheDocument();
    expect(officer.getByText("Grievance Officer (Chief Executive Officer)")).toBeInTheDocument();
    expect(officer.getByText("Prism Media Intelligence LLP")).toBeInTheDocument();
    expect(officer.getByRole("link", { name: "grievance@readprism.news" })).toHaveAttribute("href", "mailto:grievance@readprism.news");
    // No postal address is known yet: the city, and nothing made up.
    expect(officer.getByText("Bengaluru, Karnataka, India")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/\+91|\b\d{6}\b/);
  });

  it("is an indexable trust page that shares its own address", () => {
    expect(metadata.alternates?.canonical).toBe("/grievance");
    expect(metadata.openGraph?.url).toBe("/grievance");
    expect(metadata.robots).toBeUndefined();
  });

  it("states both clocks", async () => {
    await page();
    const how = within(screen.getByRole("region", { name: "How it works" }));
    expect(how.getByText("Acknowledged within 24 hours.")).toBeInTheDocument();
    expect(how.getByText("Decided within 15 days.")).toBeInTheDocument();
    expect(how.getByText(/a copy of it as we recorded it/)).toBeInTheDocument();
  });

  it("prints every month, a month with no complaints as zeros and its median as a dash", async () => {
    await page();
    const rows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
    expect(rows.map((r) => r.textContent)).toEqual(["October 202631114.5", "September 20260000—"]);
  });

  it("says so when the count cannot be reached, rather than printing nothing", async () => {
    fetchGrievanceReport.mockResolvedValue(null);
    await page();
    expect(screen.getByText("The monthly count cannot be reached right now.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("prefills the form from a record's link, and ignores a kind or page that is not ours", async () => {
    const { unmount } = await page({ kind: "A quote is not in the article", record: "/story/abc" });
    expect(screen.getByLabelText("What is it about?")).toHaveValue("A quote is not in the article");
    expect(screen.getByLabelText("Which page (optional)")).toHaveValue("/story/abc");
    unmount();
    await page({ kind: "Buy now", record: "//evil.example/x" });
    expect(screen.getByLabelText("What is it about?")).toHaveValue("");
    expect(screen.getByLabelText("Which page (optional)")).toHaveValue("");
  });

  it("sends the complaint and shows the reference, saying whether the acknowledgement went out", async () => {
    fileGrievance.mockResolvedValue({ ref: "PG-20260929-7K3Q", acknowledged: false, decide_by: "2026-10-14T08:30:00Z" });
    await page({ kind: "A fact is wrong", record: "/story/abc" });
    await userEvent.type(screen.getByLabelText("What is wrong"), "The date in the headline is wrong.");
    await userEvent.type(screen.getByLabelText("Your email"), "asha@example.test");
    await userEvent.click(screen.getByRole("button", { name: "Send the complaint" }));
    expect(fileGrievance).toHaveBeenCalledWith({
      category: "A fact is wrong", subject_url: "/story/abc", body: "The date in the headline is wrong.",
      email: "asha@example.test", name: "", website: "",
    });
    expect(await screen.findByText("PG-20260929-7K3Q")).toBeInTheDocument();
    expect(screen.getByText(/could not be emailed to asha@example.test\. Keep this reference/)).toBeInTheDocument();
    expect(screen.getByText(/decide it by 14 October 2026/)).toBeInTheDocument();
  });

  it("says why a complaint was refused, and keeps what was typed", async () => {
    fileGrievance.mockRejectedValue(new Error("Too many complaints from this connection today. Write to grievance@readprism.news instead."));
    await page({ kind: "Something else" });
    await userEvent.type(screen.getByLabelText("What is wrong"), "Something is not right here.");
    await userEvent.type(screen.getByLabelText("Your email"), "asha@example.test");
    await userEvent.click(screen.getByRole("button", { name: "Send the complaint" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/Too many complaints/);
    expect(screen.getByLabelText("What is wrong")).toHaveValue("Something is not right here.");
  });

  it("asks for a kind before sending anything, and hides the honeypot from people", async () => {
    await page();
    await userEvent.type(screen.getByLabelText("What is wrong"), "Something is not right here.");
    await userEvent.type(screen.getByLabelText("Your email"), "asha@example.test");
    await userEvent.click(screen.getByRole("button", { name: "Send the complaint" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Choose what the complaint is about.");
    expect(fileGrievance).not.toHaveBeenCalled();
    const trap = document.querySelector<HTMLInputElement>('input[name="website"]')!;
    expect(trap.tabIndex).toBe(-1);
    expect(trap.closest('[aria-hidden="true"]')).not.toBeNull();
  });
});
