// Navigation links shared by the top bar (laptop) and bottom bar (phone).

export const APP_NAME = "Event Aggregator";

export const NAV_ITEMS = [
  { label: "Home", href: "/", icon: "M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" },
  { label: "Explore", href: "/", icon: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm10 17-5-5" },
  { label: "Saved", href: "/saved", icon: "M6 3h12v18l-6-4-6 4z" },
  { label: "Passes", href: "/passes", icon: "M3 7h18v4a2 2 0 0 0 0 4v4H3v-4a2 2 0 0 0 0-4z" },
  { label: "Profile", href: "/profile", icon: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-8 9a8 8 0 0 1 16 0" },
];

/** Which tab should be highlighted for the current page. */
export function activeTab(pathname: string) {
  if (pathname.startsWith("/saved")) return "Saved";
  if (pathname.startsWith("/passes")) return "Passes";
  if (pathname.startsWith("/profile") || pathname === "/login" || pathname === "/signup") return "Profile";
  return "Home";
}