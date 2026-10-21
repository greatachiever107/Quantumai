export const REGIME: Record<string, string> = {
  Calm: "bg-up/15 text-up", Normal: "bg-mute/20 text-fg2",
  Elevated: "bg-warn/20 text-warn", High: "bg-down/20 text-down",
};
export const pct = (n: number) => `${n >= 0 ? "\u25B2" : "\u25BC"} ${Math.abs(n)}%`;
export const Badge = ({ r }: { r: string | null }) =>
  r ? <span className={`rounded px-2 py-0.5 text-xs ${REGIME[r] ?? ""}`}>{r}</span> : <span className="text-mute">-</span>;
