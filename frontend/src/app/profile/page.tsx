"use client";

import Link from "next/link";
import { logout, useSession } from "@/lib/auth";

export default function ProfilePage() {
    const session = useSession();

    if (!session) {
        return (
            <main className="px-4 pt-10">
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
    return (
        <main className="px-4 pt-10">
            <div className="flex items-center gap-3">
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-ink font-display text-xl font-bold text-white">
                    {user.name.charAt(0).toUpperCase()}
                </div>
                <div>
                    <h1 className="font-display text-2xl font-bold text-night">{user.name}</h1>
                    <p className="text-sm text-muted">{user.email}</p>
                </div>
            </div>

            <dl className="mt-6 divide-y divide-line rounded-2xl border border-line bg-white text-sm">
                <div className="flex justify-between px-4 py-3"><dt className="text-muted">Account type</dt><dd className="font-medium capitalize">{user.role}</dd></div>
                <div className="flex justify-between px-4 py-3"><dt className="text-muted">Timezone</dt><dd className="font-medium">{user.timezone ?? "—"}</dd></div>
            </dl>

            <button onClick={logout} className="mt-6 w-full rounded-full border border-line bg-white py-3 text-sm font-medium text-night hover:border-muted">
                Log out
            </button>
        </main>
    );
}