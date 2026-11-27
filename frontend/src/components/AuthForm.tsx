"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { login, OtpChallenge, PASSWORD_RULES, resendOtp, signup, verifyOtp } from "@/lib/auth";

const RESEND_SECONDS = 60;

export default function AuthForm({ mode }: { mode: "login" | "signup" }) {
    const router = useRouter();
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [role, setRole] = useState<"student" | "organizer">("student");
    const [error, setError] = useState("");
    const [busy, setBusy] = useState(false);

    // step 2: the emailed code
    const [challenge, setChallenge] = useState<OtpChallenge | null>(null);
    const [code, setCode] = useState("");
    const [cooldown, setCooldown] = useState(0);
    const [notice, setNotice] = useState("");

    const isSignup = mode === "signup";
    const passwordOk = PASSWORD_RULES.every((r) => r.test(password));

    // count down the "Resend code" timer
    useEffect(() => {
        if (cooldown <= 0) return;
        const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
        return () => clearTimeout(t);
    }, [cooldown]);

    async function onSubmitDetails(e: FormEvent) {
        e.preventDefault();
        setError("");
        if (isSignup && !name.trim()) return setError("Enter your name.");
        if (!email.includes("@")) return setError("Enter a valid email address.");
        if (isSignup && !passwordOk) return setError("Your password doesn't meet all the rules yet.");
        if (!isSignup && !password) return setError("Enter your password.");

        setBusy(true);
        try {
            const next = isSignup ? await signup({ name: name.trim(), email, password, role }) : await login(email, password);
            setChallenge(next);
            setCooldown(RESEND_SECONDS);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Something went wrong. Try again.");
        } finally {
            setBusy(false);
        }
    }

    async function onSubmitCode(e: FormEvent) {
        e.preventDefault();
        if (!challenge) return;
        setError("");
        setNotice("");
        if (!/^\d{6}$/.test(code)) return setError("Enter the 6-digit code from your email.");

        setBusy(true);
        try {
            await verifyOtp(challenge, code);
            router.push("/");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Something went wrong. Try again.");
        } finally {
            setBusy(false);
        }
    }

    async function onResend() {
        if (!challenge || cooldown > 0) return;
        setError("");
        try {
            await resendOtp(challenge);
            setNotice("New code sent.");
            setCode("");
            setCooldown(RESEND_SECONDS);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Something went wrong. Try again.");
        }
    }

    const input = "w-full rounded-xl border border-line bg-white px-4 py-2.5 text-sm outline-none focus:border-ink";
    const primary = "w-full rounded-full bg-accent py-3 text-sm font-medium text-white hover:bg-accent-dark disabled:opacity-60";

    // ---------- step 2: enter the code ----------
    if (challenge) {
        return (
            <main className="px-4 pt-10">
                <h1 className="font-display text-3xl font-bold text-night">Check your email</h1>
                <p className="mt-1 text-sm text-muted">
                    We sent a 6-digit code to <span className="font-medium text-night">{challenge.email}</span>. It expires in 10 minutes.
                </p>

                <form onSubmit={onSubmitCode} className="mt-6 space-y-3" noValidate>
                    <input
                        className={`${input} text-center font-display text-2xl tracking-[0.5em]`}
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        maxLength={6}
                        placeholder="••••••"
                        value={code}
                        onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                        autoFocus
                    />
                    {error && <p className="text-sm text-red-600">{error}</p>}
                    {notice && <p className="text-sm text-muted">{notice}</p>}
                    <button type="submit" disabled={busy} className={primary}>{busy ? "Checking…" : "Verify"}</button>
                </form>

                <div className="mt-6 flex justify-between text-sm">
                    <button onClick={() => { setChallenge(null); setCode(""); setError(""); }} className="text-muted underline">
                        Change email
                    </button>
                    <button onClick={onResend} disabled={cooldown > 0} className="font-medium text-night underline disabled:text-muted disabled:no-underline">
                        {cooldown > 0 ? `Resend code in ${cooldown}s` : "Resend code"}
                    </button>
                </div>
            </main>
        );
    }

    // ---------- step 1: details ----------
    return (
        <main className="px-4 pt-10">
            <h1 className="font-display text-3xl font-bold text-night">{isSignup ? "Create your account" : "Welcome back"}</h1>
            <p className="mt-1 text-sm text-muted">
                {isSignup ? "Discover local festivals and events near you." : "Log in to register for events."}
            </p>

            <form onSubmit={onSubmitDetails} className="mt-6 space-y-3" noValidate>
                {isSignup && (
                    <input className={input} placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
                )}
                <input className={input} type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
                <div className="relative">
                    <input
                        className={`${input} pr-12`}
                        type={showPassword ? "text" : "password"}
                        placeholder="Password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        autoComplete={isSignup ? "new-password" : "current-password"}
                    />
                    <button
                        type="button"
                        onClick={() => setShowPassword((s) => !s)}
                        aria-label={showPassword ? "Hide password" : "Show password"}
                        className="absolute inset-y-0 right-0 flex w-12 items-center justify-center text-muted hover:text-night"
                    >
                        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
                            <circle cx="12" cy="12" r="3" />
                            {showPassword && <path d="M3 3l18 18" />}
                        </svg>
                    </button>
                </div>
                {isSignup && (
                    <ul className="space-y-1 rounded-xl border border-line bg-white px-4 py-3 text-xs">
                        {PASSWORD_RULES.map((r) => {
                            const ok = r.test(password);
                            return (
                                <li key={r.label} className={ok ? "text-green-700" : "text-muted"}>
                                    {ok ? "✓" : "○"} {r.label}
                                </li>
                            );
                        })}
                    </ul>
                )}

                {isSignup && (
                    <div className="grid grid-cols-2 gap-2 pt-1">
                        {(["student", "organizer"] as const).map((r) => (
                            <button
                                key={r}
                                type="button"
                                onClick={() => setRole(r)}
                                className={`rounded-xl border px-3 py-2.5 text-sm font-medium ${role === r ? "border-ink bg-ink text-white" : "border-line bg-white text-night"}`}
                            >
                                {r === "student" ? "I'm attending" : "I organize events"}
                            </button>
                        ))}
                    </div>
                )}

                {error && <p className="text-sm text-red-600">{error}</p>}

                <button type="submit" disabled={busy} className={primary}>
                    {busy ? "Please wait…" : isSignup ? "Create account" : "Continue"}
                </button>
            </form>

            {!isSignup && (
        <p className="mt-4 text-center text-sm"><Link href="/forgot" className="text-muted underline hover:text-night">Forgot password?</Link></p>
      )}
      <p className="mt-6 text-center text-sm text-muted">
                {isSignup ? "Already have an account? " : "New here? "}
                <Link href={isSignup ? "/login" : "/signup"} className="font-medium text-night underline">
                    {isSignup ? "Log in" : "Create an account"}
                </Link>
            </p>
        </main>
    );
}