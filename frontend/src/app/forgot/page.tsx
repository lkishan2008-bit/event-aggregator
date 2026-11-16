"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { API_URL } from "@/lib/events";
import { PASSWORD_RULES } from "@/lib/auth";

async function post(path: string, body: object) {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  } catch {
    throw new Error("Couldn't reach the server. Check that the backend is running.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error ?? "Something went wrong.");
  return data;
}

export default function ForgotPage() {
  const router = useRouter();
  const [step, setStep] = useState<"email" | "reset" | "done">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run(task: () => Promise<void>) {
    setBusy(true);
    setError("");
    try { await task(); } catch (e) { setError(e instanceof Error ? e.message : "Something went wrong."); } finally { setBusy(false); }
  }

  const sendCode = (e: FormEvent) => { e.preventDefault(); run(async () => { await post("/api/auth/forgot", { email }); setStep("reset"); }); };
  const reset = (e: FormEvent) => {
    e.preventDefault();
    run(async () => { await post("/api/auth/reset", { email, code, password }); setStep("done"); setTimeout(() => router.push("/login"), 1500); });
  };

  const input = "mt-1 w-full rounded-xl border border-line bg-white px-4 py-2.5 text-sm text-night outline-none focus:border-ink";
  const primary = "w-full rounded-full bg-accent py-3 text-sm font-medium text-white hover:bg-accent-dark disabled:opacity-60";

  return (
    <main className="mx-auto max-w-md px-4 pt-10 md:pt-16">
      <h1 className="font-display text-3xl font-bold text-night">Reset your password</h1>

      {step === "email" && (
        <form onSubmit={sendCode} className="mt-6 space-y-4">
          <p className="text-sm text-muted">Enter your account email. We&apos;ll send you a 6-digit code.</p>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@college.edu.in" className={input} />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button disabled={busy} className={primary}>{busy ? "Sending\u2026" : "Send code"}</button>
        </form>
      )}

      {step === "reset" && (
        <form onSubmit={reset} className="mt-6 space-y-4">
          <p className="text-sm text-muted">If an account exists for <b>{email}</b>, a code is on its way.</p>
          <input value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} inputMode="numeric" placeholder="6-digit code" className={`${input} tracking-widest`} />
          <div className="relative">
            <input type={show ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="New password" className={`${input} pr-16`} />
            <button type="button" onClick={() => setShow(!show)} className="absolute right-3 top-1/2 mt-0.5 -translate-y-1/2 text-xs font-medium text-muted">
              {show ? "Hide" : "Show"}
            </button>
          </div>
          <ul className="space-y-1 text-xs">
            {PASSWORD_RULES.map((r) => (
              <li key={r.label} className={r.test(password) ? "text-green-700" : "text-muted"}>{r.test(password) ? "\u2713" : "\u2022"} {r.label}</li>
            ))}
          </ul>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button disabled={busy || code.length !== 6 || !PASSWORD_RULES.every((r) => r.test(password))} className={primary}>
            {busy ? "Saving\u2026" : "Set new password"}
          </button>
          <button type="button" onClick={() => setStep("email")} className="w-full text-sm text-muted underline">Use a different email</button>
        </form>
      )}

      {step === "done" && (
        <p className="mt-6 rounded-xl bg-green-50 px-4 py-3 text-sm text-green-800">{"\u2713"} Password changed. Taking you to log in{"\u2026"}</p>
      )}

      <p className="mt-6 text-center text-sm text-muted"><Link href="/login" className="font-medium text-night underline">Back to log in</Link></p>
    </main>
  );
}