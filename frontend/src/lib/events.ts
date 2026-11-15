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
  venue: { name: string; address: string | null; city: string; country_code: string } | null;
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