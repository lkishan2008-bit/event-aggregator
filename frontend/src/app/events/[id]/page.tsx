import { Suspense } from "react";
import EventDetail from "@/components/EventDetail";

// The page for one event, e.g. /events/3
export default function EventPage({ params }: PageProps<"/events/[id]">) {
  return (
    <Suspense fallback={<div className="mx-auto mt-16 h-64 max-w-4xl animate-pulse rounded-2xl bg-line/60" />}>
      <EventFromUrl params={params} />
    </Suspense>
  );
}

async function EventFromUrl({ params }: { params: PageProps<"/events/[id]">["params"] }) {
  const { id } = await params;
  return <EventDetail id={id} />;
}