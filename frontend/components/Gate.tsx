"use client";
import { useEffect, useState } from "react";

export default function Gate() {
  const [locked, setLocked] = useState(false);
  const [k, setK] = useState("");
  useEffect(() => {
    const f = () => setLocked(true);
    window.addEventListener("locked", f);
    return () => window.removeEventListener("locked", f);
  }, []);
  if (!locked) return null;
  const go = () => { try { localStorage.setItem("access_key", k.trim()); } catch {} location.reload(); };
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-bg/90 p-4 backdrop-blur">
      <div className="card tone-brand w-full max-w-sm">
        <div className="mb-1 text-lg font-semibold">Private dashboard</div>
        <div className="mb-3 text-sm text-mute">Enter the access key to view forecasts.</div>
        <input type="password" value={k} onChange={(e) => setK(e.target.value)} onKeyDown={(e) => e.key === "Enter" && go()}
          placeholder="Access key" className="mb-3 w-full rounded-xl border border-line bg-bg/60 px-3 py-2 text-sm outline-none focus:border-brand" />
        <button onClick={go} className="w-full rounded-xl bg-gradient-to-r from-brand to-ai px-3 py-2 text-sm font-semibold text-white">Unlock</button>
      </div>
    </div>
  );
}
