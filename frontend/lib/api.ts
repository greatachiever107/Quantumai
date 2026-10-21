export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type Forecast = {
  ticker: string; recent_vol_ann_pct: number; forecast_vol_ann_pct: number; change_pct: number;
  typical_daily_move_pct: number; earnings_in_window: boolean; next_earnings: string | null; regime: string | null;
};
export type ForecastsResp = { data_mode: string; as_of: string | null; note: string; items: Forecast[] };
export type Candle = { date: string; open: number; high: number; low: number; close: number; volume: number | null };
export type CandlesResp = { data_mode: string; ticker: string; candles: Candle[] };
export type Row = Record<string, string | number | null>;
export type ListResp = { data_mode: string; note?: string; items: Row[] };

function key(): Record<string, string> {
  try { const k = localStorage.getItem("access_key"); return k ? { "x-access-key": k } : {}; } catch { return {}; }
}
function check(r: Response, path: string) {
  if (r.status === 401 && typeof window !== "undefined") window.dispatchEvent(new Event("locked"));
  if (!r.ok) throw new Error(`${path} returned ${r.status}`);
}

export async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API}/api/v1${path}`, { cache: "no-store", headers: key() });
  check(r, path);
  return r.json();
}
export async function put<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API}/api/v1${path}`, {
    method: "PUT", headers: { "Content-Type": "application/json", ...key() }, body: JSON.stringify(body),
  });
  check(r, path);
  return r.json();
}
