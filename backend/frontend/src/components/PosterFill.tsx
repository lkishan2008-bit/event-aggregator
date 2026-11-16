"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/auth";

export type PosterFields = Partial<{
  title: string; category: string; description: string; date: string; start: string; end: string;
  venue: string; city: string; price: number; link: string;
}>;

const LABELS: Record<string, string> = {
  title: "title", category: "category", date: "date", start: "start time", end: "end time",
  venue: "venue", city: "city", price: "price", link: "link", description: "description",
};

/** Shrink big phone photos before upload (max 1600px, JPEG) so they upload fast. */
function shrinkImage(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, 1600 / Math.max(img.width, img.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(img.width * scale);
      canvas.height = Math.round(img.height * scale);
      canvas.getContext("2d")!.drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(img.src);
      resolve(canvas.toDataURL("image/jpeg", 0.85));
    };
    img.onerror = () => reject(new Error("That file isn't an image this browser can open. Try a JPG or PNG."));
    img.src = URL.createObjectURL(file);
  });
}

/** "Fill from poster": upload a poster photo (or paste its text) and pre-fill the form. */
export default function PosterFill({ onFill }: { onFill: (fields: PosterFields) => void }) {
  const [mode, setMode] = useState<"photo" | "text">("photo");
  const [text, setText] = useState("");
  const [preview, setPreview] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [filled, setFilled] = useState<string[] | null>(null);

  async function scan(body: { image_base64?: string; text?: string }) {
    setBusy(true);
    setError("");
    setFilled(null);
    try {
      const d = await apiFetch("/api/organizer/poster/scan", { method: "POST", body: JSON.stringify(body) });
      const fields = d.fields as PosterFields;
      onFill(fields);
      setFilled(Object.keys(fields).map((k) => LABELS[k] ?? k));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't read the poster.");
    } finally {
      setBusy(false);
    }
  }

  async function onFile(file: File | undefined) {
    if (!file) return;
    try {
      const dataUrl = await shrinkImage(file);
      setPreview(dataUrl);
      await scan({ image_base64: dataUrl });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't open the image.");
    }
  }

  const tab = (m: "photo" | "text", label: string) => (
    <button
      type="button"
      onClick={() => setMode(m)}
      className={`rounded-full px-3 py-1 text-xs font-medium ${mode === m ? "bg-night text-white" : "text-muted hover:text-night"}`}
    >
      {label}
    </button>
  );

  return (
    <section className="rounded-2xl border border-dashed border-accent bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="font-display text-lg font-bold text-night">Fill from poster</h2>
          <p className="text-xs text-muted">Upload your event poster and we&apos;ll fill the form for you.</p>
        </div>
        <div className="flex gap-1 rounded-full border border-line p-1">
          {tab("photo", "Photo")}
          {tab("text", "Paste text")}
        </div>
      </div>

      {mode === "photo" ? (
        <label className="mt-4 flex cursor-pointer items-center gap-4 rounded-xl border border-line px-4 py-3 hover:border-muted">
          {preview
            // eslint-disable-next-line @next/next/no-img-element -- local preview of the chosen file
            ? <img src={preview} alt="Poster preview" className="h-16 w-16 rounded-lg object-cover" />
            : <span className="flex h-16 w-16 items-center justify-center rounded-lg bg-paper text-2xl text-muted">+</span>}
          <span className="text-sm text-night">{busy ? "Reading poster\u2026" : preview ? "Choose another poster" : "Choose a poster photo"}</span>
          <input type="file" accept="image/*" className="hidden" disabled={busy} onChange={(e) => onFile(e.target.files?.[0])} />
        </label>
      ) : (
        <div className="mt-4 space-y-2">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste the poster text or Instagram caption here"
            className="min-h-28 w-full rounded-xl border border-line px-4 py-2.5 text-sm text-night outline-none focus:border-ink"
          />
          <button
            type="button"
            disabled={busy || !text.trim()}
            onClick={() => scan({ text })}
            className="rounded-full bg-night px-5 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {busy ? "Reading\u2026" : "Fill the form"}
          </button>
        </div>
      )}

      {filled && (
        <p className="mt-3 rounded-xl bg-green-50 px-4 py-2.5 text-sm text-green-800">
          {filled.length
            ? `Filled: ${filled.join(", ")}. Check everything below before submitting.`
            : "Couldn't find event details in that poster. Fill the form by hand."}
        </p>
      )}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </section>
  );
}