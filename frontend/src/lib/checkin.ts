// Organizer gate check-in: scan a pass, see live numbers.

import { apiFetch } from "@/lib/auth";

export type Attendee = { registration_id: number; name: string; email: string; checked_in_at: string | null };
export type CheckinResult = {
  result: "ok" | "already" | "invalid" | "wrong_event" | "cancelled" | "error";
  message: string;
  attendee?: Attendee;
};
export type CheckinStats = { event: { id: number; title: string }; going: number; checked_in: number; recent: Attendee[] };

export async function checkIn(eventId: number, code: string): Promise<CheckinResult> {
  try {
    return await apiFetch(`/api/organizer/events/${eventId}/checkin`, { method: "POST", body: JSON.stringify({ code }) });
  } catch (e) {
    return { result: "error", message: e instanceof Error ? e.message : "Something went wrong." };
  }
}

export function getCheckinStats(eventId: number): Promise<CheckinStats> {
  return apiFetch(`/api/organizer/events/${eventId}/checkins`);
}