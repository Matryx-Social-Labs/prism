"use client";

/**
 * Every /admin page sits inside this: it asks the API whether this account may
 * be here before anything renders, and hands the session and email to the page
 * through context. The API checks again on every call (api/deps.
 * require_admin_user) — this is what the reader sees, not what protects the data.
 *
 * Styled as the labeller workspace is: rules and type, no cards, mono only for
 * counts and times (DESIGN.md, 2026-09-23 labeller entry).
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";

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

  return (
    <main className="mx-auto min-h-dvh w-full max-w-[1100px] px-5 pb-24 pt-6 sm:px-8">
      {state === "checking" && <p className="sr-only">Checking your access</p>}
      {state === "signed-out" && (
        <Notice text="Sign in with a founder account to open the dashboard.">
          <Link href="/signin?next=/admin" className="btn btn-primary mt-6">
            Sign in
          </Link>
        </Notice>
      )}
      {state === "forbidden" && <Notice text="This area is for Prism's founders." />}
      {state === "error" && <Notice text="The dashboard could not reach the API. Reload to try again." />}
      {state === "ok" && session && (
        <AdminContext.Provider value={{ session, email }}>
          <nav aria-label="Admin" className="flex flex-wrap items-baseline gap-x-5 gap-y-2 border-b pb-3" style={{ borderColor: "var(--line)" }}>
            {ADMIN_NAV.map((item) => {
              const current = item.href === "/admin" ? pathname === "/admin" : pathname?.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={current ? "page" : undefined}
                  className="text-[14px] font-semibold underline-offset-4 hover:underline"
                  style={{ color: current ? "var(--accent)" : "var(--ink-2)" }}
                >
                  {item.label}
                </Link>
              );
            })}
            <span className="ml-auto font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
              {email}
            </span>
          </nav>
          {children}
        </AdminContext.Provider>
      )}
    </main>
  );
}

function Notice({ text, children }: { text: string; children?: React.ReactNode }) {
  return (
    <div className="mt-10">
      <h1 className="text-[27px] leading-tight" style={{ fontFamily: "var(--font-display), serif" }}>
        Prism admin
      </h1>
      <p className="mt-3 text-[15px]" style={{ color: "var(--ink-2)" }}>
        {text}
      </p>
      {children}
    </div>
  );
}

/** A page heading and its sections, shared by every admin page. */
export function AdminTitle({ children }: { children: React.ReactNode }) {
  return (
    <h1 className="mt-8 text-[27px] leading-tight" style={{ fontFamily: "var(--font-display), serif" }}>
      {children}
    </h1>
  );
}

export function AdminSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-10">
      <h2 className="mb-3 text-[17px] font-semibold">{title}</h2>
      {children}
    </section>
  );
}

/** A row action: accent for the usual step, ink-2 for the one to think about. */
export function TextButton({ onClick, muted, children }: { onClick: () => void; muted?: boolean; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="min-h-[44px] text-[14px] font-semibold underline-offset-4 hover:underline"
      style={{ color: muted ? "var(--ink-2)" : "var(--accent)" }}
    >
      {children}
    </button>
  );
}

/** An empty state: what would be here. */
export function Quiet({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[15px]" style={{ color: "var(--ink-2)" }}>
      {children}
    </p>
  );
}
