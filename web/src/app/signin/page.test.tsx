import { describe, expect, it, vi, beforeEach } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SignInPage from "@/app/signin/page";

const requestMagicLink = vi.hoisted(() => vi.fn());
vi.mock("@/lib/session", () => ({ requestMagicLink, saveSession: vi.fn(), signInWithGoogle: vi.fn() }));
const params = vi.hoisted(() => new URLSearchParams());
vi.mock("next/navigation", () => ({ useSearchParams: () => params, useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));

const EMAIL = "reader@example.com";

function emailField() {
  return screen.getByRole("textbox", { name: "Email" });
}
function submitButton() {
  return screen.getByRole("button", { name: /Email me a sign-in link|Sending/ });
}

async function submit(address = EMAIL) {
  await userEvent.type(emailField(), address);
  await userEvent.click(submitButton());
}

beforeEach(() => {
  requestMagicLink.mockReset().mockResolvedValue(undefined);
});

describe("Sign in — sending the link", () => {
  it("cannot be submitted without an email", () => {
    render(<SignInPage />);
    expect(submitButton()).toBeDisabled();
  });

  it("asks for a link for the address the reader entered", async () => {
    render(<SignInPage />);
    await submit();
    expect(requestMagicLink).toHaveBeenCalledWith(EMAIL);
  });

  it("locks the button while the request is in flight", async () => {
    let deliver: () => void = () => {};
    requestMagicLink.mockImplementation(
      () =>
        new Promise<void>((res) => {
          deliver = () => res();
        })
    );
    render(<SignInPage />);
    await submit();

    expect(screen.getByRole("button", { name: "Sending…" })).toBeDisabled();
    expect(requestMagicLink).toHaveBeenCalledTimes(1);

    await act(async () => deliver());
    expect(await screen.findByText("Check your inbox.")).toBeInTheDocument();
  });
});

describe("Sign in — confirmation", () => {
  it("replaces the form with the address the link went to", async () => {
    render(<SignInPage />);
    await submit();

    expect(await screen.findByText("Check your inbox.")).toBeInTheDocument();
    expect(screen.getByText(EMAIL)).toBeInTheDocument();
    // The form is gone — no second send, no confusion about whether it worked.
    expect(screen.queryByRole("textbox", { name: "Email" })).not.toBeInTheDocument();
  });
});

describe("Sign in — failure", () => {
  it("shows what the server said and keeps the form open to retry", async () => {
    requestMagicLink.mockRejectedValue(new Error("Too many sign-in attempts. Try in an hour."));
    render(<SignInPage />);
    await submit();

    expect(await screen.findByText("Too many sign-in attempts. Try in an hour.")).toBeInTheDocument();
    expect(screen.queryByText("Check your inbox.")).not.toBeInTheDocument();
    expect(emailField()).toHaveValue(EMAIL);
    expect(submitButton()).toBeEnabled();
  });

  // A failed send must un-busy the button, or the reader's second attempt is
  // a dead click and the only way out is a page reload.
  it("lets the reader retry after a failed send", async () => {
    requestMagicLink.mockRejectedValueOnce(new Error("Mailer unavailable"));
    render(<SignInPage />);
    await submit();
    await screen.findByText("Mailer unavailable");

    await userEvent.click(submitButton());

    expect(requestMagicLink).toHaveBeenCalledTimes(2);
    expect(await screen.findByText("Check your inbox.")).toBeInTheDocument();
  });
});

describe("Sign in — the way out", () => {
  it("goes back to the story a gate sent the reader from, otherwise to the chart", () => {
    params.set("next", "/story/e1");
    const { unmount } = render(<SignInPage />);
    expect(screen.getByRole("link", { name: /back to the story/i })).toHaveAttribute("href", "/story/e1");
    unmount();
    params.delete("next");
    render(<SignInPage />);
    expect(screen.getByRole("link", { name: /keep reading/i })).toHaveAttribute("href", "/feed");
  });
});
