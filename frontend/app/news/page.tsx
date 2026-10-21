import Shell from "@/components/Shell";

export default function News() {
  return (
    <Shell mode="live" asOf={null}>
      <div className="card tone-brand">
        <div className="mb-2 text-lg font-semibold">News &amp; sentiment</div>
        <p className="text-sm text-fg2">No news provider is connected, so this page shows nothing rather than invented headlines.</p>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-mute">
          <li>Headlines, publishers, timestamps and links need a licensed news API (for example Finnhub, Polygon or Alpaca News).</li>
          <li>Sentiment labels would come from a model run on those real articles, shown with the model name and its limits.</li>
          <li>Before connecting one, check its terms allow display in a public app.</li>
        </ul>
      </div>
    </Shell>
  );
}
