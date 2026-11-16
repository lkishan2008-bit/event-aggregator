"use client";

import { useState } from "react";
import { apiFetch, useSession } from "@/lib/auth";

const REASONS = [
  ["fake", "This event is fake / not happening"],
  ["scam", "Asks for money outside the app"],
  ["wrong_details", "Wrong date, time or place"],
  ["spam", "Spam or misleading"],
  ["other", "Something else"],
] as const;

/** Small "Report this event" link that opens a reason picker. */
export default function ReportEvent({ eventId }: { eventId: number }) {
  const session = useSession();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<string>("fake");
  const [details, setDetails] = useState("");
  const [state, setState] = useState<"idle" | "busy" | "done">("idle");
  const [error, setError] = useState("");

  if (!session) return null;
  if (state === "done") return <p className="text-center text-xs text-muted">Thanks, our team will review this event.</p>;

  async function send() {
    setState("busy");
    setError("");
    try {
      await apiFetch(`/api/events/${eventId}/report`, { method: "POST", body: JSON.stringify({ reason, details }) });
      setState("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't send the report.");
      setState("idle");
    }
  }

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="w-full text-center text-xs text-muted underline hover:text-night">
        Report this event
      </button>
    );
  }
  return (
    <div className="space-y-2 rounded-xl border border-line p-3">
      <p className="text-sm font-medium text-night">What&apos;s wrong?</p>
      <select value={reason} onChange={(e) => setReason(e.target.value)} className="w-full rounded-lg border border-line px-3 py-2 text-sm">
        {REASONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
      <textarea value={details} onChange={(e) => setDetails(e.target.value)} placeholder="Details (optional)" className="w-full rounded-lg border border-line px-3 py-2 text-sm" />
      <div className="flex gap-2">
        <button onClick={send} disabled={state === "busy"} className="flex-1 rounded-full bg-night py-2 text-sm font-medium text-white disabled:opacity-60">
          {state === "busy" ? "Sending\u2026" : "Send report"}
        </button>
        <button onClick={() => setOpen(false)} className="px-3 text-sm text-muted underline">Cancel</button>
      </div>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}