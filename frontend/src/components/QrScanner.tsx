"use client";

import { useEffect, useRef, useState } from "react";

/** Opens the camera and calls onScan with the text inside each QR code it sees. */
export default function QrScanner({ onScan }: { onScan: (text: string) => void }) {
  const [error, setError] = useState("");
  const onScanRef = useRef(onScan);
  useEffect(() => { onScanRef.current = onScan; }, [onScan]);

  useEffect(() => {
    let stopped = false;
    let scanner: import("html5-qrcode").Html5Qrcode | null = null;
    let last = { text: "", at: 0 };

    // the library touches the camera, so load it only in the browser
    import("html5-qrcode").then(({ Html5Qrcode }) => {
      if (stopped) return;
      scanner = new Html5Qrcode("qr-reader");
      scanner
        .start(
          { facingMode: "environment" }, // back camera on phones
          { fps: 10, qrbox: { width: 230, height: 230 } },
          (text) => {
            const now = Date.now();
            if (text === last.text && now - last.at < 3000) return; // same pass held in front of the camera
            last = { text, at: now };
            onScanRef.current(text);
          },
          () => {}, // "no QR in this frame" - ignore
        )
        .catch(() => setError("Couldn't open the camera. Allow camera access, or type the pass code below."));
    });

    return () => {
      stopped = true;
      if (scanner?.isScanning) scanner.stop().then(() => scanner?.clear()).catch(() => {});
    };
  }, []);

  return (
    <div>
      <div id="qr-reader" className="overflow-hidden rounded-2xl bg-night" />
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}