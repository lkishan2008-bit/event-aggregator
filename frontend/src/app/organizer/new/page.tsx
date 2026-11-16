"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import RoleGate from "@/components/RoleGate";
import { apiFetch } from "@/lib/auth";

const CATEGORY_OPTIONS = [
  ["fest", "Fest"], ["hackathon", "Hackathon"], ["workshop", "Workshop"], ["meetup", "Meetup"],
  ["conference", "Conference"], ["cultural", "Cultural"], ["sports", "Sports"], ["other", "Other"],
];

function SubmitForm() {
  const router = useRouter();
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone; // e.g. Asia/Kolkata
  const [f, setF] = useState({
    title: "", category: "workshop", description: "", date: "", start: "", end: "",
    venue: "", address: "", city: "Bengaluru", country: "IN", price: "0", currency: "INR", link: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!f.title.trim()) return setError("Enter the event title.");
    if (!f.date || !f.start) return setError("Choose the date and start time.");
    if (!f.venue.trim() || !f.city.trim()) return setError("Enter the venue name and city.");
    if (!/^[A-Za-z]{2}$/.test(f.country)) return setError("Country must be a 2-letter code, like IN.");
    if (Number(f.price) < 0 || Number.isNaN(Number(f.price))) return setError("Price must be 0 or more.");

    // the date + time are in this browser's timezone; send them as exact UTC moments
    const start = new Date(`${f.date}T${f.start}`);
    const end = f.end ? new Date(`${f.date}T${f.end}`) : null;
    if (end && end <= start) return setError("End time must be after the start time.");
    if (start < new Date()) return setError("The start time is in the past.");

    setBusy(true);
    try {
      await apiFetch("/api/events", {
        method: "POST",
        body: JSON.stringify({
          title: f.title.trim(),
          category: f.category,
          description: f.description.trim() || null,
          start_utc: start.toISOString(),
          end_utc: end ? end.toISOString() : null,
          timezone,
          price_amount: Number(f.price),
          currency: f.currency.toUpperCase(),
          registration_url: f.link.trim() || null,
          venue: { name: f.venue.trim(), address: f.address.trim() || null, city: f.city.trim(), country_code: f.country.toUpperCase() },
        }),
      });
      router.push("/organizer");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  const input = "mt-1 w-full rounded-xl border border-line bg-white px-4 py-2.5 text-sm text-night outline-none focus:border-ink";
  const label = "block text-xs font-medium text-muted";

  return (
    <main className="mx-auto max-w-2xl px-4 pt-6 md:px-6 md:pt-10">
      <Link href="/organizer" className="text-sm text-muted hover:text-night">← Your events</Link>
      <h1 className="mt-3 font-display text-3xl font-bold text-night">Submit an event</h1>
      <p className="mt-1 text-sm text-muted">An admin will review it before it appears in the feed.</p>

      <form onSubmit={onSubmit} className="mt-6 space-y-5" noValidate>
        <section className="space-y-3 rounded-2xl border border-line bg-white p-5">
          <label className={label}>Event title
            <input className={input} value={f.title} onChange={set("title")} placeholder="HackRV 4.0" />
          </label>
          <label className={label}>Category
            <select className={input} value={f.category} onChange={set("category")}>
              {CATEGORY_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className={label}>Description
            <textarea className={`${input} min-h-28`} value={f.description} onChange={set("description")} placeholder="What happens, who it's for, what to bring" />
          </label>
        </section>

        <section className="space-y-3 rounded-2xl border border-line bg-white p-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <label className={label}>Date<input type="date" className={input} value={f.date} onChange={set("date")} /></label>
            <label className={label}>Starts<input type="time" className={input} value={f.start} onChange={set("start")} /></label>
            <label className={label}>Ends (optional)<input type="time" className={input} value={f.end} onChange={set("end")} /></label>
          </div>
          <p className="text-xs text-muted">Times are in your timezone: {timezone}</p>
        </section>

        <section className="space-y-3 rounded-2xl border border-line bg-white p-5">
          <label className={label}>Venue name
            <input className={input} value={f.venue} onChange={set("venue")} placeholder="RVCE Main Auditorium" />
          </label>
          <label className={label}>Address (optional)
            <input className={input} value={f.address} onChange={set("address")} placeholder="Mysore Road" />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className={label}>City<input className={input} value={f.city} onChange={set("city")} /></label>
            <label className={label}>Country code<input className={`${input} uppercase`} maxLength={2} value={f.country} onChange={set("country")} /></label>
          </div>
        </section>

        <section className="space-y-3 rounded-2xl border border-line bg-white p-5">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className={label}>Price (0 = free)<input type="number" min="0" className={input} value={f.price} onChange={set("price")} /></label>
            <label className={label}>Currency<input className={`${input} uppercase`} maxLength={3} value={f.currency} onChange={set("currency")} /></label>
          </div>
          <label className={label}>Registration link (optional)
            <input className={input} value={f.link} onChange={set("link")} placeholder="https://..." />
          </label>
        </section>

        {error && <p className="text-sm text-red-600">{error}</p>}
        <button type="submit" disabled={busy} className="w-full rounded-full bg-accent py-3 text-sm font-medium text-white hover:bg-accent-dark disabled:opacity-60">
          {busy ? "Submitting…" : "Submit for review"}
        </button>
      </form>
    </main>
  );
}

export default function NewEventPage() {
  return <RoleGate roles={["organizer", "admin"]}>{() => <SubmitForm />}</RoleGate>;
}