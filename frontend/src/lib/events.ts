// Sample data until the Flask API serves real events.
// Global-ready: times in UTC + the event's IANA timezone, price + ISO currency.

export type EventItem = {
  id: number;
  title: string;
  category: "fest" | "hackathon" | "workshop" | "meetup";
  startUtc: string;
  timezone: string;
  venue: string;
  city: string;
  distanceKm: number;
  priceAmount: number;
  currency: string;
  going: number;
  posterColor: string; // placeholder until real poster images
};

export const CATEGORIES = [
  { key: "all", label: "All" },
  { key: "fest", label: "Fests" },
  { key: "hackathon", label: "Hackathons" },
  { key: "workshop", label: "Workshops" },
  { key: "meetup", label: "Meetups" },
] as const;

export const SAMPLE_EVENTS: EventItem[] = [
  { id: 1, title: "HackRV 3.0", category: "hackathon", startUtc: "2026-11-22T03:30:00Z", timezone: "Asia/Kolkata", venue: "RVCE, Mysore Road", city: "Bengaluru", distanceKm: 4.2, priceAmount: 0, currency: "INR", going: 312, posterColor: "#2f5bff" },
  { id: 2, title: "8th Mile Cultural Fest", category: "fest", startUtc: "2026-11-28T06:30:00Z", timezone: "Asia/Kolkata", venue: "RVCE Main Grounds", city: "Bengaluru", distanceKm: 4.2, priceAmount: 199, currency: "INR", going: 1840, posterColor: "#c2185b" },
  { id: 3, title: "Intro to CRISPR Workshop", category: "workshop", startUtc: "2026-11-21T08:30:00Z", timezone: "Asia/Kolkata", venue: "IISc, Malleshwaram", city: "Bengaluru", distanceKm: 14.8, priceAmount: 0, currency: "INR", going: 86, posterColor: "#0e7c7b" },
  { id: 4, title: "BangPypers Monthly Meetup", category: "meetup", startUtc: "2026-11-23T05:30:00Z", timezone: "Asia/Kolkata", venue: "Koramangala", city: "Bengaluru", distanceKm: 11.3, priceAmount: 0, currency: "INR", going: 140, posterColor: "#6d4c41" },
  { id: 5, title: "UI/UX Design Sprint", category: "workshop", startUtc: "2026-12-05T04:30:00Z", timezone: "Asia/Kolkata", venue: "PES University", city: "Bengaluru", distanceKm: 9.1, priceAmount: 299, currency: "INR", going: 64, posterColor: "#ef6c00" },
];

export function formatEventTime(e: EventItem) {
  return new Intl.DateTimeFormat("en-IN", {
    weekday: "short", day: "numeric", month: "short",
    hour: "numeric", minute: "2-digit", timeZone: e.timezone,
  }).format(new Date(e.startUtc));
}

export function formatPrice(e: EventItem) {
  if (e.priceAmount === 0) return "Free";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: e.currency, maximumFractionDigits: 0 }).format(e.priceAmount);
}

/** true if the event starts between now and the end of this coming weekend (Sat–Sun) */
export function isThisWeekend(e: EventItem, now: number) {
  const start = new Date(e.startUtc).getTime();
  const d = new Date(now);
  const daysToSunday = (7 - d.getDay()) % 7;
  const saturday = new Date(d.getFullYear(), d.getMonth(), d.getDate() + daysToSunday - 1).getTime();
  const endOfSunday = new Date(d.getFullYear(), d.getMonth(), d.getDate() + daysToSunday, 23, 59, 59).getTime();
  return start >= Math.max(now, saturday) && start <= endOfSunday;
}