import { describe, expect, it } from "vitest";
import nextConfig, { CSP } from "../../next.config";

describe("the Content-Security-Policy, report-only first", () => {
  it("is sent report-only on every page, never enforced yet", async () => {
    const rules = await nextConfig.headers!();
    const all = rules.find((r) => r.source === "/:path*")!.headers;
    expect(all.find((h) => h.key === "Content-Security-Policy-Report-Only")?.value).toBe(CSP);
    expect(all.find((h) => h.key === "Content-Security-Policy")).toBeUndefined();
  });

  it("allows what sign-in, checkout, photographs and podcast audio load, and reports to the API", () => {
    for (const needed of ["https://accounts.google.com", "https://checkout.razorpay.com", "img-src 'self' data: blob: https:", "media-src 'self' https:", "frame-ancestors 'none'", "object-src 'none'"]) {
      expect(CSP).toContain(needed);
    }
    expect(CSP).toMatch(/report-uri \S+\/api\/v1\/csp-report/);
  });
});
