"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { activeTab, NAV_ITEMS } from "@/lib/nav";

/** Phone navigation: fixed bar at the bottom. Hidden on laptops (md and up). */
export default function BottomNav() {
  const active = activeTab(usePathname());

  return (
    <nav className="fixed inset-x-0 bottom-0 z-10 bg-ink md:hidden">
      <ul className="mx-auto flex max-w-md justify-around py-2.5">
        {NAV_ITEMS.map((it) => (
          <li key={it.label}>
            <Link href={it.href} className={`flex flex-col items-center gap-1 text-[11px] ${it.label === active ? "text-accent" : "text-white/70 hover:text-white"}`}>
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d={it.icon} />
              </svg>
              {it.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}