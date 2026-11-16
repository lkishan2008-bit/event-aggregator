"use client";

// Login state for the whole app.
// The backend gives us a JWT token on login/signup; we keep it (and the user) in localStorage
// so the user stays logged in after a refresh.

import { useSyncExternalStore } from "react";
import { API_URL } from "@/lib/events";

export type User = {
    id: number;
    name: string;
    email: string;
    role: "student" | "organizer" | "admin";
    country_code: string | null;
    city: string | null;
    timezone: string | null;
    email_verified?: boolean;
    created_at?: string | null;
};

type Session = { token: string; user: User };

const KEY = "ea_session";
let cache: Session | null | undefined;
const listeners = new Set<() => void>();

function read(): Session | null {
    if (cache !== undefined) return cache;
    try {
        const raw = localStorage.getItem(KEY);
        cache = raw ? (JSON.parse(raw) as Session) : null;
    } catch {
        cache = null;
    }
    return cache;
}

function save(session: Session | null) {
    cache = session;
    try {
        if (session) localStorage.setItem(KEY, JSON.stringify(session));
        else localStorage.removeItem(KEY);
    } catch {
        // storage unavailable (private mode etc.) — session lasts until refresh
    }
    listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
    listeners.add(listener);
    return () => listeners.delete(listener);
}

/** Current session, or null when logged out (always null while rendering on the server). */
export function useSession() {
    return useSyncExternalStore(subscribe, read, () => null);
}

export function logout() {
    save(null);
}

export type OtpChallenge = { otp_required: true; purpose: "signup" | "login"; email: string };

async function post(path: string, body: Record<string, unknown>) {
    let res: Response;
    try {
        res = await fetch(`${API_URL}/api/auth/${path}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
    } catch {
        throw new Error("Couldn't reach the server. Check that the backend is running.");
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error ?? "Something went wrong. Try again.");
    return data;
}

/** Step 1: check email + password. The server then emails a 6-digit code. */
export function login(email: string, password: string): Promise<OtpChallenge> {
    return post("login", { email, password });
}

/** Step 1 of signup: create the account. The server then emails a 6-digit code. */
export function signup(input: { name: string; email: string; password: string; role: "student" | "organizer"; city?: string }): Promise<OtpChallenge> {
    // the browser knows the user's timezone, e.g. "Asia/Kolkata"
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return post("register", { ...input, timezone });
}

/** Step 2: send the code from the email. On success the user is logged in. */
export async function verifyOtp(challenge: OtpChallenge, code: string) {
    const data = await post("verify-otp", { email: challenge.email, purpose: challenge.purpose, code });
    save({ token: data.access_token, user: data.user });
    return data.user as User;
}

export function resendOtp(challenge: OtpChallenge) {
    return post("resend-otp", { email: challenge.email, purpose: challenge.purpose });
}

/** Edit your own profile (name, city, country). Needs to be logged in. */
export async function updateProfile(fields: { name?: string; city?: string; country_code?: string }) {
    const session = read();
    if (!session) throw new Error("Log in first.");
    let res: Response;
    try {
        res = await fetch(`${API_URL}/api/auth/me`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token}` },
            body: JSON.stringify(fields),
        });
    } catch {
        throw new Error("Couldn't reach the server. Check that the backend is running.");
    }
    if (res.status === 401) {
        save(null); // login expired
        throw new Error("Your session expired. Log in again.");
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error ?? "Something went wrong. Try again.");
    save({ token: session.token, user: data.user });
    return data.user as User;
}
/** Same rules as the backend: 8+ chars, upper, lower, number, symbol. */
export const PASSWORD_RULES = [
    { label: "At least 8 characters", test: (p: string) => p.length >= 8 },
    { label: "An uppercase letter", test: (p: string) => /[A-Z]/.test(p) },
    { label: "A lowercase letter", test: (p: string) => /[a-z]/.test(p) },
    { label: "A number", test: (p: string) => /\d/.test(p) },
    { label: "A symbol (like @ # !)", test: (p: string) => /[^A-Za-z0-9]/.test(p) },
];