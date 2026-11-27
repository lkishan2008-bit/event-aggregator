import EventFeed from "@/components/EventFeed";
import UserBadge from "@/components/UserBadge";

export default function Home() {
  return (
    <main className="px-4 pt-6 md:px-6 md:pt-10">      <header className="mb-5 flex items-end justify-between">
      <div>
        <p className="text-sm text-muted">Local festivals, temple fairs, markets and events near you</p>
        <h1 className="font-display text-3xl font-bold text-night md:text-4xl">What&apos;s on</h1>
      </div>
      {/* on laptops the badge is in the top bar */}
      <div className="md:hidden"><UserBadge /></div>
    </header>
      <EventFeed />
    </main>
  );
}