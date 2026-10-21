import type { NewsItem } from "@/lib/api";
import { timeAgo } from "@/lib/ui";

const TONE: Record<string, string> = {
  Positive: "bg-up/15 text-up", Negative: "bg-down/15 text-down", Neutral: "bg-mute/20 text-mute",
};

export default function NewsList({ items, compact = false }: { items: NewsItem[]; compact?: boolean }) {
  return (
    <div>
      {items.map((n, i) => (
        <div key={n.url + i} className="border-t border-line py-3 first:border-t-0 first:pt-0">
          <a href={n.url} target="_blank" rel="noopener noreferrer"
            className={`block font-medium leading-snug hover:text-brand ${compact ? "text-sm" : "text-base"}`}>{n.title}</a>
          <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-mute">
            <span className={`rounded-full px-2 py-0.5 font-medium ${TONE[n.sentiment] ?? TONE.Neutral}`}>{n.sentiment}</span>
            {n.tickers.map((t) => <span key={t.ticker} className="rounded bg-fg/5 px-1.5 py-0.5 font-medium text-fg2">{t.ticker}</span>)}
            <span>{n.publisher ?? "Unknown source"}</span>
            {n.published_at && <span>&middot; {timeAgo(n.published_at)}</span>}
          </div>
        </div>))}
    </div>
  );
}
