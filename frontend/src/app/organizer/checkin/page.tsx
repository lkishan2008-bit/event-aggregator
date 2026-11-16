"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import QrScanner from "@/components/QrScanner";
import RoleGate from "@/components/RoleGate";
import { apiFetch } from "@/lib/auth";
import { checkIn, CheckinResult, CheckinStats, getCheckinStats } from "@/lib/checkin";
import { EventItem } from "@/lib/events";

const RESULT_STYLE: Record<CheckinResult["result"], string> = {
  ok: "bg-green-600 text-white",
  already: "bg-amber-400 text-night",
  cancelled: "bg-red-600 text-white",
  invalid: "bg-red-600 text-white",
  wrong_event: "bg-red-600 text-white",
  error: "bg-red-600 text-white",
};

const timeOf = (iso: string | null) =>
  iso ? new Intl.DateTimeFormat("en-IN", { hour: "numeric", minute: "2-digit" }).format(new Date(iso)) : "";

function Scanner({ eventId }: { eventId: number }) {
  const [stats, setStats] = useState<CheckinStats | null>(null);
  const [result, setResult] = useState<CheckinResult | null>(null);
  const [camera, setCamera] = useState(false);
  const [code, setCode] = useState("");

  const refresh = useCallback(() => {
    getCheckinStats(eventId).then(setStats).catch(() => {});
  }, [eventId]);

  // live numbers: refresh every 5 seconds (other volunteers may be scanning too)
  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => clearInterval(timer);
  }, [refresh]);

  const scan = useCallback(async (text: string) => {
    const r = await checkIn(eventId, text.trim());
    setResult(r);
    if (r.result === "ok") refresh();
  }, [eventId, refresh]);

  return (
    <div className="grid gap-6 md:grid-cols-[1fr_300px]">
      <div className="space-y-4">
        {result && (
          <div className={`rounded-2xl px-5 py-4 ${RESULT_STYLE[result.result]}`}>
            <p className="font-display text-2xl font-bold">
              {result.result === "ok" ? "\u2713 " : result.result === "already" ? "! " : "\u2715 "}{result.message}
            </p>
            {result.attendee && (
              <p className="mt-1 text-sm opacity-90">
                {result.attendee.name} {"\u00b7"} {result.attendee.email}
                {result.result === "already" && ` \u00b7 at ${timeOf(result.attendee.checked_in_at)}`}
              </p>
            )}
          </div>
        )}

        {camera ? (
          <>
            <QrScanner onScan={scan} />
            <button onClick={() => setCamera(false)} className="w-full rounded-full border border-line bg-white py-3 text-sm font-medium text-night">Stop camera</button>
          </>
        ) : (
          <button onClick={() => setCamera(true)} className="w-full rounded-full bg-accent py-4 text-base font-medium text-white hover:bg-accent-dark">
            Start scanning
          </button>
        )}

        <form
          onSubmit={(e) => { e.preventDefault(); if (code.trim()) { scan(code); setCode(""); } }}
          className="flex gap-2"
        >
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Or type / paste the pass code"
            className="min-w-0 flex-1 rounded-full border border-line bg-white px-4 py-2.5 text-sm outline-none focus:border-night"
          />
          <button className="rounded-full bg-night px-5 py-2.5 text-sm font-medium text-white">Check in</button>
        </form>
      </div>

      <aside className="h-fit space-y-4 rounded-2xl border border-line bg-white p-5">
        <div>
          <p className="text-sm text-muted">Checked in</p>
          <p className="font-display text-4xl font-bold text-night">
            {stats ? stats.checked_in : "\u2013"}<span className="text-xl text-muted"> / {stats ? stats.going : "\u2013"}</span>
          </p>
          {stats && stats.going > 0 && (
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-line">
              <div className="h-full bg-accent transition-all" style={{ width: `${(stats.checked_in / stats.going) * 100}%` }} />
            </div>
          )}
        </div>
        <div>
          <p className="mb-2 text-sm font-medium text-night">Latest arrivals</p>
          {stats?.recent.length ? (
            <ul className="space-y-1.5 text-sm">
              {stats.recent.map((a) => (
                <li key={a.registration_id} className="flex justify-between gap-2">
                  <span className="truncate text-night">{a.name}</span>
                  <span className="shrink-0 text-muted">{timeOf(a.checked_in_at)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted">No one yet.</p>
          )}
        </div>
      </aside>
    </div>
  );
}

function CheckinPage() {
  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [eventId, setEventId] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    apiFetch("/api/organizer/events")
      .then((d) => {
        if (cancelled) return;
        const live = (d.events as EventItem[]).filter((e) => e.status === "approved");
        setEvents(live);
        // /organizer/checkin?event=12 opens that event straight away
        const wanted = Number(new URLSearchParams(window.location.search).get("event"));
        setEventId(live.some((e) => e.id === wanted) ? wanted : live[0]?.id ?? null);
      })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, []);

  if (error) return <p className="rounded-2xl border border-line bg-white px-4 py-10 text-center text-sm text-muted">{error}</p>;
  if (!events) return <div className="h-40 animate-pulse rounded-2xl bg-line/60" />;
  if (events.length === 0 || eventId === null) {
    return (
      <p className="rounded-2xl border border-dashed border-line px-4 py-10 text-center text-sm text-muted">
        You have no approved events to check people into yet.
      </p>
    );
  }

  return (
    <>
      <select
        value={eventId}
        onChange={(e) => setEventId(Number(e.target.value))}
        className="mb-5 w-full rounded-full border border-line bg-white px-4 py-2.5 text-sm font-medium text-night md:w-auto"
      >
        {events.map((e) => <option key={e.id} value={e.id}>{e.title}</option>)}
      </select>
      <Scanner key={eventId} eventId={eventId} />
    </>
  );
}

export default function Page() {
  return (
    <RoleGate roles={["organizer", "admin"]}>
      {() => (
        <main className="mx-auto max-w-4xl px-4 pt-6 md:px-6 md:pt-10">
          <Link href="/organizer" className="text-sm text-muted hover:text-night">{"\u2190"} Your events</Link>
          <h1 className="mt-2 font-display text-3xl font-bold text-night">Gate check-in</h1>
          <p className="mb-5 mt-1 text-sm text-muted">Scan each attendee&apos;s QR pass. Each pass works only once.</p>
          <CheckinPage />
        </main>
      )}
    </RoleGate>
  );
}