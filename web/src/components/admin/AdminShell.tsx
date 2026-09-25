"use client";

/**
 * Every /admin page sits inside this: it asks the API whether this account may
 * be here before anything renders, and hands the session and email to the page
 * through context. The API checks again on every call (api/deps.
 * require_admin_user) — this is what the reader sees, not what protects the data.
 *
 * Until the API says yes the page is one of four access states on a bare bar
 * (the brand, an "Admin" badge, the theme): checking, signed out, not on the
 * founders' list, or the API could not be reached. The chrome after that is
 * AdminFrame (below); mono only for counts, times, codes and the email.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useId, useRef, useState } from "react";

import { Brand } from "@/components/Brand";
import { SectionHead } from "@/components/SectionHead";
import { ThemeToggle } from "@/components/ThemeToggle";

import { AdminError, fetchAdminMe } from "@/lib/admin";
import { useSession, type Session } from "@/lib/session";

import { istClock } from "./AuditItem";
import { dayLabel } from "./charts/format";

interface Admin {
  session: Session;
  email: string;
}

const AdminContext = createContext<Admin | null>(null);

/** The signed-in founder. Only callable under AdminShell, which renders its
 *  children only once the API has said yes. */
export function useAdmin(): Admin {
  const admin = useContext(AdminContext);
  if (!admin) throw new Error("useAdmin outside AdminShell");
  return admin;
}

export const ADMIN_NAV: ReadonlyArray<{ href: string; label: string }> = [
  { href: "/admin", label: "Overview" },
  { href: "/admin/coverage", label: "Coverage" },
  { href: "/admin/labellers", label: "Labellers" },
  { href: "/admin/batches", label: "Batches" },
  { href: "/admin/people", label: "People" },
  { href: "/admin/controls", label: "Controls" },
  { href: "/admin/audit", label: "Audit" },
];

export type AccessState = "checking" | "signed-out" | "forbidden" | "error";

export function AdminShell({ children }: { children: React.ReactNode }) {
  const session = useSession();
  const pathname = usePathname();
  // useSession reads storage in an effect, so its first value is null for
  // everyone; without this a founder would see "Sign in" flash first.
  const [mounted, setMounted] = useState(false);
  const [state, setState] = useState<AccessState | "ok">("checking");
  const [email, setEmail] = useState("");
  const [failure, setFailure] = useState<{ status: number; at: string } | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (!mounted) return;
    if (!session) {
      setState("signed-out");
      return;
    }
    let live = true;
    setState("checking");
    fetchAdminMe(session)
      .then((me) => {
        if (!live) return;
        setEmail(me.email);
        setState("ok");
      })
      .catch((e: unknown) => {
        if (!live) return;
        const status = e instanceof AdminError ? e.status : 0;
        setFailure({ status, at: new Date().toISOString() });
        setState(status === 401 ? "signed-out" : status === 403 ? "forbidden" : "error");
      });
    return () => {
      live = false;
    };
  }, [mounted, session, attempt]);

  if (state === "ok" && session) {
    return (
      <AdminFrame session={session} email={email} path={pathname ?? ""}>
        {children}
      </AdminFrame>
    );
  }
  return <AdminAccess state={state === "ok" ? "checking" : state} email={session?.email} failure={failure} onRetry={() => setAttempt((n) => n + 1)} />;
}

const ACCESS: Record<AccessState, { title: string; body?: string }> = {
  checking: { title: "Checking access…" },
  "signed-out": { title: "Sign in with a founder account", body: "The admin opens for accounts on the founders' list." },
  forbidden: { title: "This area is for Prism's founders" },
  error: { title: "Prism's API could not be reached", body: "Nothing in the admin can load until it answers. Check the API status, then try again." },
};

/** The four ways in before the dashboard: each a title, a line, one way on. */
export function AdminAccess({
  state,
  email,
  failure,
  onRetry,
}: {
  state: AccessState;
  email?: string;
  failure?: { status: number; at: string } | null;
  onRetry: () => void;
}) {
  const { title, body } = ACCESS[state];
  return (
    <div className="min-h-dvh">
      <header className="flex h-[var(--masthead)] items-center gap-2 border-b px-[var(--gutter)] lg:h-[var(--topbar)]" style={{ borderColor: "var(--line)" }}>
        <Brand size={20} />
        <span className="flex-1" />
        <span className="p-badge p-badge--outline">Admin</span>
        <ThemeToggle />
      </header>
      <div className="mx-auto grid max-w-[440px] gap-3.5 px-[var(--gutter)] py-[72px] lg:px-0 lg:py-[120px]" role={state === "checking" ? "status" : undefined}>
        <span className="p-count">/ADMIN</span>
        <h1 style={{ font: "var(--t-display-m)", letterSpacing: "var(--track-display)", textWrap: "balance" }}>{title}</h1>
        {state === "checking" && (
          <div className="admin-checking" aria-hidden>
            <i />
          </div>
        )}
        {state === "forbidden" && (
          <p style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
            You&apos;re signed in as <span className="font-mono text-[14px] [overflow-wrap:anywhere]">{email}</span>, which isn&apos;t on the list. Nothing here
            was shown to you.
          </p>
        )}
        {body && <p style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>{body}</p>}
        {state === "signed-out" && (
          <div>
            <Link href="/signin?next=/admin" className="p-btn p-btn--primary">
              Sign in
            </Link>
          </div>
        )}
        {state === "forbidden" && (
          <div>
            <Link href="/" className="p-btn p-btn--secondary">
              Back to Prism
            </Link>
          </div>
        )}
        {state === "error" && (
          <>
            <div>
              <button type="button" className="p-btn p-btn--secondary" onClick={onRetry}>
                Try again
              </button>
            </div>
            {failure && (
              <span className="p-count">
                ERROR REF · {failure.status ? `API-${failure.status}` : "NO ANSWER"} · {dayLabel(failure.at).toUpperCase()} {istClock(failure.at)} IST
              </span>
            )}
          </>
        )}
      </div>
    </div>
  );
}

