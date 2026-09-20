import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const router = vi.hoisted(() => ({ replace: vi.fn(), push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => router }));
const session = vi.hoisted(() => ({ signInWithGoogle: vi.fn(), saveSession: vi.fn() }));
vi.mock("@/lib/session", () => session);

// The client id is read at module load; stub it before importing the component.
vi.stubEnv("NEXT_PUBLIC_GOOGLE_CLIENT_ID", "test-client.apps.googleusercontent.com");
const { GoogleSignIn } = await import("@/components/GoogleSignIn");

type Cb = (r: { credential: string }) => void;
const gis = vi.hoisted(() => ({ cb: null as Cb | null, rendered: [] as Record<string, unknown>[] }));

beforeEach(() => {
  vi.clearAllMocks();
  gis.cb = null;
  gis.rendered = [];
  window.google = {
    accounts: {
      id: {
        initialize: (o) => { gis.cb = o.callback; },
        renderButton: (_el, o) => { gis.rendered.push(o); },
        prompt: () => {},
      },
    },
  };
});
afterEach(() => {
  delete window.google;
  window.sessionStorage.clear();
  window.history.replaceState(null, "", "/");
});

describe("GoogleSignIn", () => {
  it("looks like our button: a labelled pill of ours, with Google's real button laid invisibly over it", async () => {
    render(<GoogleSignIn />);
    const pill = screen.getByText("Continue with Google").closest("div")!;
    expect(pill.className).toContain("btn");
    await waitFor(() => expect(gis.rendered.length).toBe(1));
    expect(gis.rendered[0].shape).toBe("pill");
    // Google's own button is present for the click, unseen by the eye.
    const slot = screen.getByLabelText("Continue with Google");
    expect(slot.parentElement!.style.opacity).toBe("0");
  });

  it("after a Google sign-in, finishes the trip the reader was on — via onboarding for a new reader", async () => {
    window.history.replaceState(null, "", "/signin?next=%2Fplus");
    session.signInWithGoogle.mockResolvedValue({ session: { token: "t", userId: "u", email: "a@b.c" }, needsProfile: true });
    render(<GoogleSignIn />);
    await waitFor(() => expect(gis.cb).not.toBeNull());
    await act(async () => { gis.cb!({ credential: "cred" }); });
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/onboarding?next=%2Fplus"));
  });

  it("a returning reader goes straight back", async () => {
    window.sessionStorage.setItem("prism.next.v1", "/plus?from=ask-limit");
    session.signInWithGoogle.mockResolvedValue({ session: { token: "t", userId: "u", email: "a@b.c" }, needsProfile: false });
    render(<GoogleSignIn />);
    await waitFor(() => expect(gis.cb).not.toBeNull());
    await act(async () => { gis.cb!({ credential: "cred" }); });
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/plus?from=ask-limit"));
  });
});
