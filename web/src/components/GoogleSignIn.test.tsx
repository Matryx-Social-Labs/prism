import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const router = vi.hoisted(() => ({ replace: vi.fn(), push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => router }));
const session = vi.hoisted(() => ({ signInWithGoogle: vi.fn(), saveSession: vi.fn() }));
vi.mock("@/lib/session", () => session);

// The client id is read at module load; stub it before importing the component.
vi.stubEnv("NEXT_PUBLIC_GOOGLE_CLIENT_ID", "test-client.apps.googleusercontent.com");
const { GoogleSignIn } = await import("@/components/GoogleSignIn");

type TokenCb = (r: { access_token?: string; error?: string }) => void;
const gis = vi.hoisted(() => ({ cb: null as TokenCb | null, inits: [] as Record<string, unknown>[], requested: 0 }));

beforeEach(() => {
  vi.clearAllMocks();
  gis.cb = null;
  gis.inits = [];
  gis.requested = 0;
  window.google = {
    accounts: {
      oauth2: {
        initTokenClient: (o) => {
          gis.cb = o.callback;
          gis.inits.push(o);
          return { requestAccessToken: () => { gis.requested += 1; } };
        },
      },
    },
  };
});
afterEach(() => {
  delete window.google;
  window.sessionStorage.clear();
  window.history.replaceState(null, "", "/");
});

// REGRESSION (founder, 2026-09-20): Google's rendered button, hidden under our
// pill at opacity 0, refused every click — it checks its own visibility. Our
// pill is now a real button that starts Google's token flow.
describe("GoogleSignIn", () => {
  it("is our own button, and a click asks Google for a token scoped to email", async () => {
    render(<GoogleSignIn />);
    const btn = screen.getByRole("button", { name: "Continue with Google" });
    expect(btn.className).toContain("p-btn--secondary");
    await userEvent.click(btn);
    await waitFor(() => expect(gis.requested).toBe(1));
    expect(gis.inits[0].client_id).toBe("test-client.apps.googleusercontent.com");
    expect(String(gis.inits[0].scope)).toContain("email");
  });

  it("after Google answers, sends the access token up and finishes the trip — via onboarding for a new reader", async () => {
    window.history.replaceState(null, "", "/signin?next=%2Fplus");
    session.signInWithGoogle.mockResolvedValue({ session: { token: "t", userId: "u", email: "a@b.c" }, needsProfile: true });
    render(<GoogleSignIn />);
    await userEvent.click(screen.getByRole("button", { name: "Continue with Google" }));
    await waitFor(() => expect(gis.cb).not.toBeNull());
    await act(async () => { gis.cb!({ access_token: "ya29.x" }); });
    expect(session.signInWithGoogle).toHaveBeenCalledWith("ya29.x");
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/onboarding?next=%2Fplus"));
  });

  it("a returning reader goes straight back; a closed chooser just re-enables the button", async () => {
    window.sessionStorage.setItem("prism.next.v1", "/plus?from=ask-limit");
    session.signInWithGoogle.mockResolvedValue({ session: { token: "t", userId: "u", email: "a@b.c" }, needsProfile: false });
    render(<GoogleSignIn />);
    await userEvent.click(screen.getByRole("button", { name: /Continue with Google|Opening Google/ }));
    await waitFor(() => expect(gis.cb).not.toBeNull());
    await act(async () => { gis.cb!({ error: "access_denied" }); });
    expect(screen.getByRole("button", { name: "Continue with Google" })).toBeEnabled();
    await userEvent.click(screen.getByRole("button", { name: "Continue with Google" }));
    await act(async () => { gis.cb!({ access_token: "ya29.y" }); });
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/plus?from=ask-limit"));
  });

  it("says what went wrong and one way on when the API refuses Google's token", async () => {
    session.signInWithGoogle.mockRejectedValue(new Error("token rejected by google"));
    render(<GoogleSignIn />);
    await userEvent.click(screen.getByRole("button", { name: "Continue with Google" }));
    await waitFor(() => expect(gis.cb).not.toBeNull());
    await act(async () => { gis.cb!({ access_token: "ya29.z" }); });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Google sign-in did not finish");
    expect(alert).toHaveTextContent("Token rejected by google. Try again, or use your email.");
    expect(screen.getByRole("button", { name: "Continue with Google" })).toBeEnabled();
  });
});
