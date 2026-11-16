"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/auth";

type Status = { email: string; verified: boolean } | null;

/** "Get verified" card: prove you own an official college email to get the Verified badge. */
export default function VerifyOrganizer() {
  const [status, setStatus] = useState<Status | undefined>(undefined);
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"email" | "code">("email");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch("/api/organizer/verification").then((d) => setStatus(d.verification)).catch(() => setStatus(null));
  }, []);

  async function run(task: () => Promise<void>) {
    setBusy(true);
    setError("");
    try { await task(); } catch (e) { setError(e instanceof Error ? e.message : "Something went wrong."); } finally { setBusy(false); }
  }

  if (status === undefined) return null;
  if (status?.verified) {
    return (
      <div className="mb-5 rounded-2xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
        {"\u2713"} <b>Verified organizer</b> ({status.email}). Your events go live straight away unless our automatic checks find something unusual.
      </div>
    );
  }

  return (
    <div className="mb-5 rounded-2xl border border-line bg-white p-4">
      <p className="font-display text-lg font-bold text-night">Get verified</p>
      <p className="mt-1 text-sm text-muted">
        Confirm your official college email (like club@rvce.edu.in). Verified organizers get a badge and their events go live faster.
      </p>
      {step === "email" ? (
        <form className="mt-3 flex flex-col gap-2 sm:flex-row" onSubmit={(e) => { e.preventDefault(); run(async () => { await apiFetch("/api/organizer/verify/start", { method: "POST", body: JSON.stringify({ email }) }); setStep("code"); }); }}>
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="yourclub@college.edu.in" className="min-w-0 flex-1 rounded-full border border-line px-4 py-2.5 text-sm outline-none focus:border-ink" />
          <button disabled={busy} className="rounded-full bg-night px-5 py-2.5 text-sm font-medium text-white disabled:opacity-60">{busy ? "Sending\u2026" : "Send code"}</button>
        </form>
      ) : (
        <form className="mt-3 flex flex-col gap-2 sm:flex-row" onSubmit={(e) => { e.preventDefault(); run(async () => { const d = await apiFetch("/api/organizer/verify/confirm", { method: "POST", body: JSON.stringify({ code }) }); setStatus({ email: d.email, verified: true }); }); }}>
          <input value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} inputMode="numeric" placeholder={`6-digit code sent to ${email}`} className="min-w-0 flex-1 rounded-full border border-line px-4 py-2.5 text-sm tracking-widest outline-none focus:border-ink" />
          <button disabled={busy || code.length !== 6} className="rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-white disabled:opacity-60">{busy ? "Checking\u2026" : "Verify"}</button>
          <button type="button" onClick={() => { setStep("email"); setCode(""); }} className="px-2 text-sm text-muted underline">Change email</button>
        </form>
      )}
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}