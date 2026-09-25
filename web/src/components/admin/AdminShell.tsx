"use client";

/**
 * Every /admin page sits inside this: it asks the API whether this account may
 * be here before anything renders, and hands the session and email to the page
 * through context. The API checks again on every call (api/deps.
 * require_admin_user) — this is what the reader sees, not what protects the data.
 *
 * The chrome is AdminFrame (below); mono only for counts, times and the email.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useId, useRef, useState } from "react";

import { Brand } from "@/components/Brand";
import { SectionHead } from "@/components/SectionHead";

import { AdminError, fetchAdminMe } from "@/lib/admin";
import { useSession, type Session } from "@/lib/session";

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

type State = "checking" | "signed-out" | "forbidden" | "error" | "ok";

export function AdminShell({ children }: { children: React.ReactNode }) {
  const session = useSession();
  const pathname = usePathname();
  // useSession reads storage in an effect, so its first value is null for
  // everyone; without this a founder would see "Sign in" flash first.
  const [mounted, setMounted] = useState(false);
  const [state, setState] = useState<State>("checking");
  const [email, setEmail] = useState("");

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (!mounted) return;
    if (!session) {
      setState("signed-out");
      return;
    }
    let live = true;
    fetchAdminMe(session)
      .then((me) => {
        if (!live) return;
        setEmail(me.email);
        setState("ok");
      })
      .catch((e: unknown) => {
        if (!live) return;
        const status = e instanceof AdminError ? e.status : 0;
        setState(status === 401 ? "signed-out" : status === 403 ? "forbidden" : "error");
      });
    return () => {
      live = false;
    };
  }, [mounted, session]);

  if (state === "ok" && session) {
    return (
      <AdminFrame session={session} email={email} path={pathname ?? ""}>
        {children}
      </AdminFrame>
    );
  }
  return (
    <div className="mx-auto w-full max-w-[640px] px-5 pb-24 pt-16">
      {state === "checking" && <p className="sr-only">Checking your access</p>}
      {state === "signed-out" && (
        <Notice text="Sign in with a founder account to open the dashboard.">
          <Link href="/signin?next=/admin" className="p-btn p-btn--primary mt-6">
            Sign in
          </Link>
        </Notice>
      )}
      {state === "forbidden" && <Notice text="This area is for Prism's founders." />}
      {state === "error" && <Notice text="The dashboard could not reach the API. Reload to try again." />}
    </div>
  );
}

/**
 * The admin's chrome (Design System v2 · AdminShell): a 220px sticky sidebar —
 * the brand, an "Admin" badge, the pages, the founder's email in mono — beside
 * the page. On a phone the same sidebar folds into a top bar whose pages scroll
 * sideways, so every page stays one tap away. Hands the session down.
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
        <aside className="flex flex-wrap items-center gap-x-3 gap-y-2 px-3 pb-1 pt-3 lg:sticky lg:top-0 lg:max-h-dvh lg:flex-col lg:flex-nowrap lg:items-stretch lg:gap-4 lg:overflow-y-auto lg:py-[18px]">
          <div className="order-1 flex min-w-0 items-center gap-2 px-2">
            <Brand size={20} />
            <span className="p-badge p-badge--outline">Admin</span>
          </div>
          <span className="order-2 ml-auto min-w-0 truncate px-2 font-mono text-[11px] lg:order-3 lg:ml-0 lg:px-2.5" style={{ color: "var(--ink-3)" }}>
            {email}
          </span>
          <nav ref={nav} aria-label="Admin" className="p-hide-scroll order-3 -mx-3 flex w-[calc(100%+24px)] gap-0.5 overflow-x-auto px-3 lg:order-2 lg:mx-0 lg:grid lg:w-auto lg:overflow-visible lg:px-0">
            {ADMIN_NAV.map((item) => {
              const current = item.href === "/admin" ? path === "/admin" : path.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={current ? "page" : undefined}
                  className="flex min-h-[44px] shrink-0 items-center whitespace-nowrap rounded-[var(--r-md)] px-2.5 no-underline hover:bg-[var(--sunken)] lg:min-h-0 lg:py-2.5"
                  style={{
                    font: `${current ? 600 : 500} 14.5px/1 var(--font-read)`,
                    background: current ? "var(--accent-soft)" : undefined,
                    color: current ? "var(--accent)" : "var(--ink-2)",
                  }}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>
        </div>
        <div className="min-w-0 px-4 pb-12 pt-5 sm:px-6 lg:px-8 lg:pt-6">{children}</div>
      </div>
    </AdminContext.Provider>
  );
}

function Notice({ text, children }: { text: string; children?: React.ReactNode }) {
  return (
    <div>
      <h1 style={{ font: "var(--t-display-l)", letterSpacing: "var(--track-display)" }}>Prism admin</h1>
      <p className="mt-3 text-[15px]" style={{ color: "var(--ink-2)" }}>
        {text}
      </p>
      {children}
    </div>
  );
}

/** A page heading and its sections, shared by every admin page. */
export function AdminTitle({ children }: { children: React.ReactNode }) {
  return <h1 style={{ font: "var(--t-display-l)", letterSpacing: "var(--track-display)" }}>{children}</h1>;
}

/** A section under the 3px ink rule (SectionHead): `sub` is a mono provenance
 *  strip ("3 of 5 on"), `hint` a line of prose. */
export function AdminSection({ title, sub, hint, children }: { title: string; sub?: string; hint?: string; children: React.ReactNode }) {
  const id = useId();
  return (
    <section className="mt-8" aria-labelledby={id}>
      <SectionHead id={id} title={title} sub={sub} hint={hint} />
      {children}
    </section>
  );
}

/** A row action: accent for the usual step, ink-2 for the one to think about. */
export function TextButton({ onClick, muted, children }: { onClick: () => void; muted?: boolean; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} className="p-btn p-btn--text" style={muted ? { color: "var(--ink-2)" } : undefined}>
      {children}
    </button>
  );
}

/** An empty state: what would be here. */
export function Quiet({ children }: { children: React.ReactNode }) {
  return (
    <p className="py-3 text-[15px]" style={{ color: "var(--ink-2)" }}>
      {children}
    </p>
  );
}
