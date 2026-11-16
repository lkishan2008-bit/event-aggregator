"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import EventCard from "@/components/EventCard";
import RoleGate from "@/components/RoleGate";
import { EventItem } from "@/lib/events";
import { getSavedEvents, useSavedIds } from "@/lib/saved";

function SavedList() {
  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [error, setError] = useState("");
  const ids = useSavedIds(); // re-filter when something is unsaved on this page

  useEffect(() => {
    let cancelled = false;
    getSavedEvents()
      .then((list) => { if (!cancelled) setEvents(list); })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, []);

  if (error) return <p className="rounded-2xl border border-line bg-white px-4 py-10 text-center text-sm text-muted">{error}</p>;
  if (!events) return <div className="h-48 animate-pulse rounded-2xl bg-line/60" />;
  const shown = ids ? events.filter((e) => ids.has(e.id)) : events;
  if (shown.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-line px-4 py-10 text-center text-sm text-muted">
        <p>Nothing saved yet. Tap the bookmark on any event to keep it here.</p>
        <Link href="/" className="mt-4 inline-block rounded-full bg-accent px-5 py-2.5 font-medium text-white">Find events</Link>
      </div>
    );
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {shown.map((e) => <EventCard key={e.id} event={e} weekend={false} />)}
    </div>
  );
}

export default function SavedPage() {
  return (
    <RoleGate roles={["student", "organizer", "admin"]}>
      {() => (
        <main className="mx-auto max-w-6xl px-4 pt-6 md:px-6 md:pt-10">
          <h1 className="font-display text-3xl font-bold text-night">Saved</h1>
          <p className="mb-5 mt-1 text-sm text-muted">Events you bookmarked. Finished events drop off automatically.</p>
          <SavedList />
        </main>
      )}
    </RoleGate>
  );
}