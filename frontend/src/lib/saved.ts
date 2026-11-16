// Saved (bookmarked) events: a tiny shared store so every Save button on the page stays in sync.

import { useSyncExternalStore } from "react";
import { apiFetch } from "@/lib/auth";
import { EventItem } from "@/lib/events";

let ids: Set<number> | null = null;
let loadedFor: string | null = null; // which login token the ids belong to
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((l) => l());
const subscribe = (l: () => void) => { listeners.add(l); return () => listeners.delete(l); };

/** Set of saved event ids for the logged-in user (null until loaded). */
export function useSavedIds() {
  return useSyncExternalStore(subscribe, () => ids, () => null);
}

/** Load the saved ids once per login. */
export function ensureSavedLoaded(token: string) {
  if (loadedFor === token) return;
  loadedFor = token;
  ids = null;
  apiFetch("/api/me/saved")
    .then((d) => { if (loadedFor === token) { ids = new Set(d.ids as number[]); emit(); } })
    .catch(() => { loadedFor = null; });
}

export async function toggleSave(eventId: number) {
  const wasSaved = ids?.has(eventId) ?? false;
  const next = new Set(ids ?? []);
  if (wasSaved) next.delete(eventId); else next.add(eventId);
  ids = next; // update the button straight away
  emit();
  try {
    await apiFetch(`/api/events/${eventId}/save`, { method: wasSaved ? "DELETE" : "POST" });
  } catch {
    const undo = new Set(ids);
    if (wasSaved) undo.add(eventId); else undo.delete(eventId);
    ids = undo;
    emit();
  }
}

export async function getSavedEvents(): Promise<EventItem[]> {
  const d = await apiFetch("/api/me/saved");
  return d.events;
}