/**
 * The admin's chrome (Design System v2 · AdminShell): a 220px sticky sidebar —
 * the brand, an "Admin" badge, the pages, the founder's email in mono — beside
 * the page. On a phone it is a 52px bar (brand, badge, email) over a tab strip
 * of the pages that scrolls sideways, so every page stays one tap away.
 */
export function AdminFrame({ session, email, path, children }: Admin & { path: string; children: React.ReactNode }) {
  const nav = useRef<HTMLElement>(null);
  // On a phone the pages scroll sideways: bring the current one into view.
  useEffect(() => {
    nav.current?.querySelector('[aria-current="page"]')?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
  }, [path]);
  return (
    <AdminContext.Provider value={{ session, email }}>
      <div className="min-h-dvh lg:grid lg:grid-cols-[220px_minmax(0,1fr)]">
        {/* The rule runs the page's full height; the sidebar sticks inside it. */}
        <div className="border-b lg:border-b-0 lg:border-r" style={{ borderColor: "var(--line)" }}>
          <div className="lg:sticky lg:top-0 lg:grid lg:max-h-dvh lg:content-start lg:gap-4 lg:overflow-y-auto lg:px-3 lg:py-[18px]">
            <div className="flex h-[52px] min-w-0 items-center gap-2 px-[var(--gutter)] lg:h-auto lg:px-2">
              <Brand size={20} />
              <span className="p-badge p-badge--outline">Admin</span>
              <span className="min-w-0 flex-1 truncate text-right font-mono text-[11px] lg:hidden" style={{ color: "var(--ink-3)" }}>
                {email}
              </span>
            </div>
            <nav ref={nav} aria-label="Admin" className="admin-nav p-hide-scroll flex overflow-x-auto px-[var(--gutter)] lg:grid lg:gap-0.5 lg:overflow-visible lg:px-0">
              {ADMIN_NAV.map((item) => {
                const current = item.href === "/admin" ? path === "/admin" : path.startsWith(item.href);
                return (
                  <Link key={item.href} href={item.href} aria-current={current ? "page" : undefined}>
                    {item.label}
                  </Link>
                );
              })}
            </nav>
            <span className="hidden truncate px-2.5 font-mono text-[11px] lg:block" style={{ color: "var(--ink-3)" }}>
              {email}
            </span>
          </div>
        </div>
        <div className="grid min-w-0 content-start gap-5 px-[var(--gutter)] pb-8 pt-4 lg:gap-6 lg:px-8 lg:pb-14 lg:pt-7">{children}</div>
      </div>
    </AdminContext.Provider>
  );
}

/** A page's name: display-m on a phone, display-l beside the sidebar. */
export function AdminTitle({ children }: { children: React.ReactNode }) {
  return <h1 className="admin-title">{children}</h1>;
}

/** A page's head: its name, a mono provenance line under it, controls at the right. */
export function AdminHead({ title, line, children }: { title: string; line?: string | null; children?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="min-w-0 flex-[1_1_280px]">
        <AdminTitle>{title}</AdminTitle>
        {line && <p className="p-count mt-1.5 whitespace-normal">{line}</p>}
      </div>
      {children}
    </div>
  );
}

/** A section under the 3px ink rule (SectionHead): `sub` is a mono provenance
 *  strip ("3 of 5 on"), `hint` a line of prose, `right` sits at its end. */
export function AdminSection({
  title,
  sub,
  hint,
  right,
  children,
}: {
  title: string;
  sub?: string;
  hint?: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}) {
  const id = useId();
  return (
    <section className="grid min-w-0 content-start gap-2.5" aria-labelledby={id}>
      <SectionHead id={id} title={title} sub={sub} hint={hint} right={right} />
      {children}
    </section>
  );
}

/** An empty list: what would be here. */
export function Quiet({ children }: { children: React.ReactNode }) {
  return (
    <p className="py-2 text-[15px]" style={{ color: "var(--ink-2)" }}>
      {children}
    </p>
  );
}
