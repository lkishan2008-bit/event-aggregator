"use client";

import { useMemo, useState, useSyncExternalStore } from "react";
import EventCard from "@/components/EventCard";
import { CATEGORIES, EventItem, isThisWeekend } from "@/lib/events";

const subscribe = () => () => {};
let clientNow: number | null = null;
const getClientNow = () => (clientNow ??= Date.now());

export default function EventFeed({ events }: { events: EventItem[] }) {
  const [category, setCategory] = useState<string>("all");
  const [freeOnly, setFreeOnly] = useState(false);
  const [weekendOnly, setWeekendOnly] = useState(false);
  const [query, setQuery] = useState("");
  // read the clock only in the browser (null while rendering on the server)
  const now = useSyncExternalStore(subscribe, getClientNow, () => null);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return events
      .filter((e) => category === "all" || e.category === category)
      .filter((e) => !freeOnly || e.priceAmount === 0)
      .filter((e) => !weekendOnly || (now !== null && isThisWeekend(e, now)))
      .filter((e) => !q || e.title.toLowerCase().includes(q) || e.venue.toLowerCase().includes(q))
      .sort((a, b) => a.startUtc.localeCompare(b.startUtc));
  }, [events, category, freeOnly, weekendOnly, query, now]);

  const chip = (active: boolean) =>
    `shrink-0 rounded-full border px-3.5 py-1.5 text-sm font-medium transition ${
      active ? "border-accent bg-accent text-white" : "border-line bg-white text-night hover:border-muted"
    }`;

  return (
    <section>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search hackathons, fests, venues"
        className="mb-3 w-full rounded-xl border border-line bg-white px-4 py-2.5 text-sm outline-none focus:border-ink"
      />

      <div className="no-scrollbar -mx-4 mb-4 flex gap-2 overflow-x-auto px-4">
        <button className={chip(weekendOnly)} onClick={() => setWeekendOnly(!weekendOnly)}>This weekend</button>
        <button className={chip(freeOnly)} onClick={() => setFreeOnly(!freeOnly)}>Free</button>
        {CATEGORIES.map((c) => (
          <button key={c.key} className={chip(category === c.key)} onClick={() => setCategory(c.key)}>
            {c.label}
          </button>
        ))}
      </div>

      <div className="space-y-4">
        {visible.map((e) => (
          <EventCard key={e.id} event={e} weekend={now !== null && isThisWeekend(e, now)} />
        ))}
        {visible.length === 0 && (
          <p className="rounded-2xl border border-dashed border-line px-4 py-10 text-center text-sm text-muted">
            No events match these filters. Try removing one.
          </p>
        )}
      </div>
    </section>
  );
}