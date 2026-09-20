"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { afterSignIn, takeNext } from "@/lib/next";
import { saveSession, signInWithGoogle } from "@/lib/session";

/**
 * Sign in with Google (Google Identity Services, ID-token mode). Renders
 * nothing until NEXT_PUBLIC_GOOGLE_CLIENT_ID is set, so the sign-in page is
 * complete without it. The credential goes to /api/v1/auth/google, which
 * verifies it and returns the same session a magic link does; the verified
 * email is the identity, so an existing link account is the same account.
 */
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (o: { client_id: string; callback: (r: { credential: string }) => void; ux_mode?: string; auto_select?: boolean; itp_support?: boolean }) => void;
          renderButton: (el: HTMLElement, o: Record<string, string | number>) => void;
          prompt: () => void;
        };
      };
    };
  }
}

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";

// Google's rendered button (an iframe) cannot be restyled, and the ID-token
// flow only works from Google's own button. So the reader sees OUR pill —
// the secondary button beside the primary "Email me a sign-in link" — and
// Google's real button sits over it at opacity 0, scaled to the pill's
// height, taking the click. Google's terms allow a custom look as long as
// the button says what it does and carries the G.
const GIS_HEIGHT = 40; // size: "large"

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

export function GoogleSignIn({ oneTap = false }: { oneTap?: boolean }) {
  const router = useRouter();
  const slot = useRef<HTMLDivElement>(null);
  const pill = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!CLIENT_ID || !slot.current) return;
    let cancelled = false;
    const boot = () => {
      if (cancelled || !window.google || !slot.current) return;
      window.google.accounts.id.initialize({
        client_id: CLIENT_ID,
        itp_support: true,
        callback: ({ credential }) => {
          signInWithGoogle(credential)
            .then(({ session, needsProfile }) => {
              saveSession(session);
              router.replace(afterSignIn(needsProfile, takeNext("/feed", new URLSearchParams(window.location.search).get("next"))));
            })
            .catch((e: Error) => setError(e.message));
        },
      });
      // Google's button is 40px tall; the pill is 48. Scale the invisible
      // button up to cover the pill, and size it to the pill's width.
      const width = pill.current?.clientWidth ?? 320;
      const scale = 48 / GIS_HEIGHT;
      window.google.accounts.id.renderButton(slot.current, {
        type: "standard", theme: "outline", size: "large", shape: "pill", text: "continue_with", logo_alignment: "left",
        // Google draws its button ~26px narrower than asked; ask for the difference.
        width: Math.min(400, Math.max(200, Math.round(width / scale) + 28)),
      });
      if (oneTap) window.google.accounts.id.prompt();
    };
    if (window.google) boot();
    else {
      const s = document.createElement("script");
      s.src = "https://accounts.google.com/gsi/client";
      s.async = true;
      s.defer = true;
      s.onload = boot;
      document.head.appendChild(s);
    }
    return () => { cancelled = true; };
  }, [router, oneTap]);

  if (!CLIENT_ID) return null;
  return (
    <div className="flex flex-col gap-2">
      <div className="relative">
        <div ref={pill} className="btn btn-secondary btn-lg w-full" aria-hidden>
          <GoogleG />
          Continue with Google
        </div>
        {/* Google's real button: over the pill, unseen, scaled to its height. */}
        <div className="absolute inset-0 flex items-center justify-center overflow-hidden rounded-full" style={{ opacity: 0, transform: `scale(${48 / GIS_HEIGHT})` }}>
          <div ref={slot} aria-label="Continue with Google" />
        </div>
      </div>
      {error && <p className="text-[13px]" style={{ color: "var(--danger)" }}>{error}</p>}
    </div>
  );
}
