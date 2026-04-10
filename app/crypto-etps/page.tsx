import { CryptoETPsSection } from "../components/CryptoETPsSection";

export default function CryptoEtpsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-white">Crypto ETPs</h1>
        <p className="mt-2 max-w-2xl text-zinc-400">
          Spot crypto exchange-traded products: SEC fund filing index links resolved by ticker and trust CIK.
        </p>
      </div>
      <CryptoETPsSection />
    </div>
  );
}
