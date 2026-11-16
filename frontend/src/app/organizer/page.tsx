"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import RoleGate from "@/components/RoleGate";
import StatusBadge from "@/components/StatusBadge";
import OrganizerFeeds from "@/components/OrganizerFeeds";
import VerifyOrganizer from "@/components/VerifyOrganizer";
import { apiFetch } from "@/lib/auth";
import { EventItem, formatEventTime } from "@/lib/events";

function MyEvents() {
  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    apiFetch("/api/organizer/events")
      .then((d) => { if (!cancelled) setEvents(d.events); })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, []);

  if (error) return <p className="rounded-2xl border border-line bg-white px-4 py-10 text-center text-sm text-muted">{error}</p>;
  if (!events) return <div className="h-40 animate-pulse rounded-2xl bg-line/60" />;
  if (events.length === 0) {
    return (
      <p className="rounded-2xl border border-dashed border-line px-4 py-10 text-center text-sm text-muted">
        You haven&apos;t submitted any events yet.
      </p>
    );
  }

  return (
    <ul className="divide-y divide-line rounded-2xl border border-line bg-white">
      {events.map((e) => (
        <li key={e.id} className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="truncate font-medium text-night">{e.title}</p>
            <p className="text-xs text-muted">{formatEventTime(e)} {"\u00b7"} {e.venue?.name}</p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <span className="text-xs text-muted">{e.going} going</span>
            <StatusBadge status={e.status} />
            {e.status === "approved" && <Link href={`/events/${e.id}`} className="text-sm font-medium text-night underline">View</Link>}
            {e.status === "approved" && (
              <Link href={`/organizer/checkin?event=${e.id}`} className="rounded-full bg-night px-3 py-1 text-xs font-medium text-white">Check-in</Link>
            )}
            {e.status === "approved" && (
              <Link href={`/organizer/report?event=${e.id}`} className="rounded-full border border-line px-3 py-1 text-xs font-medium text-night">Report</Link>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function OrganizerPage() {
  return (
    <RoleGate roles={["organizer", "admin"]}>
      {(user) => (
        <main className="mx-auto max-w-4xl px-4 pt-6 md:px-6 md:pt-10">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-sm text-muted">{user.name}</p>
              <h1 className="font-display text-3xl font-bold text-night">Your events</h1>
            </div>
            <Link href="/organizer/new" className="rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-white hover:bg-accent-dark">
              + Submit an event
            </Link>
          </div>
          <VerifyOrganizer />
          <OrganizerFeeds />
          <p className="mb-4 text-sm text-muted">New events from unverified organizers are checked by an admin before they appear in the feed.</p>
          <MyEvents />
        </main>
      )}
    </RoleGate>
  );
}