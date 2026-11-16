// Event data comes from the Flask API (GET /api/events).
// Global-ready: times in UTC + the event's IANA timezone, price + ISO currency.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5000";

export type EventItem = {
  id: number;
  title: string;
  description: string | null;
  category: string;
  start_utc: string;
  end_utc: string | null;
  timezone: string;
  price_amount: number;
  currency: string;
  is_free: boolean;
  poster_url: string | null;
  registration_url: string | null;
  venue: { name: string; address: string | null; city: string; country_code: string; latitude?: number | null; longitude?: number | null } | null;
  organizer?: { id: number; name: string } | null;
  status?: "pending" | "approved" | "rejected" | "cancelled" | "completed";
  going: number;
};

export const CATEGORIES = [
  { key: "all", label: "All" },
  { key: "fest", label: "Fests" },
  { key: "hackathon", label: "Hackathons" },
  { key: "workshop", label: "Workshops" },
  { key: "meetup", label: "Meetups" },
] as const;

export async function fetchEvents(): Promise<EventItem[]> {
  const res = await fetch(`${API_URL}/api/events`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  const data = await res.json();
  return data.events as EventItem[];
}

export async function fetchEvent(id: string | number): Promise<EventItem | null> {
  const res = await fetch(`${API_URL}/api/events/${id}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API error ${res.status}`);
  const data = await res.json();
  return data.event as EventItem;
}

/** Google Maps directions link: uses exact coordinates if we have them, otherwise the address text. */
export function directionsUrl(e: EventItem) {
  const v = e.venue;
  if (!v) return null;
  const destination = v.latitude != null && v.longitude != null
    ? `${v.latitude},${v.longitude}`
    : [v.name, v.address, v.city, v.country_code].filter(Boolean).join(", ");
  return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(destination)}`;
}

/** "Add to Google Calendar" link with the event's start/end time. */
export function calendarUrl(e: EventItem) {
  const fmt = (iso: string) => iso.replace(/[-:]/g, "").replace(/\.\d+/, "");
  const start = fmt(e.start_utc);
  const end = fmt(e.end_utc ?? new Date(new Date(e.start_utc).getTime() + 2 * 3600_000).toISOString());
  const where = e.venue ? [e.venue.name, e.venue.address, e.venue.city].filter(Boolean).join(", ") : "";
  const params = new URLSearchParams({ action: "TEMPLATE", text: e.title, dates: `${start}/${end}`, location: where, details: e.description ?? "" });
  return `https://calendar.google.com/calendar/render?${params}`;
}

export function formatTimeRange(e: EventItem) {
  const day = new Intl.DateTimeFormat("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: e.timezone }).format(new Date(e.start_utc));
  const time = (iso: string) => new Intl.DateTimeFormat("en-IN", { hour: "numeric", minute: "2-digit", timeZone: e.timezone }).format(new Date(iso));
  return { day, time: e.end_utc ? `${time(e.start_utc)} – ${time(e.end_utc)}` : time(e.start_utc) };
}

// Placeholder poster colours until organizers upload real posters
const POSTER_COLORS = ["#2f5bff", "#0e7c7b", "#c2185b", "#6d4c41", "#ef6c00", "#5e35b1"];
export function posterColor(e: EventItem) {
  return POSTER_COLORS[e.id % POSTER_COLORS.length];
}

export function formatEventTime(e: EventItem) {
  return new Intl.DateTimeFormat("en-IN", {
    weekday: "short", day: "numeric", month: "short",
    hour: "numeric", minute: "2-digit", timeZone: e.timezone,
  }).format(new Date(e.start_utc));
}

export function formatPrice(e: EventItem) {
  if (e.is_free) return "Free";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: e.currency, maximumFractionDigits: 0 }).format(e.price_amount);
}

/** true if the event starts between now and the end of this coming weekend (Sat–Sun) */
export function isThisWeekend(e: EventItem, now: number) {
  const start = new Date(e.start_utc).getTime();
  const d = new Date(now);
  const daysToSunday = (7 - d.getDay()) % 7;
  const saturday = new Date(d.getFullYear(), d.getMonth(), d.getDate() + daysToSunday - 1).getTime();
  const endOfSunday = new Date(d.getFullYear(), d.getMonth(), d.getDate() + daysToSunday, 23, 59, 59).getTime();
  return start >= Math.max(now, saturday) && start <= endOfSunday;
}