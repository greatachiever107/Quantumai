export const REGIME: Record<string, string> = {
  Calm: "bg-up/15 text-up", Normal: "bg-mute/20 text-fg2",
  Elevated: "bg-warn/20 text-warn", High: "bg-down/20 text-down",
};
export const pct = (n: number) => `${n >= 0 ? "\u25B2" : "\u25BC"} ${Math.abs(n)}%`;
export const Badge = ({ r }: { r: string | null }) =>
  r ? <span className={`rounded px-2 py-0.5 text-xs ${REGIME[r] ?? ""}`}>{r}</span> : <span className="text-mute">-</span>;

export function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (m < 60) return `${m}m ago`;
  if (m < 60 * 24) return `${Math.round(m / 60)}h ago`;
  return `${Math.round(m / 1440)}d ago`;
}
