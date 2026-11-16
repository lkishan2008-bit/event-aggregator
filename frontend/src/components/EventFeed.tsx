"use client";

import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import EventCard from "@/components/EventCard";
import { CATEGORIES, dayKey, EventItem, fetchEvents, isThisWeekend } from "@/lib/events";

const subscribe = () => () => {};
let clientNow: number | null = null;
const getClientNow = () => (clientNow ??= Date.now());

/** The next 7 days (in this browser's timezone): key + label like "Today", "Tomorrow", "Sat 21 Nov". */
function nextSevenDays(now: number) {
  return Array.from({ length: 7 }, (_, i) => {
    const d = now + i * 86_400_000;
    const label = i === 0 ? "Today" : i === 1 ? "Tomorrow"
      : new Intl.DateTimeFormat("en-IN", { weekday: "short", day: "numeric", month: "short" }).format(new Date(d));
    return { key: dayKey(d), label };
  });
}

export default function EventFeed() {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [view, setView] = useState<"week" | "all">("week");
  const [category, setCategory] = useState<string>("all");
  const [freeOnly, setFreeOnly] = useState(false);
  const [weekendOnly, setWeekendOnly] = useState(false);
  const [query, setQuery] = useState("");
  const [city, setCity] = useState("anywhere");
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
      .filter((e) => city === "anywhere" || e.venue?.city === city)
      .filter((e) => category === "all" || e.category === category)
      .filter((e) => !freeOnly || e.is_free)
      .filter((e) => view === "week" || !weekendOnly || (now !== null && isThisWeekend(e, now)))
      .filter((e) => !q || e.title.toLowerCase().includes(q) || (e.venue?.name ?? "").toLowerCase().includes(q))
      .sort((a, b) => a.start_utc.localeCompare(b.start_utc));
  }, [events, category, freeOnly, weekendOnly, query, now, view, city]);

  // cities that have events, busiest first
  const cities = useMemo(() => {
    const counts = new Map<string, number>();
    events.forEach((e) => e.venue && counts.set(e.venue.city, (counts.get(e.venue.city) ?? 0) + 1));
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [events]);

  // "This week": events grouped under each of the next 7 days
  const week = useMemo(() => {
    if (now === null) return [];
    return nextSevenDays(now).map((day) => ({ ...day, events: visible.filter((e) => dayKey(e.start_utc) === day.key) }));
  }, [visible, now]);
  const weekCount = week.reduce((n, d) => n + d.events.length, 0);

  const chip = (active: boolean) =>
    `shrink-0 rounded-full border px-3.5 py-1.5 text-sm font-medium transition ${
      active ? "border-accent bg-accent text-white" : "border-line bg-white text-night hover:border-muted"
    }`;
  const tab = (active: boolean) =>
    `rounded-full px-4 py-1.5 text-sm font-medium ${active ? "bg-night text-white" : "text-muted hover:text-night"}`;

  return (
    <section>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <select
          value={city}
          onChange={(e) => setCity(e.target.value)}
          aria-label="City"
          className="rounded-full border border-line bg-white px-4 py-2 text-sm font-medium text-night outline-none focus:border-ink"
        >
          <option value="anywhere">Anywhere</option>
          {cities.map(([c, n]) => <option key={c} value={c}>{c} ({n})</option>)}
        </select>
        <div className="flex gap-1 rounded-full border border-line bg-white p-1">
          <button className={tab(view === "week")} onClick={() => setView("week")}>This week</button>
          <button className={tab(view === "all")} onClick={() => setView("all")}>All upcoming</button>
        </div>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search hackathons, fests, venues"
          className="min-w-0 flex-1 rounded-xl border border-line bg-white px-4 py-2.5 text-sm outline-none focus:border-ink md:max-w-xl"
        />
      </div>

      <div className="no-scrollbar -mx-4 mb-4 flex gap-2 overflow-x-auto px-4 md:mx-0 md:flex-wrap md:px-0">
        {view === "all" && <button className={chip(weekendOnly)} onClick={() => setWeekendOnly(!weekendOnly)}>This weekend</button>}
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

      {status === "ready" && view === "week" && (
        <div className="space-y-6">
          {week.map((day) => (
            <div key={day.key}>
              <h2 className="mb-2 flex items-baseline gap-2 font-display text-lg font-bold text-night">
                {day.label}
                <span className="text-sm font-normal text-muted">
                  {day.events.length ? `${day.events.length} event${day.events.length > 1 ? "s" : ""}` : "nothing yet"}
                </span>
              </h2>
              {day.events.length > 0 && (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {day.events.map((e) => (
                    <EventCard key={e.id} event={e} weekend={now !== null && isThisWeekend(e, now)} />
                  ))}
                </div>
              )}
            </div>
          ))}
          {weekCount === 0 && (
            <p className="rounded-2xl border border-dashed border-line px-4 py-8 text-center text-sm text-muted">
              Nothing in the next 7 days matches. <button onClick={() => setView("all")} className="font-medium text-night underline">See all upcoming</button>
            </p>
          )}
        </div>
      )}

      {status === "ready" && view === "all" && (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {visible.map((e) => (
          <EventCard key={e.id} event={e} weekend={now !== null && isThisWeekend(e, now)} />
        ))}
        {visible.length === 0 && (
          <p className="col-span-full rounded-2xl border border-dashed border-line px-4 py-10 text-center text-sm text-muted">
            No events match these filters. Try removing one.
          </p>
        )}
      </div>
      )}
    </section>
  );
}