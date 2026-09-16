import { beforeEach, describe, expect, it, vi } from "vitest";

// `/` branches on one cookie: a first visitor gets the landing, anyone who has
// reached the chart before is sent back to it. Both arms are asserted so a
// page that always renders the landing (or always redirects) cannot ship.
const has = vi.hoisted(() => vi.fn<(name: string) => boolean>());
const redirect = vi.hoisted(() => vi.fn());
vi.mock("next/headers", () => ({ cookies: async () => ({ has }) }));
vi.mock("next/navigation", () => ({ redirect }));
vi.mock("@/components/Landing", () => ({ Landing: () => <main>the landing</main> }));

import Page from "@/app/page";

beforeEach(() => {
  has.mockReset();
  redirect.mockReset();
});

describe("/ — landing for a first visitor, chart for a returning reader", () => {
  it("renders the landing when the returning cookie is absent", async () => {
    has.mockReturnValue(false);
    const tree = await Page();
    expect(redirect).not.toHaveBeenCalled();
    expect(tree).toBeTruthy();
    expect(has).toHaveBeenCalledWith("prism.returning");
  });

  it("redirects to /feed when the returning cookie is present", async () => {
    has.mockReturnValue(true);
    await Page();
    expect(redirect).toHaveBeenCalledWith("/feed");
  });
});
