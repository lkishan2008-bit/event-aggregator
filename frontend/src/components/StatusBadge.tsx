const STYLES: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  cancelled: "bg-line text-muted",
  completed: "bg-line text-muted",
};

const LABELS: Record<string, string> = {
  pending: "Waiting for approval",
  approved: "Live",
  rejected: "Rejected",
  cancelled: "Cancelled",
  completed: "Completed",
};

export default function StatusBadge({ status }: { status?: string }) {
  if (!status) return null;
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[status] ?? "bg-line text-muted"}`}>{LABELS[status] ?? status}</span>;
}