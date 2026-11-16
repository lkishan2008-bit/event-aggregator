"use client";

import Link from "next/link";
import { QRCodeSVG } from "qrcode.react";
import { useEffect, useState } from "react";
import RoleGate from "@/components/RoleGate";
import { formatTimeRange } from "@/lib/events";
import { getMyPasses, Registration } from "@/lib/registrations";

function PassCard({ reg }: { reg: Registration }) {
  const e = reg.event!;
  const { day, time } = formatTimeRange(e);
  return (
    <article className="overflow-hidden rounded-2xl bg-night text-white">
      <div className="flex flex-col gap-5 p-5 sm:flex-row sm:items-center">
        <div className="rounded-xl bg-white p-3 self-center">
          <QRCodeSVG value={reg.qr_token} size={148} level="M" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs uppercase tracking-wide text-white/60">Your pass</p>
          <h2 className="mt-1 font-display text-2xl font-bold leading-tight">{e.title}</h2>
          <p className="mt-2 text-sm text-white/80">{day}</p>
          <p className="text-sm text-white/80">{time}</p>
          {e.venue && <p className="mt-1 text-sm text-white/80">{e.venue.name}, {e.venue.city}</p>}
          <p className="mt-3 text-sm">
            {reg.checked_in_at
              ? <span className="text-green-400">✓ Checked in</span>
              : <span className="text-accent">● Show this QR code at the entrance</span>}
          </p>
        </div>
      </div>
      <div className="flex items-center justify-between border-t border-dashed border-white/20 px-5 py-3 text-xs text-white/60">
        <span>Pass #{reg.id}</span>
        <Link href={`/events/${e.id}`} className="font-medium text-white underline">Event details</Link>
      </div>
    </article>
  );
}

function Passes() {
  const [passes, setPasses] = useState<Registration[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    getMyPasses()
      .then((p) => { if (!cancelled) setPasses(p); })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, []);

  if (error) return <p className="rounded-2xl border border-line bg-white px-4 py-10 text-center text-sm text-muted">{error}</p>;
  if (!passes) return <div className="h-48 animate-pulse rounded-2xl bg-line/60" />;
  if (passes.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-line px-4 py-10 text-center text-sm text-muted">
        <p>No passes yet. Register for an event and your QR pass will appear here.</p>
        <Link href="/" className="mt-4 inline-block rounded-full bg-accent px-5 py-2.5 font-medium text-white">Find events</Link>
      </div>
    );
  }
  return <div className="grid gap-4 lg:grid-cols-2">{passes.map((r) => <PassCard key={r.id} reg={r} />)}</div>;
}

export default function PassesPage() {
  return (
    <RoleGate roles={["student", "organizer", "admin"]}>
      {() => (
        <main className="mx-auto max-w-4xl px-4 pt-6 md:px-6 md:pt-10">
          <h1 className="font-display text-3xl font-bold text-night">Your passes</h1>
          <p className="mb-5 mt-1 text-sm text-muted">Show the QR code at the event entrance to check in.</p>
          <Passes />
        </main>
      )}
    </RoleGate>
  );
}