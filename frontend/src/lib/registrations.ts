// Registering for events, paying for paid tickets, and the user's QR passes.

import { apiFetch } from "@/lib/auth";
import { EventItem } from "@/lib/events";

export type Registration = {
  id: number;
  status: "registered" | "pending_payment" | "cancelled";
  qr_token: string | null; // only set once the ticket is confirmed
  amount_paid: number;
  checked_in_at: string | null;
  created_at: string;
  event?: EventItem;
};

/** A payment order to open in Razorpay Checkout (mock = fake test screen when no Razorpay keys are set). */
export type PaymentOrder = {
  id: string;
  amount: number; // in paise
  currency: string;
  key_id: string | null;
  mock: boolean;
  event_title: string;
  name: string;
  email: string;
};

export async function getMyRegistration(eventId: number): Promise<Registration | null> {
  const d = await apiFetch(`/api/events/${eventId}/my-registration`);
  return d.registration;
}

export async function registerFor(eventId: number): Promise<{ registration: Registration; payment?: PaymentOrder }> {
  return apiFetch(`/api/events/${eventId}/register`, { method: "POST" });
}

export async function verifyPayment(eventId: number, p: { order_id: string; payment_id: string; signature: string }): Promise<Registration> {
  const d = await apiFetch(`/api/events/${eventId}/pay/verify`, { method: "POST", body: JSON.stringify(p) });
  return d.registration;
}

export async function cancelRegistration(eventId: number): Promise<Registration> {
  const d = await apiFetch(`/api/events/${eventId}/register`, { method: "DELETE" });
  return d.registration;
}

export async function getMyPasses(): Promise<Registration[]> {
  const d = await apiFetch("/api/me/registrations");
  return d.registrations;
}

// ---------- Razorpay Checkout ----------

type RazorpayResponse = { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string };
type RazorpayCheckout = { open: () => void; on: (event: string, cb: () => void) => void };
declare global {
  interface Window { Razorpay?: new (options: Record<string, unknown>) => RazorpayCheckout }
}

function loadRazorpay(): Promise<void> {
  if (window.Razorpay) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Couldn't load the payment window. Check your internet."));
    document.body.appendChild(s);
  });
}

/** Opens Razorpay Checkout. Resolves with the signed payment, or null if the user closed the window. */
export async function payWithRazorpay(order: PaymentOrder): Promise<{ order_id: string; payment_id: string; signature: string } | null> {
  await loadRazorpay();
  return new Promise((resolve) => {
    const rzp = new window.Razorpay!({
      key: order.key_id,
      amount: order.amount,
      currency: order.currency,
      order_id: order.id,
      name: "Event Aggregator",
      description: order.event_title,
      prefill: { name: order.name, email: order.email },
      theme: { color: "#ff5a1f" },
      handler: (r: RazorpayResponse) => resolve({ order_id: r.razorpay_order_id, payment_id: r.razorpay_payment_id, signature: r.razorpay_signature }),
      modal: { ondismiss: () => resolve(null) },
    });
    rzp.on("payment.failed", () => {}); // Razorpay shows the error and lets the user retry
    rzp.open();
  });
}