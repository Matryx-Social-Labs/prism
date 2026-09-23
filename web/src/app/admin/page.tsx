"use client";

import { AdminSection, AdminTitle, useAdmin } from "@/components/admin/AdminShell";

export default function AdminOverview() {
  const { email } = useAdmin();
  return (
    <>
      <AdminTitle>Overview</AdminTitle>
      <AdminSection title="Signed in">
        <p className="font-mono text-[12px]" style={{ color: "var(--ink-2)" }}>
          {email}
        </p>
      </AdminSection>
    </>
  );
}
