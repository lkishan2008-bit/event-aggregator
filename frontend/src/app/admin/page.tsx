"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import RoleGate from "@/components/RoleGate";
import StatusBadge from "@/components/StatusBadge";
import { apiFetch } from "@/lib/auth";
import { EventItem, formatEventTime, formatPrice } from "@/lib/events";

const TABS = [["pending", "Waiting"], ["approved", "Live"], ["rejected", "Rejected"]] as const;

function Review() {
  const [tab, setTab] = useState<(typeof TABS)[number][0]>("pending");
  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiFetch(`/api/admin/events?status=${tab}`)
      .then((d) => { if (!cancelled) { setEvents(d.events); setError(""); } })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, [tab]);

  async function decide(id: number, action: "approve" | "reject") {
    setBusyId(id);
    try {
      await apiFetch(`/api/admin/events/${id}/${action}`, { method: "POST" });
      setEvents((list) => (list ?? []).filter((e) => e.id !== id)); // it moved to another tab
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <div className="mb-4 flex gap-2">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            onClick={() => { setTab(key); setEvents(null); }}
            className={`rounded-full border px-4 py-1.5 text-sm font-medium ${tab === key ? "border-ink bg-ink text-white" : "border-line bg-white text-night"}`}
          >
            {label}
          </button>
        ))}
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {!events && !error && <div className="h-40 animate-pulse rounded-2xl bg-line/60" />}
      {events && events.length === 0 && (
        <p className="rounded-2xl border border-dashed border-line px-4 py-10 text-center text-sm text-muted">Nothing here right now.</p>
      )}

      <div className="space-y-3">
        {events?.map((e) => (
          <article key={e.id} className="rounded-2xl border border-line bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <h2 className="font-display text-lg font-bold text-night">{e.title}</h2>
                <p className="text-sm text-muted">
                  {formatEventTime(e)} {"\u00b7"} {e.venue?.name}, {e.venue?.city} {"\u00b7"} {formatPrice(e)} {"\u00b7"} <span className="capitalize">{e.category}</span>
                </p>
                <p className="text-sm text-muted">By {e.organizer?.name ?? "unknown"}{e.organizer?.verified_domain ? ` \u00b7 verified @${e.organizer.verified_domain}` : ""}</p>
              </div>
              <StatusBadge status={e.status} />
            </div>
            {e.description && <p className="mt-2 line-clamp-3 text-sm text-night">{e.description}</p>}

            {(e.reports ?? 0) > 0 && (
              <p className="mt-2 text-sm font-medium text-red-700">Reported by {e.reports} user{e.reports === 1 ? "" : "s"}</p>
            )}
            {e.red_flags && e.red_flags.length > 0 && (
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {e.red_flags.map((f) => (
                  <li key={f} className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${f.startsWith("Organizer is not verified") ? "bg-line text-muted" : "bg-red-50 text-red-700"}`}>
                    {f}
                  </li>
                ))}
              </ul>
            )}

            <div className="mt-3 flex flex-wrap gap-2">
              {e.status !== "approved" && (
                <button disabled={busyId === e.id} onClick={() => decide(e.id, "approve")} className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-dark disabled:opacity-60">
                  Approve
                </button>
              )}
              {e.status !== "rejected" && (
                <button disabled={busyId === e.id} onClick={() => decide(e.id, "reject")} className="rounded-full border border-line px-4 py-2 text-sm font-medium text-night hover:border-muted disabled:opacity-60">
                  Reject
                </button>
              )}
              {e.status === "approved" && <Link href={`/events/${e.id}`} className="px-2 py-2 text-sm font-medium text-night underline">View</Link>}
            </div>
          </article>
        ))}
      </div>
    </>
  );
}

export default function AdminPage() {
  return (
    <RoleGate roles={["admin"]}>
      {() => (
        <main className="mx-auto max-w-4xl px-4 pt-6 md:px-6 md:pt-10">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <h1 className="font-display text-3xl font-bold text-night">Review events</h1>
            <Link href="/admin/sources" className="rounded-full border border-line bg-white px-4 py-2 text-sm font-medium text-night hover:border-muted">Event feeds</Link>
          </div>
          <p className="mb-5 mt-1 text-sm text-muted">Approve events to publish them in the feed. Rejected events stay hidden.</p>
          <Review />
        </main>
      )}
    </RoleGate>
  );
}