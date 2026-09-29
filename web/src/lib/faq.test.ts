import { describe, expect, it } from "vitest";
import manifest from "@/app/manifest";
import { LANDING_FAQ } from "@/lib/faq";

describe("the landing FAQ", () => {
  // Every answer is checked against the code it describes: this one is the manifest.
  it("answers 'Is there an app?' as the manifest installs it: no store, the home screen, opening on Today", () => {
    const app = LANDING_FAQ.find((f) => f.q === "Is there an app?");
    expect(app?.a).toMatch(/^Not in an app store\./);
    expect(app?.a).toMatch(/home screen/);
    expect(app?.a).toMatch(/opens on Today/);
    const m = manifest();
    expect(m.display).toBe("standalone");
    expect(m.start_url).toBe("/feed"); // the chart, titled Today
  });
});
