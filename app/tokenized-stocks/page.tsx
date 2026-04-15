import { TokenizedStocksSection } from "../components/TokenizedStocksSection";

export default function TokenizedStocksPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-white">Tokenized Stocks</h1>
        <p className="mt-2 max-w-3xl text-zinc-400">
          Topline Tokenized Stocks metrics and the full distributed platform table from RWA.xyz, scraped from page
          HTML.
        </p>
      </div>
      <TokenizedStocksSection />
    </div>
  );
}
