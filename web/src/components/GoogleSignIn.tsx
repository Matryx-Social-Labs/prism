"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Alert } from "@/components/ui";
import { afterSignIn, takeNext } from "@/lib/next";
import { saveSession, signInWithGoogle } from "@/lib/session";

/**
 * Continue with Google — OUR button, Google's OAuth token flow.
 *
 * Google's rendered "Sign in with Google" button cannot wear our style, and
 * it refuses the click when it is not visibly its own (it checks its own
 * visibility, so an overlay at opacity 0 is a dead button — that is what
 * broke sign-in on 2026-09-20). The token client has no button: our pill
 * calls `requestAccessToken()`, Google's account chooser opens, and the access
 * token goes to /api/v1/auth/google, which asks Google whose it is and checks
 * it was minted for our client id. Same session, same account, as a magic link.
 * Renders nothing — not even the "or" rule above it — until
 * NEXT_PUBLIC_GOOGLE_CLIENT_ID is set. A closed chooser is not an error: the
 * button simply comes back. Anything else says what happened and one way on.
 */
declare global {
  interface Window {
    google?: {
      accounts: {
        oauth2: {
          initTokenClient: (o: {
            client_id: string;
            scope: string;
            callback: (r: { access_token?: string; error?: string; error_description?: string }) => void;
            error_callback?: (e: { type: string; message?: string }) => void;
          }) => { requestAccessToken: (o?: { prompt?: string }) => void };
        };
      };
    };
  }
}

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";
const SCOPE = "openid email profile";
const GSI = "https://accounts.google.com/gsi/client";

function loadGsi(): Promise<void> {
  if (window.google?.accounts?.oauth2) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${GSI}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("Google could not be reached")), { once: true });
      return;
    }
    const s = document.createElement("script");
    s.src = GSI;
    s.async = true;
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Google could not be reached"));
    document.head.appendChild(s);
  });
}

function GoogleG() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden>
      <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.6l6.7-6.7C35.7 2.6 30.3 0 24 0 14.6 0 6.5 5.4 2.6 13.2l7.8 6.1C12.3 13.6 17.7 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4 7.1-10 7.1-17.5z" />
      <path fill="#FBBC05" d="M10.4 28.7A14.5 14.5 0 0 1 9.5 24c0-1.6.3-3.2.8-4.7l-7.8-6.1A24 24 0 0 0 0 24c0 3.9.9 7.5 2.6 10.8l7.8-6.1z" />
      <path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.5-5.8c-2.1 1.4-4.9 2.3-8.4 2.3-6.3 0-11.7-4.1-13.6-9.9l-7.8 6.1C6.5 42.6 14.6 48 24 48z" />
    </svg>
  );
}

export function GoogleSignIn() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const alive = useRef(true);
  useEffect(() => {
    // Warm the script so the first tap opens Google at once.
    loadGsi().catch(() => {});
    return () => { alive.current = false; };
  }, []);

  async function start() {
    setError(null);
    setBusy(true);
    try {
      await loadGsi();
      const client = window.google!.accounts.oauth2.initTokenClient({
        client_id: CLIENT_ID,
        scope: SCOPE,
        callback: (r) => {
          if (!r.access_token) {
            if (alive.current) { setBusy(false); if (r.error && r.error !== "access_denied") setError(r.error_description || "Google sign-in failed"); }
            return;
          }
          signInWithGoogle(r.access_token)
            .then(({ session, needsProfile }) => {
              saveSession(session);
              router.replace(afterSignIn(needsProfile, takeNext("/feed", new URLSearchParams(window.location.search).get("next"))));
            })
            .catch((e: Error) => { if (alive.current) { setError(e.message); setBusy(false); } });
        },
        // The reader closed the popup, or the browser blocked it.
        error_callback: (e) => { if (alive.current) { setBusy(false); if (e.type !== "popup_closed") setError(e.message || "Google sign-in could not open"); } },
      });
      client.requestAccessToken();
    } catch (e) {
      setBusy(false);
      setError(e instanceof Error ? e.message : "Google sign-in failed");
    }
  }

  if (!CLIENT_ID) return null;
  return (
    <>
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3" aria-hidden style={{ font: "500 13px/1 var(--font-read)", color: "var(--ink-3)" }}>
        <span className="h-px" style={{ background: "var(--line)" }} />
        or
        <span className="h-px" style={{ background: "var(--line)" }} />
      </div>
      <button type="button" onClick={start} disabled={busy} aria-busy={busy || undefined} className="p-btn p-btn--secondary p-btn--lg p-btn--block">
        {!busy && <GoogleG />}
        {busy ? "Opening Google…" : "Continue with Google"}
      </button>
      {error && (
        <Alert tone="error" title="Google sign-in did not finish">
          {sentence(error)} Try again, or use your email.
        </Alert>
      )}
    </>
  );
}

/** Google's and the API's messages arrive lower-case and unpunctuated ("token rejected by google"). */
function sentence(s: string): string {
  const t = s.trim();
  return t.charAt(0).toUpperCase() + t.slice(1) + (/[.!?]$/.test(t) ? "" : ".");
}
