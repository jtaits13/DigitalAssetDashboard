import { NewsSection } from "./components/NewsSection";
import { CryptoETPsSection } from "./components/CryptoETPsSection";
import { StablecoinWidget } from "./components/StablecoinWidget";
import { TokenizedStocksSection } from "./components/TokenizedStocksSection";

export default function HomePage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-white">Overview</h1>
        <p className="mt-2 max-w-2xl text-zinc-400">
          Market snapshot: headlines and stablecoin aggregates (via RWA.xyz when configured).
        </p>
      </div>
      <div className="grid gap-6 lg:grid-cols-2 lg:items-start">
        <NewsSection />
        <StablecoinWidget />
      </div>
      <TokenizedStocksSection compact />
      <CryptoETPsSection />
    </div>
  );
}
