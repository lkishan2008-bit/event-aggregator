import EventFeed from "@/components/EventFeed";
import UserBadge from "@/components/UserBadge";

export default function Home() {
  return (
    <main className="px-4 pt-6">
      <header className="mb-5 flex items-end justify-between">
        <div>
          <p className="text-sm text-muted">Bengaluru</p>
          <h1 className="font-display text-3xl font-bold text-night">What&apos;s on</h1>
        </div>
        <UserBadge />
      </header>
      <EventFeed />
    </main>
  );
}