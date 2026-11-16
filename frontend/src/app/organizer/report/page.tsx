"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import RoleGate from "@/components/RoleGate";
import { apiFetch } from "@/lib/auth";
import { EventItem, formatTimeRange } from "@/lib/events";

type Row = { name: string; count: number };
type Report = {
  event: EventItem;
  generated_at: string;
  totals: { registered: number; checked_in: number; attendance_rate: number; cancelled: number; paid_tickets: number; revenue: number; currency: string };
  institutions: Row[];
  cities: Row[];
  arrivals_by_hour: { hour: string; count: number }[];
  registrations_by_day: { day: string; count: number }[];
};

const money = (n: number, currency: string) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 font-display text-3xl font-bold text-night">{value}</p>
      {hint && <p className="text-xs text-muted">{hint}</p>}
    </div>
  );
}

/** Simple horizontal bars (no chart library needed; prints cleanly). */
function Bars({ title, rows, empty }: { title: string; rows: Row[]; empty: string }) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <section className="break-inside-avoid rounded-2xl border border-line bg-white p-5">
      <h2 className="mb-3 font-display text-lg font-bold text-night">{title}</h2>
      {rows.length === 0 ? <p className="text-sm text-muted">{empty}</p> : (
        <ul className="space-y-2">
          {rows.map((r) => (
            <li key={r.name} className="grid grid-cols-[minmax(0,10rem)_1fr_2.5rem] items-center gap-3 text-sm">
              <span className="truncate text-night">{r.name}</span>
              <span className="h-3 overflow-hidden rounded-full bg-line">
                <span className="block h-full rounded-full bg-accent print:bg-night" style={{ width: `${(r.count / max) * 100}%` }} />
              </span>
              <span className="text-right font-medium text-night">{r.count}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ReportView() {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const id = new URLSearchParams(window.location.search).get("event");
    if (!id) {
      Promise.resolve().then(() => { if (!cancelled) setError("No event chosen. Open the report from your events list."); });
      return () => { cancelled = true; };
    }
    apiFetch(`/api/organizer/events/${id}/report`)
      .then((d) => { if (!cancelled) setReport(d); })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, []);

  if (error) return <p className="rounded-2xl border border-line bg-white px-4 py-10 text-center text-sm text-muted">{error}</p>;
  if (!report) return <div className="h-64 animate-pulse rounded-2xl bg-line/60" />;

  const { event, totals: t } = report;
  const { day, time } = formatTimeRange(event);
  const generated = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(report.generated_at));

  return (
    <div className="space-y-5">
      <header className="rounded-2xl bg-night p-6 text-white print:bg-white print:p-0 print:text-night">
        <p className="text-xs uppercase tracking-wide text-white/60 print:text-muted">Sponsor report</p>
        <h1 className="mt-1 font-display text-3xl font-bold">{event.title}</h1>
        <p className="mt-2 text-sm text-white/80 print:text-muted">
          {day} {"\u00b7"} {time} {"\u00b7"} {event.venue?.name}, {event.venue?.city}
        </p>
        <p className="text-sm text-white/80 print:text-muted">
          Organized by {event.organizer?.name}{event.organizer?.verified_domain ? ` (verified @${event.organizer.verified_domain})` : ""}
        </p>
      </header>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Registered" value={t.registered.toLocaleString("en-IN")} hint={t.cancelled ? `${t.cancelled} cancelled` : undefined} />
        <Stat label="Checked in" value={t.checked_in.toLocaleString("en-IN")} hint="scanned at the gate" />
        <Stat label="Attendance" value={`${t.attendance_rate}%`} hint="of registered people came" />
        <Stat label="Ticket sales" value={money(t.revenue, t.currency)} hint={`${t.paid_tickets} paid tickets`} />
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <Bars title="Where attendees come from" rows={report.institutions} empty="No registrations yet." />
        <Bars title="Attendee cities" rows={report.cities} empty="No registrations yet." />
        <Bars title="Arrivals by hour" rows={report.arrivals_by_hour.map((a) => ({ name: a.hour, count: a.count }))} empty="No check-ins yet." />
        <Bars title="Registrations by day" rows={report.registrations_by_day.map((d) => ({ name: d.day, count: d.count }))} empty="No registrations yet." />
      </div>

      <p className="text-xs text-muted">
        Generated {generated}. Check-ins are counted from unique QR passes scanned at the entrance; ticket sales count only payments verified with Razorpay.
      </p>
    </div>
  );
}

export default function ReportPage() {
  return (
    <RoleGate roles={["organizer", "admin"]}>
      {() => (
        <main className="mx-auto max-w-4xl px-4 pt-6 md:px-6 md:pt-10 print:max-w-none print:p-0">
          <div className="mb-4 flex items-center justify-between print:hidden">
            <Link href="/organizer" className="text-sm text-muted hover:text-night">{"\u2190"} Your events</Link>
            <button onClick={() => window.print()} className="rounded-full bg-accent px-5 py-2 text-sm font-medium text-white hover:bg-accent-dark">
              Print / Save as PDF
            </button>
          </div>
          <ReportView />
        </main>
      )}
    </RoleGate>
  );
}