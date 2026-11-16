"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import RegisterBox from "@/components/RegisterBox";
import ReportEvent from "@/components/ReportEvent";
import SaveButton from "@/components/SaveButton";
import { calendarUrl, directionsUrl, EventItem, fetchEvent, formatPrice, formatTimeRange, posterColor } from "@/lib/events";

export default function EventDetail({ id }: { id: string }) {
  const [event, setEvent] = useState<EventItem | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "missing" | "error">("loading");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchEvent(id)
      .then((e) => { if (!cancelled) { setEvent(e); setStatus(e ? "ready" : "missing"); } })
      .catch(() => { if (!cancelled) setStatus("error"); });
    return () => { cancelled = true; };
  }, [id]);

  async function share() {
    const url = window.location.href;
    try {
      if (navigator.share) await navigator.share({ title: event?.title, url });
      else { await navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 2000); }
    } catch {
      // user closed the share sheet
    }
  }

  const back = <Link href="/" className="text-sm text-muted hover:text-night">{"\u2190"} All events</Link>;

  if (status === "loading") {
    return (
      <main className="mx-auto max-w-4xl px-4 pt-6 md:px-6 md:pt-10">
        {back}
        <div className="mt-4 aspect-[16/9] animate-pulse rounded-2xl bg-line/60 md:aspect-[21/9]" />
      </main>
    );
  }

  if (status !== "ready" || !event) {
    return (
      <main className="mx-auto max-w-4xl px-4 pt-6 md:px-6 md:pt-10">
        {back}
        <p className="mt-6 rounded-2xl border border-line bg-white px-4 py-10 text-center text-sm text-muted">
          {status === "missing" ? "This event doesn't exist or isn't public yet." : "Couldn't load this event. Check that the backend is running."}
        </p>
      </main>
    );
  }

  const { day, time } = formatTimeRange(event);
  const maps = directionsUrl(event);
  const v = event.venue;

  return (
    <main className="mx-auto max-w-4xl px-4 pt-6 md:px-6 md:pt-10">
      {back}

      <div className="relative mt-4 flex aspect-[16/9] items-end overflow-hidden rounded-2xl p-5 md:aspect-[21/9] md:p-8" style={{ background: posterColor(event) }}>
        <div className="absolute left-4 top-4 flex gap-1.5 md:left-6 md:top-6">
          {event.is_free && <span className="rounded-full bg-accent px-2.5 py-0.5 text-xs font-medium text-white">Free</span>}
          <span className="rounded-full bg-white/20 px-2.5 py-0.5 text-xs font-medium capitalize text-white">{event.category}</span>
        </div>
        <h1 className="font-display text-3xl font-bold leading-tight text-white md:text-5xl">{event.title}</h1>
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-[1fr_320px]">
        {/* left: details */}
        <div className="space-y-6">
          <section className="space-y-4 rounded-2xl border border-line bg-white p-5 text-sm">
            <div>
              <p className="text-muted">When</p>
              <p className="mt-0.5 font-medium text-night">{day}</p>
              <p className="text-night">{time} <span className="text-muted">({event.timezone})</span></p>
            </div>
            {v && (
              <div>
                <p className="text-muted">Where</p>
                <p className="mt-0.5 font-medium text-night">{v.name}</p>
                <p className="text-night">{[v.address, v.city, v.country_code].filter(Boolean).join(", ")}</p>
              </div>
            )}
            {event.organizer && (
              <div>
                <p className="text-muted">Organized by</p>
                <p className="mt-0.5 font-medium text-night">
                  {event.organizer.name}
                  {event.organizer.verified_domain && (
                    <span className="ml-2 rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-800" title={`Verified with an @${event.organizer.verified_domain} email`}>
                      {"\u2713"} Verified {"\u00b7"} {event.organizer.verified_domain}
                    </span>
                  )}
                </p>
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-line bg-white p-5 text-sm">
            <h2 className="font-display text-lg font-bold text-night">About this event</h2>
            <p className="mt-2 whitespace-pre-line text-muted">{event.description || "The organizer hasn't added a description yet."}</p>
          </section>
        </div>

        {/* right: actions (sticks while scrolling on laptops) */}
        <aside className="h-fit space-y-3 rounded-2xl border border-line bg-white p-5 md:sticky md:top-24">
          <div className="flex items-baseline justify-between">
            <span className="font-display text-2xl font-bold text-night">{formatPrice(event)}</span>
            <span className="text-sm text-muted">{event.going.toLocaleString("en-IN")} going</span>
          </div>

          <RegisterBox event={event} onGoingChange={(going) => setEvent({ ...event, going })} />
          <SaveButton eventId={event.id} variant="full" />
          {event.registration_url && (
            <a href={event.registration_url} target="_blank" rel="noopener noreferrer" className="block w-full rounded-full border border-line py-3 text-center text-sm font-medium text-night hover:border-muted">
              Organizer&apos;s website
            </a>
          )}

          {maps && (
            <a href={maps} target="_blank" rel="noopener noreferrer" className="block w-full rounded-full border border-line py-3 text-center text-sm font-medium text-night hover:border-muted">
              Get directions
            </a>
          )}
          <a href={calendarUrl(event)} target="_blank" rel="noopener noreferrer" className="block w-full rounded-full border border-line py-3 text-center text-sm font-medium text-night hover:border-muted">
            Add to Google Calendar
          </a>
          <button onClick={share} className="w-full rounded-full border border-line py-3 text-sm font-medium text-night hover:border-muted">
            {copied ? "Link copied" : "Share"}
          </button>
          <ReportEvent eventId={event.id} />
        </aside>
      </div>
    </main>
  );
}