import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import StoriesAdminPage from "@/app/admin/stories/page";

const fetchAdminStories = vi.hoisted(() => vi.fn());
const pinStory = vi.hoisted(() => vi.fn());
const unpinStory = vi.hoisted(() => vi.fn());
const ADMIN = vi.hoisted(() => ({ session: { token: "t", userId: "u", email: "f@example.test" }, email: "f@example.test" }));
vi.mock("@/components/admin/AdminShell", async (orig) => ({ ...(await orig<typeof import("@/components/admin/AdminShell")>()), useAdmin: () => ADMIN }));
vi.mock("@/lib/admin", async (orig) => ({ ...(await orig<typeof import("@/lib/admin")>()), fetchAdminStories, pinStory, unpinStory }));

const story = (slug: string, over = {}) => ({
  slug, label: `Story ${slug}`, status: "active", developments: 12, source_count: 9, velocity: 3, running: false,
  pinned: false, pinned_until: null, last_updated_at: "2026-10-02T12:00:00Z", ...over,
});

beforeEach(() => {
  fetchAdminStories.mockReset().mockResolvedValue({ stories: [
    story("iran-war", { pinned: true, pinned_until: "2026-10-09T12:00:00Z", running: true }), story("flydubai")] , pin_days_max: 30 });
  pinStory.mockReset().mockResolvedValue(story("flydubai", { pinned: true }));
  unpinStory.mockReset().mockResolvedValue(story("iran-war"));
});

describe("admin stories", () => {
  it("says which story is pinned and until when, and pins another for the days chosen", async () => {
    render(<StoriesAdminPage />);
    const iran = (await screen.findByRole("link", { name: "Story iran-war" })).closest("li")!;
    expect(within(iran).getByText(/Pinned until/)).toBeInTheDocument();
    expect(within(iran).getByRole("button", { name: "Unpin" })).toBeInTheDocument();
    const fly = screen.getByRole("link", { name: "Story flydubai" }).closest("li")!;
    await userEvent.selectOptions(within(fly).getByLabelText(/Days to pin/), "3");
    await userEvent.click(within(fly).getByRole("button", { name: "Pin" }));
    expect(pinStory).toHaveBeenCalledWith(ADMIN.session, "flydubai", 3);
    expect(fetchAdminStories).toHaveBeenCalledTimes(2); // the list is read again after the change
  });

  it("unpins, and shows a refusal as an error", async () => {
    unpinStory.mockRejectedValueOnce(new Error("No story with that address is being served"));
    render(<StoriesAdminPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Unpin" }));
    expect(unpinStory).toHaveBeenCalledWith(ADMIN.session, "iran-war");
    expect(await screen.findByText("No story with that address is being served")).toBeInTheDocument();
  });
});
