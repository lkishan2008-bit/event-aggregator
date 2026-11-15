const items = [
  { label: "Home", icon: "M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z", active: true },
  { label: "Explore", icon: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm10 17-5-5" },
  { label: "Saved", icon: "M6 3h12v18l-6-4-6 4z" },
  { label: "Passes", icon: "M3 7h18v4a2 2 0 0 0 0 4v4H3v-4a2 2 0 0 0 0-4z" },
  { label: "Profile", icon: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-8 9a8 8 0 0 1 16 0" },
];

export default function BottomNav() {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-10 bg-ink">
      <ul className="mx-auto flex max-w-md justify-around py-2.5">
        {items.map((it) => (
          <li key={it.label}>
            <a href="#" className={`flex flex-col items-center gap-1 text-[11px] ${it.active ? "text-accent" : "text-white/70 hover:text-white"}`}>
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d={it.icon} />
              </svg>
              {it.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}