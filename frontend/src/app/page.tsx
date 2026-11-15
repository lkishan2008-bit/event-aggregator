import EventFeed from "@/components/EventFeed";
import { SAMPLE_EVENTS } from "@/lib/events";

export default function Home() {
  return (
    <main className="px-4 pt-6">
      <header className="mb-5 flex items-end justify-between">
        <div>
          <p className="text-sm text-muted">Bengaluru</p>
          <h1 className="font-display text-3xl font-bold text-night">What&apos;s on</h1>
        </div>
        <span className="rounded-full bg-ink px-3 py-1 text-xs font-medium text-white">Students</span>
      </header>
      <EventFeed events={SAMPLE_EVENTS} />
    </main>
  );
}