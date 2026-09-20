"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
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

export function GoogleSignIn({ oneTap = false }: { oneTap?: boolean }) {
  const router = useRouter();
  const slot = useRef<HTMLDivElement>(null);
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
              router.replace(needsProfile ? "/onboarding" : "/feed");
            })
            .catch((e: Error) => setError(e.message));
        },
      });
      window.google.accounts.id.renderButton(slot.current, { type: "standard", theme: "outline", size: "large", shape: "pill", text: "continue_with", width: 320, logo_alignment: "left" });
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
    <div className="flex flex-col items-center gap-2">
      <div ref={slot} aria-label="Continue with Google" />
      {error && <p className="text-[13px]" style={{ color: "var(--danger)" }}>{error}</p>}
    </div>
  );
}
