"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import RoleGate from "@/components/RoleGate";
import { apiFetch } from "@/lib/auth";

type Source = {
  id: number; name: string; url: string; city: string; timezone: string; auto_approve: boolean;
  organizer: { id: number; name: string; email: string };
  last_synced_at: string | null; last_result: string | null; events: number;
};

const when = (iso: string | null) =>
  iso ? new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }).format(new Date(iso)) : "never";

function Sources() {
  const [sources, setSources] = useState<Source[] | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<number | "add" | null>(null);
  const [f, setF] = useState({ name: "", url: "", organizer_email: "", city: "Bengaluru", auto_approve: false });

  const load = useCallback(() => {
    apiFetch("/api/admin/sources").then((d) => setSources(d.sources)).catch((e) => setError(e.message));
  }, []);
  useEffect(() => { load(); }, [load]);

  async function add(e: FormEvent) {
    e.preventDefault();
    setBusy("add");
    setError("");
    try {
      await apiFetch("/api/admin/sources", { method: "POST", body: JSON.stringify(f) });
      setF({ name: "", url: "", organizer_email: "", city: "Bengaluru", auto_approve: false });
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't add the feed.");
    } finally {
      setBusy(null);
    }
  }

  async function act(id: number, kind: "sync" | "delete") {
    setBusy(id);
    setError("");
    try {
      if (kind === "sync") await apiFetch(`/api/admin/sources/${id}/sync`, { method: "POST" });
      else await apiFetch(`/api/admin/sources/${id}`, { method: "DELETE" });
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(null);
    }
  }

  const input = "mt-1 w-full rounded-xl border border-line bg-white px-4 py-2.5 text-sm text-night outline-none focus:border-ink";
  const label = "block text-xs font-medium text-muted";

  return (
    <div className="space-y-6">
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!sources ? (
        <div className="h-32 animate-pulse rounded-2xl bg-line/60" />
      ) : sources.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-line px-4 py-8 text-center text-sm text-muted">No feeds yet. Add a college or club calendar below.</p>
      ) : (
        <ul className="space-y-3">
          {sources.map((s) => (
            <li key={s.id} className="rounded-2xl border border-line bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-display text-lg font-bold text-night">{s.name}</p>
                  <p className="truncate text-xs text-muted">{s.url}</p>
                  <p className="mt-1 text-sm text-muted">
                    {s.events} events {"\u00b7"} as {s.organizer.name} {"\u00b7"} {s.city} {"\u00b7"} {s.auto_approve ? "goes live directly" : "admin reviews first"}
                  </p>
                  <p className={`mt-1 text-xs ${s.last_result?.startsWith("error") ? "text-red-600" : "text-muted"}`}>
                    Last sync: {when(s.last_synced_at)}{s.last_result ? ` \u00b7 ${s.last_result}` : ""}
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button disabled={busy === s.id} onClick={() => act(s.id, "sync")} className="rounded-full bg-night px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
                    {busy === s.id ? "Syncing\u2026" : "Sync now"}
                  </button>
                  <button disabled={busy === s.id} onClick={() => act(s.id, "delete")} className="rounded-full border border-line px-4 py-2 text-sm font-medium text-night disabled:opacity-60">
                    Remove
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={add} className="space-y-3 rounded-2xl border border-line bg-white p-5">
        <h2 className="font-display text-lg font-bold text-night">Add a calendar feed</h2>
        <label className={label}>Name
          <input className={input} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="PES Coding Club" />
        </label>
        <label className={label}>Calendar link (iCal / .ics)
          <input className={input} value={f.url} onChange={(e) => setF({ ...f, url: e.target.value })} placeholder="https://calendar.google.com/calendar/ical/.../basic.ics" />
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className={label}>Organizer account email
            <input className={input} value={f.organizer_email} onChange={(e) => setF({ ...f, organizer_email: e.target.value })} placeholder="pes@example.com" />
          </label>
          <label className={label}>City
            <input className={input} value={f.city} onChange={(e) => setF({ ...f, city: e.target.value })} />
          </label>
        </div>
        <label className="flex items-center gap-2 text-sm text-night">
          <input type="checkbox" checked={f.auto_approve} onChange={(e) => setF({ ...f, auto_approve: e.target.checked })} />
          Trusted feed: publish its events without review
        </label>
        <button disabled={busy === "add"} className="w-full rounded-full bg-accent py-3 text-sm font-medium text-white hover:bg-accent-dark disabled:opacity-60">
          {busy === "add" ? "Importing\u2026" : "Add and import now"}
        </button>
        <p className="text-xs text-muted">Feeds are re-imported automatically every hour: new events are added, changed ones updated, cancelled ones removed.</p>
      </form>
    </div>
  );
}

export default function SourcesPage() {
  return (
    <RoleGate roles={["admin"]}>
      {() => (
        <main className="mx-auto max-w-4xl px-4 pt-6 md:px-6 md:pt-10">
          <Link href="/admin" className="text-sm text-muted hover:text-night">{"\u2190"} Review events</Link>
          <h1 className="mt-2 font-display text-3xl font-bold text-night">Event feeds</h1>
          <p className="mb-5 mt-1 text-sm text-muted">Import events automatically from public college, club and community calendars.</p>
          <Sources />
        </main>
      )}
    </RoleGate>
  );
}