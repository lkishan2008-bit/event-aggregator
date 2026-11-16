"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { logout, updateProfile, useSession, User } from "@/lib/auth";

function memberSince(iso?: string | null) {
    if (!iso) return "—";
    return new Intl.DateTimeFormat("en-IN", { month: "long", year: "numeric" }).format(new Date(iso));
}

const ROLE_INFO: Record<User["role"], { title: string; text: string }> = {
    student: { title: "Student", text: "Register for events and keep your passes here." },
    organizer: { title: "Organizer", text: "Soon: submit events, see registrations and scan QR passes at the gate." },
    admin: { title: "Admin", text: "Soon: review and approve events submitted by organizers." },
};

export default function ProfilePage() {
    const session = useSession();
    const [editing, setEditing] = useState(false);
    const [name, setName] = useState("");
    const [city, setCity] = useState("");
    const [country, setCountry] = useState("");
    const [error, setError] = useState("");
    const [saved, setSaved] = useState(false);
    const [busy, setBusy] = useState(false);

    if (!session) {
        return (
            <main className="mx-auto max-w-md px-4 pt-10 md:pt-16">
                <h1 className="font-display text-3xl font-bold text-night">Your profile</h1>
                <p className="mt-2 text-sm text-muted">Log in to save events and get your passes.</p>
                <div className="mt-6 flex gap-2">
                    <Link href="/login" className="rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-white">Log in</Link>
                    <Link href="/signup" className="rounded-full border border-line bg-white px-5 py-2.5 text-sm font-medium text-night">Create account</Link>
                </div>
            </main>
        );
    }

    const { user } = session;
    const role = ROLE_INFO[user.role];

    function startEditing() {
        setName(user.name);
        setCity(user.city ?? "");
        setCountry(user.country_code ?? "");
        setError("");
        setSaved(false);
        setEditing(true);
    }

    async function onSave(e: FormEvent) {
        e.preventDefault();
        setError("");
        if (!name.trim()) return setError("Enter your name.");
        if (country && !/^[A-Za-z]{2}$/.test(country)) return setError("Country must be a 2-letter code, like IN or US.");
        setBusy(true);
        try {
            await updateProfile({ name: name.trim(), city: city.trim(), country_code: country.trim() });
            setEditing(false);
            setSaved(true);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Something went wrong. Try again.");
        } finally {
            setBusy(false);
        }
    }

    const input = "w-full rounded-xl border border-line bg-white px-4 py-2.5 text-sm outline-none focus:border-ink";
    const row = "flex justify-between gap-4 px-4 py-3";

    return (
        <main className="mx-auto max-w-2xl px-4 pt-10 md:pt-16">
            <div className="flex items-center gap-4">
                <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-ink font-display text-2xl font-bold text-white">
                    {user.name.charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0">
                    <h1 className="truncate font-display text-2xl font-bold text-night md:text-3xl">{user.name}</h1>
                    <p className="flex flex-wrap items-center gap-2 text-sm text-muted">
                        <span className="truncate">{user.email}</span>
                        {user.email_verified !== false && (
                            <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">✓ Verified</span>
                        )}
                    </p>
                </div>
            </div>

            {saved && <p className="mt-4 rounded-xl bg-green-50 px-4 py-2.5 text-sm text-green-800">Profile updated.</p>}

            <div className="mt-6 grid gap-4 md:grid-cols-2">
                {/* details or edit form */}
                <section className="rounded-2xl border border-line bg-white text-sm">
                    <div className="flex items-center justify-between border-b border-line px-4 py-3">
                        <h2 className="font-medium text-night">Your details</h2>
                        {!editing && (
                            <button onClick={startEditing} className="text-sm font-medium text-night underline">Edit</button>
                        )}
                    </div>

                    {editing ? (
                        <form onSubmit={onSave} className="space-y-3 p-4" noValidate>
                            <label className="block text-xs text-muted">Name
                                <input className={`${input} mt-1`} value={name} onChange={(e) => setName(e.target.value)} />
                            </label>
                            <label className="block text-xs text-muted">City
                                <input className={`${input} mt-1`} placeholder="Bengaluru" value={city} onChange={(e) => setCity(e.target.value)} />
                            </label>
                            <label className="block text-xs text-muted">Country code
                                <input className={`${input} mt-1 uppercase`} placeholder="IN" maxLength={2} value={country} onChange={(e) => setCountry(e.target.value)} />
                            </label>
                            {error && <p className="text-sm text-red-600">{error}</p>}
                            <div className="flex gap-2 pt-1">
                                <button type="submit" disabled={busy} className="flex-1 rounded-full bg-accent py-2.5 text-sm font-medium text-white hover:bg-accent-dark disabled:opacity-60">
                                    {busy ? "Saving…" : "Save"}
                                </button>
                                <button type="button" onClick={() => setEditing(false)} className="flex-1 rounded-full border border-line py-2.5 text-sm font-medium text-night">
                                    Cancel
                                </button>
                            </div>
                        </form>
                    ) : (
                        <dl className="divide-y divide-line">
                            <div className={row}><dt className="text-muted">City</dt><dd className="font-medium">{user.city || "—"}</dd></div>
                            <div className={row}><dt className="text-muted">Country</dt><dd className="font-medium">{user.country_code || "—"}</dd></div>
                            <div className={row}><dt className="text-muted">Timezone</dt><dd className="font-medium">{user.timezone ?? "—"}</dd></div>
                            <div className={row}><dt className="text-muted">Member since</dt><dd className="font-medium">{memberSince(user.created_at)}</dd></div>
                        </dl>
                    )}
                </section>

                {/* account type */}
                <section className="flex flex-col rounded-2xl border border-line bg-white p-4 text-sm">
                    <p className="text-muted">Account type</p>
                    <p className="mt-1 font-display text-2xl font-bold text-night">{role.title}</p>
                    <p className="mt-2 text-muted">{role.text}</p>
                    <div className="mt-auto pt-4">
                        <button onClick={logout} className="w-full rounded-full border border-line bg-white py-2.5 text-sm font-medium text-night hover:border-muted">
                            Log out
                        </button>
                    </div>
                </section>
            </div>
        </main>
    );
}