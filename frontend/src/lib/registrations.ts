// Registering for events and the user's QR passes.

import { apiFetch } from "@/lib/auth";
import { EventItem } from "@/lib/events";

export type Registration = {
  id: number;
  status: "registered" | "cancelled";
  qr_token: string;
  checked_in_at: string | null;
  created_at: string;
  event?: EventItem;
};

export async function getMyRegistration(eventId: number): Promise<Registration | null> {
  const d = await apiFetch(`/api/events/${eventId}/my-registration`);
  return d.registration;
}

export async function registerFor(eventId: number): Promise<Registration> {
  const d = await apiFetch(`/api/events/${eventId}/register`, { method: "POST" });
  return d.registration;
}

export async function cancelRegistration(eventId: number): Promise<Registration> {
  const d = await apiFetch(`/api/events/${eventId}/register`, { method: "DELETE" });
  return d.registration;
}

export async function getMyPasses(): Promise<Registration[]> {
  const d = await apiFetch("/api/me/registrations");
  return d.registrations;
}