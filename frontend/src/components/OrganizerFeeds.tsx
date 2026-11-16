"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/auth";

type Source = { id: number; name: string; url: string; events: number; last_synced_at: string | null; last_result: string | null };

const when = (iso: string | null) =>
  iso ? new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }).format(new Date(iso)) : "never";

/** Organizers connect their club calendar (Google Calendar / Luma / Meetup .ics link); it re-syncs every hour. */
export default function OrganizerFeeds() {
  const [sources, setSources] = useState<Source[] | null>(null);
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ name: "", url: "", city: "Bengaluru" });
  const [busy, setBusy] = useState<number | "add" | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    apiFetch("/api/organizer/sources").then((d) => setSources(d.sources)).catch((e) => setError(e.message));
  }, []);
  useEffect(() => { load(); }, [load]);

  async function run(id: number | "add", task: () => Promise<unknown>) {
    setBusy(id);
    setError("");
    try { await task(); load(); } catch (e) { setError(e instanceof Error ? e.message : "Something went wrong."); } finally { setBusy(null); }
  }

  function add(e: FormEvent) {
    e.preventDefault();
    run("add", async () => {
      await apiFetch("/api/organizer/sources", { method: "POST", body: JSON.stringify(f) });
      setF({ name: "", url: "", city: "Bengaluru" });
      setOpen(false);
    });
  }

  const input = "mt-1 w-full rounded-xl border border-line bg-white px-4 py-2.5 text-sm text-night outline-none focus:border-ink";

  return (
    <section className="mb-5 rounded-2xl border border-line bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-display text-lg font-bold text-night">Auto-import my calendar</p>
          <p className="text-sm text-muted">Connect your club&apos;s Google Calendar, Luma or Meetup link. New and changed events sync every hour.</p>
        </div>
        {!open && <button onClick={() => setOpen(true)} className="rounded-full bg-night px-4 py-2 text-sm font-medium text-white">+ Connect calendar</button>}
      </div>

      {sources && sources.length > 0 && (
        <ul className="mt-3 space-y-2">
          {sources.map((s) => (
            <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-line px-3 py-2">
              <div className="min-w-0">
                <p className="text-sm font-medium text-night">{s.name} {"\u00b7"} {s.events} events</p>
                <p className={`text-xs ${s.last_result?.startsWith("error") ? "text-red-600" : "text-muted"}`}>
                  Last sync {when(s.last_synced_at)}{s.last_result ? ` \u00b7 ${s.last_result}` : ""}
                </p>
              </div>
              <div className="flex gap-2">
                <button disabled={busy === s.id} onClick={() => run(s.id, () => apiFetch(`/api/organizer/sources/${s.id}/sync`, { method: "POST" }))} className="rounded-full border border-line px-3 py-1 text-xs font-medium text-night disabled:opacity-60">
                  {busy === s.id ? "Syncing\u2026" : "Sync now"}
                </button>
                <button disabled={busy === s.id} onClick={() => run(s.id, () => apiFetch(`/api/organizer/sources/${s.id}`, { method: "DELETE" }))} className="px-2 text-xs text-muted underline">
                  Disconnect
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {open && (
        <form onSubmit={add} className="mt-3 space-y-2">
          <input className={input} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Calendar name, e.g. Coding Club events" />
          <input className={input} value={f.url} onChange={(e) => setF({ ...f, url: e.target.value })} placeholder="iCal link (ends with .ics)" />
          <input className={input} value={f.city} onChange={(e) => setF({ ...f, city: e.target.value })} placeholder="City" />
          <div className="flex gap-2">
            <button disabled={busy === "add"} className="rounded-full bg-accent px-5 py-2 text-sm font-medium text-white disabled:opacity-60">
              {busy === "add" ? "Importing\u2026" : "Connect and import"}
            </button>
            <button type="button" onClick={() => setOpen(false)} className="px-2 text-sm text-muted underline">Cancel</button>
          </div>
          <p className="text-xs text-muted">Google Calendar: Settings {"\u2192"} your calendar {"\u2192"} Integrate calendar {"\u2192"} &quot;Public address in iCal format&quot;.</p>
        </form>
      )}
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </section>
  );
}