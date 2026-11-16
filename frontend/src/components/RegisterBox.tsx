"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSession } from "@/lib/auth";
import { cancelRegistration, getMyRegistration, Registration, registerFor } from "@/lib/registrations";

/** The Register / You're going box on the event page. */
export default function RegisterBox({ eventId, onGoingChange }: { eventId: number; onGoingChange: (going: number) => void }) {
  const session = useSession();
  const [reg, setReg] = useState<Registration | null | undefined>(undefined); // undefined = still checking
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    getMyRegistration(eventId)
      .then((r) => { if (!cancelled) setReg(r); })
      .catch(() => { if (!cancelled) setReg(null); });
    return () => { cancelled = true; };
  }, [session, eventId]);

  const primary = "block w-full rounded-full bg-accent py-3 text-center text-sm font-medium text-white hover:bg-accent-dark disabled:opacity-60";

  if (!session) {
    return <Link href="/login" className={primary}>Log in to register</Link>;
  }
  if (reg === undefined) {
    return <div className="h-11 animate-pulse rounded-full bg-line/60" />;
  }

  async function act(kind: "register" | "cancel") {
    setBusy(true);
    setError("");
    try {
      const r = kind === "register" ? await registerFor(eventId) : await cancelRegistration(eventId);
      setReg(r.status === "registered" ? r : null);
      if (r.event) onGoingChange(r.event.going);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  if (reg) {
    return (
      <div className="space-y-2">
        <p className="rounded-xl bg-green-50 px-4 py-2.5 text-center text-sm font-medium text-green-800">✓ You&apos;re going</p>
        <Link href="/passes" className={primary}>View my pass</Link>
        <button onClick={() => act("cancel")} disabled={busy} className="w-full py-1 text-sm text-muted underline hover:text-night disabled:opacity-60">
          {busy ? "Cancelling…" : "Cancel registration"}
        </button>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <button onClick={() => act("register")} disabled={busy} className={primary}>
        {busy ? "Registering…" : "Register"}
      </button>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}