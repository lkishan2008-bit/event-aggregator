import { EventItem, formatEventTime, formatPrice, posterColor } from "@/lib/events";

export default function EventCard({ event, weekend }: { event: EventItem; weekend: boolean }) {
  return (
    <article className="overflow-hidden rounded-2xl border border-line bg-white">
      {/* poster placeholder: replace with <Image> once posters are uploaded */}
      <div className="relative flex aspect-[16/9] items-end p-4" style={{ background: posterColor(event) }}>
        <div className="absolute left-3 top-3 flex gap-1.5">
          {event.is_free && <span className="rounded-full bg-accent px-2.5 py-0.5 text-xs font-medium text-white">Free</span>}
          {weekend && <span className="rounded-full bg-white/20 px-2.5 py-0.5 text-xs font-medium text-white">This weekend</span>}
        </div>
        <h2 className="font-display text-2xl font-bold leading-tight text-white">{event.title}</h2>
      </div>

      <div className="space-y-1.5 px-4 py-3 text-sm text-muted">
        <p>{formatEventTime(event)}</p>
        {event.venue && <p>{event.venue.name} · {event.venue.city}</p>}
        <div className="flex items-center justify-between pt-2">
          <span className="text-xs">{event.going.toLocaleString("en-IN")} going · {formatPrice(event)}</span>
          <button className="rounded-full bg-accent px-4 py-1.5 text-sm font-medium text-white hover:bg-accent-dark">
            Register
          </button>
        </div>
      </div>
    </article>
  );
}