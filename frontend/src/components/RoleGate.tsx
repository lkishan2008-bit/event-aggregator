"use client";

import Link from "next/link";
import { ReactNode } from "react";
import { useSession, User } from "@/lib/auth";

/** Shows the page only to logged-in users with one of the given roles. */
export default function RoleGate({ roles, children }: { roles: User["role"][]; children: (user: User) => ReactNode }) {
  const session = useSession();

  if (!session) {
    return (
      <main className="mx-auto max-w-md px-4 pt-10 md:pt-16">
        <h1 className="font-display text-2xl font-bold text-night">Log in first</h1>
        <p className="mt-2 text-sm text-muted">You need to be logged in to see this page.</p>
        <Link href="/login" className="mt-6 inline-block rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-white">Log in</Link>
      </main>
    );
  }
  if (!roles.includes(session.user.role)) {
    return (
      <main className="mx-auto max-w-md px-4 pt-10 md:pt-16">
        <h1 className="font-display text-2xl font-bold text-night">Not available</h1>
        <p className="mt-2 text-sm text-muted">This page is only for {roles.join(" or ")} accounts.</p>
        <Link href="/" className="mt-6 inline-block rounded-full border border-line bg-white px-5 py-2.5 text-sm font-medium text-night">Back to events</Link>
      </main>
    );
  }
  return <>{children(session.user)}</>;
}