"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSession } from "@/lib/auth";
import { EventItem, formatPrice } from "@/lib/events";
import {
  cancelRegistration, getMyRegistration, PaymentOrder, payWithRazorpay, Registration, registerFor, verifyPayment,
} from "@/lib/registrations";

/** The Register / Pay / You're going box on the event page. */
export default function RegisterBox({ event, onGoingChange }: { event: EventItem; onGoingChange: (going: number) => void }) {
  const session = useSession();
  const [reg, setReg] = useState<Registration | null | undefined>(undefined); // undefined = still checking
  const [mockOrder, setMockOrder] = useState<PaymentOrder | null>(null); // demo payment screen
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const paid = !event.is_free && event.price_amount > 0;

  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    getMyRegistration(event.id)
      .then((r) => { if (!cancelled) setReg(r); })
      .catch(() => { if (!cancelled) setReg(null); });
    return () => { cancelled = true; };
  }, [session, event.id]);

  const primary = "block w-full rounded-full bg-accent py-3 text-center text-sm font-medium text-white hover:bg-accent-dark disabled:opacity-60";

  if (event.external) {
    return (
      <div className="space-y-2">
        <a href={event.registration_url ?? "#"} target="_blank" rel="noopener noreferrer" className={primary}>
          Get tickets {"\u2197"}
        </a>
        <p className="text-center text-xs text-muted">Tickets are sold on the organizer&apos;s site.</p>
      </div>
    );
  }
  if (!session) {
    return <Link href="/login" className={primary}>Log in to register</Link>;
  }
  if (reg === undefined) {
    return <div className="h-11 animate-pulse rounded-full bg-line/60" />;
  }

  function confirmed(r: Registration) {
    setReg(r.status === "registered" ? r : null);
    if (r.event) onGoingChange(r.event.going);
  }

  async function run(task: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await task();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  const register = () => run(async () => {
    const { registration, payment } = await registerFor(event.id);
    if (!payment) return confirmed(registration); // free event (or already registered)
    if (payment.mock) return setMockOrder(payment); // no Razorpay keys: show the demo payment screen
    const signed = await payWithRazorpay(payment);
    if (!signed) return setError("Payment cancelled. Your seat isn't booked yet.");
    confirmed(await verifyPayment(event.id, signed));
  });

  const payMock = () => run(async () => {
    const order = mockOrder!;
    setMockOrder(null);
    confirmed(await verifyPayment(event.id, { order_id: order.id, payment_id: `pay_mock_${Date.now()}`, signature: "mock-paid" }));
  });

  const cancel = () => run(async () => confirmed(await cancelRegistration(event.id)));

  if (reg) {
    return (
      <div className="space-y-2">
        <p className="rounded-xl bg-green-50 px-4 py-2.5 text-center text-sm font-medium text-green-800">
          {"\u2713"} You&apos;re going{reg.amount_paid > 0 && ` \u00b7 paid ${formatPrice(event)}`}
        </p>
        <Link href="/passes" className={primary}>View my pass</Link>
        {reg.amount_paid > 0 ? (
          <p className="text-center text-xs text-muted">Paid tickets: contact the organizer for refunds.</p>
        ) : (
          <button onClick={cancel} disabled={busy} className="w-full py-1 text-sm text-muted underline hover:text-night disabled:opacity-60">
            {busy ? "Cancelling\u2026" : "Cancel registration"}
          </button>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    );
  }

  if (mockOrder) {
    return (
      <div className="space-y-3 rounded-xl border border-dashed border-accent p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-accent">Test payment</p>
        <p className="text-sm text-night">
          Pay <b>{formatPrice(event)}</b> for {event.title}. Demo mode: no real money is charged.
        </p>
        <button onClick={payMock} disabled={busy} className={primary}>{busy ? "Paying\u2026" : `Pay ${formatPrice(event)}`}</button>
        <button onClick={() => setMockOrder(null)} className="w-full text-sm text-muted underline">Cancel</button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <button onClick={register} disabled={busy} className={primary}>
        {busy ? "Please wait\u2026" : paid ? `Pay ${formatPrice(event)} & register` : "Register"}
      </button>
      {paid && <p className="text-center text-xs text-muted">UPI, cards and netbanking via Razorpay</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}