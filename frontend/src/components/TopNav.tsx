"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import UserBadge from "@/components/UserBadge";
import { activeTab, APP_NAME, NAV_ITEMS } from "@/lib/nav";

/** Laptop navigation: bar at the top. Hidden on phones (below md). */
export default function TopNav() {
    const active = activeTab(usePathname());

    return (
        <header className="sticky top-0 z-10 hidden border-b border-line bg-paper/95 backdrop-blur md:block">
            <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
                <Link href="/" className="font-display text-xl font-bold text-night">{APP_NAME}</Link>
                <nav className="flex items-center gap-1">
                    {NAV_ITEMS.filter((it) => it.label !== "Profile").map((it) => (
                        <Link
                            key={it.label}
                            href={it.href}
                            className={`rounded-full px-4 py-2 text-sm font-medium ${it.label === active ? "bg-ink text-white" : "text-muted hover:text-night"}`}
                        >
                            {it.label}
                        </Link>
                    ))}
                </nav>
                <UserBadge />
            </div>
        </header>
    );
}