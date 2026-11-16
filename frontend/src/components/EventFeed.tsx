"use client";

import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import EventCard from "@/components/EventCard";
import { CATEGORIES, EventItem, fetchEvents, isThisWeekend } from "@/lib/events";

const subscribe = () => () => { };
let clientNow: number | null = null;
const getClientNow = () => (clientNow ??= Date.now());

export default function EventFeed() {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [category, setCategory] = useState<string>("all");
  const [freeOnly, setFreeOnly] = useState(false);
  const [weekendOnly, setWeekendOnly] = useState(false);
  const [query, setQuery] = useState("");
  // read the clock only in the browser (null while rendering on the server)
  const now = useSyncExternalStore(subscribe, getClientNow, () => null);

  useEffect(() => {
    let cancelled = false;
    fetchEvents()
      .then((list) => { if (!cancelled) { setEvents(list); setStatus("ready"); } })
      .catch(() => { if (!cancelled) setStatus("error"); });
    return () => { cancelled = true; };
  }, []);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return events
      .filter((e) => category === "all" || e.category === category)
      .filter((e) => !freeOnly || e.is_free)
      .filter((e) => !weekendOnly || (now !== null && isThisWeekend(e, now)))
      .filter((e) => !q || e.title.toLowerCase().includes(q) || (e.venue?.name ?? "").toLowerCase().includes(q))
      .sort((a, b) => a.start_utc.localeCompare(b.start_utc));
  }, [events, category, freeOnly, weekendOnly, query, now]);

  const chip = (active: boolean) =>
    `shrink-0 rounded-full border px-3.5 py-1.5 text-sm font-medium transition ${active ? "border-accent bg-accent text-white" : "border-line bg-white text-night hover:border-muted"
    }`;

  return (
    <section>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search hackathons, fests, venues"
        className="mb-3 w-full rounded-xl border border-line bg-white px-4 py-2.5 text-sm outline-none focus:border-ink md:max-w-xl" />

      <div className="no-scrollbar -mx-4 mb-4 flex gap-2 overflow-x-auto px-4 md:mx-0 md:flex-wrap md:px-0">        <button className={chip(weekendOnly)} onClick={() => setWeekendOnly(!weekendOnly)}>This weekend</button>
        <button className={chip(freeOnly)} onClick={() => setFreeOnly(!freeOnly)}>Free</button>
        {CATEGORIES.map((c) => (
          <button key={c.key} className={chip(category === c.key)} onClick={() => setCategory(c.key)}>
            {c.label}
          </button>
        ))}
      </div>

      {status === "loading" && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => <div key={i} className="h-72 animate-pulse rounded-2xl bg-line/60" />)}
        </div>
      )}

      {status === "error" && (
        <p className="rounded-2xl border border-line bg-white px-4 py-10 text-center text-sm text-muted">
          Couldn&apos;t load events. Check that the backend is running on port 5000.
        </p>
      )}

      {status === "ready" && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {visible.map((e) => (
            <EventCard key={e.id} event={e} weekend={now !== null && isThisWeekend(e, now)} />
          ))}
          {visible.length === 0 && (
            <p className="col-span-full rounded-2xl border border-dashed border-line px-4 py-10 text-center text-sm text-muted">              No events match these filters. Try removing one.
            </p>
          )}
        </div>
      )}
    </section>
  );
}