import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SiteFooter } from "@/components/SiteFooter";
import { ThemeToggle } from "@/components/ThemeToggle";

const mockPathname = vi.fn<() => string>();
vi.mock("next/navigation", () => ({ usePathname: () => mockPathname() }));

afterEach(() => {
  localStorage.clear();
  delete document.documentElement.dataset.theme;
});

/**
 * The theme control's one home on a phone's non-app pages is the footer's Appearance row
 * (Claude Design · screens/PhoneBar.html, direction D): the phone bar has no toggle there.
 */
describe("SiteFooter", () => {
  it("shows on a phone on the non-app pages, with the Appearance control", () => {
    mockPathname.mockReturnValue("/");
    render(<SiteFooter />);
    const footer = screen.getByRole("contentinfo");
    expect(footer).not.toHaveClass("hidden");
    expect(within(footer).getByRole("radiogroup", { name: "Appearance" })).toBeInTheDocument();
  });

  it("stays desk-only in the app, where the tab bar is the phone's chrome", () => {
    mockPathname.mockReturnValue("/feed");
    render(<SiteFooter />);
    expect(screen.getByRole("contentinfo")).toHaveClass("hidden", "lg:block");
  });

  it("links the grievance, contact and delivery pages Razorpay and the IT Rules require, grouped", () => {
    mockPathname.mockReturnValue("/about");
    render(<SiteFooter />);
    const nav = within(screen.getByRole("navigation", { name: "Footer" }));
    const hrefs = Object.fromEntries(nav.getAllByRole("link").map((a) => [a.textContent, a.getAttribute("href")]));
    expect(hrefs).toMatchObject({
      Grievance: "/grievance",
      Contact: "mailto:hello@readprism.news",
      Delivery: "/delivery",
      States: "/state",
      Archive: "/archive",
      Privacy: "/privacy",
    });
    expect(nav.getByText("Policies and contact")).toBeInTheDocument();
  });

  it("follows the header's toggle, so the two never disagree on the desk", () => {
    mockPathname.mockReturnValue("/plus");
    render(<><ThemeToggle /><SiteFooter /></>);
    expect(screen.getByRole("radio", { name: "System" })).toHaveAttribute("aria-checked", "true");
    fireEvent.click(screen.getByRole("button", { name: /theme/ }));
    const picked = localStorage.getItem("prism.theme");
    expect(screen.getByRole("radio", { name: picked === "dark" ? "Dark" : "Light" })).toHaveAttribute("aria-checked", "true");
  });
});
