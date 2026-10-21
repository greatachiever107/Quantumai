"use client";
import { useEffect, useState } from "react";

export type Theme = "dark" | "light";

export function useTheme(): Theme {
  const [t, setT] = useState<Theme>("dark");
  useEffect(() => {
    const el = document.documentElement;
    const read = () => setT(el.classList.contains("dark") ? "dark" : "light");
    read();
    const mo = new MutationObserver(read);
    mo.observe(el, { attributes: true, attributeFilter: ["class"] });
    return () => mo.disconnect();
  }, []);
  return t;
}

export const chartColors = (t: Theme) =>
  t === "dark" ? { text: "#94a3b8", grid: "#1f2a44" } : { text: "#64748b", grid: "#e2e8f0" };
