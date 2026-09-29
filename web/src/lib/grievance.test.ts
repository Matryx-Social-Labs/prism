import { afterEach, describe, expect, it, vi } from "vitest";
import { fileGrievance, grievanceHref, recordPath } from "@/lib/grievance";
import { GRIEVANCE_OFFICER } from "@/lib/legal";
import { ORGANIZATION } from "@/lib/seo";

afterEach(() => vi.unstubAllGlobals());

const input = { email: "a@example.test", category: "A fact is wrong" as const, body: "The date is wrong.", name: "", subject_url: "", website: "" };
const answer = (status: number, body: unknown) => vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));

describe("the grievance client", () => {
  it("addresses the form with the kind and the record filled in", () => {
    const href = new URL(grievanceHref("A fact is wrong", "/story/abc"), "https://www.readprism.news");
    expect([href.pathname, href.searchParams.get("kind"), href.searchParams.get("record"), href.hash]).toEqual(["/grievance", "A fact is wrong", "/story/abc", "#complain"]);
    expect(grievanceHref("Something else")).toBe("/grievance?kind=Something+else#complain");
  });

  it("prefills only a path on this site", () => {
    expect(recordPath("/story/abc")).toBe("/story/abc");
    for (const v of ["//evil.example/x", "https://evil.example/x", "javascript:alert(1)", undefined, ["/story/a"]]) expect(recordPath(v)).toBe("");
  });

  it("returns the reference, and turns every refusal into a sentence with a way on", async () => {
    vi.stubGlobal("fetch", answer(201, { ref: "PG-20260929-7K3Q", acknowledged: true, decide_by: "2026-10-14T08:30:00Z" }));
    expect((await fileGrievance(input)).ref).toBe("PG-20260929-7K3Q");

    vi.stubGlobal("fetch", answer(429, { detail: "Too many complaints from this connection today." }));
    await expect(fileGrievance(input)).rejects.toThrow("Too many complaints from this connection today.");

    vi.stubGlobal("fetch", answer(422, { detail: [{ loc: ["body", "email"], msg: "bad" }] }));
    await expect(fileGrievance(input)).rejects.toThrow(/Check the email address/);

    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("offline"); }));
    await expect(fileGrievance(input)).rejects.toThrow(/could not be reached\. Write to grievance@readprism\.news/);
  });

  it("tells search and answer engines who the Grievance Officer is (Organization JSON-LD)", () => {
    expect(ORGANIZATION.contactPoint).toContainEqual({ "@type": "ContactPoint", contactType: "grievance", name: GRIEVANCE_OFFICER.name, email: "grievance@readprism.news" });
  });
});
