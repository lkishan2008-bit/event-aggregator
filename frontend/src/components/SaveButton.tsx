"use client";

import { useRouter } from "next/navigation";
import { MouseEvent, useEffect } from "react";
import { useSession } from "@/lib/auth";
import { ensureSavedLoaded, toggleSave, useSavedIds } from "@/lib/saved";

/** Bookmark button. Works inside a card link (it stops the click from opening the event). */
export default function SaveButton({ eventId, variant = "icon" }: { eventId: number; variant?: "icon" | "full" }) {
  const session = useSession();
  const ids = useSavedIds();
  const router = useRouter();
  const saved = ids?.has(eventId) ?? false;

  useEffect(() => { if (session) ensureSavedLoaded(session.token); }, [session]);

  function onClick(e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!session) return router.push("/login");
    toggleSave(eventId);
  }

  const icon = (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill={saved ? "currentColor" : "none"} stroke="currentColor" strokeWidth={2} aria-hidden>
      <path d="M6 3h12v18l-6-4-6 4z" strokeLinejoin="round" />
    </svg>
  );

  if (variant === "full") {
    return (
      <button onClick={onClick} className={`flex w-full items-center justify-center gap-2 rounded-full border py-3 text-sm font-medium ${saved ? "border-night bg-night text-white" : "border-line text-night hover:border-muted"}`}>
        {icon} {saved ? "Saved" : "Save for later"}
      </button>
    );
  }
  return (
    <button
      onClick={onClick}
      aria-label={saved ? "Remove from saved" : "Save event"}
      className={`flex h-8 w-8 items-center justify-center rounded-full ${saved ? "bg-white text-night" : "bg-black/30 text-white hover:bg-black/45"}`}
    >
      {icon}
    </button>
  );
}