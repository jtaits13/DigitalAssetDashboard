"use client";

import { formatPct, formatUsdCompact } from "@/lib/format";
import type { StablecoinSummary } from "@/lib/rwa";
import Link from "next/link";
import { useEffect, useState } from "react";

export function StablecoinWidget() {
  const [data, setData] = useState<StablecoinSummary | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/stablecoins/summary");
        if (!res.ok) throw new Error("Failed to load");
        const json = (await res.json()) as StablecoinSummary;
        if (!cancelled) setData(json);
      } catch {
        if (!cancelled) setErr("Could not load metrics");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="flex h-full flex-col rounded-xl border border-[var(--border)] bg-[var(--card)] p-6 shadow-lg shadow-black/20">
      <Link
        href="/stablecoins"
        className="inline-flex w-full items-center justify-center rounded-md border border-[var(--border)] bg-zinc-900/80 px-3 py-2 text-sm font-medium text-zinc-100 transition hover:border-blue-500/50 hover:bg-zinc-800"
      >
        Additional Data
      </Link>
      <h2 className="mt-5 text-sm font-semibold uppercase tracking-wider text-zinc-500">Stablecoins</h2>
      <p className="mt-1 text-xs text-zinc-600">Totals reflect RWA.xyz &quot;Stablecoins&quot; asset class when an API key is configured.</p>

      <div className="mt-6 grid flex-1 gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-[var(--border)] bg-black/20 p-4">
          <p className="text-xs text-zinc-500">Total value</p>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-white">
            {data ? formatUsdCompact(data.totalValueUsd) : "—"}
          </p>
        </div>
        <div className="rounded-lg border border-[var(--border)] bg-black/20 p-4">
          <p className="text-xs text-zinc-500">1 month change</p>
          <p
            className={`mt-2 text-2xl font-semibold tabular-nums ${
              data?.change30dPct == null
                ? "text-zinc-300"
                : data.change30dPct >= 0
                  ? "text-emerald-400"
                  : "text-rose-400"
            }`}
          >
            {data ? formatPct(data.change30dPct) : "—"}
          </p>
        </div>
      </div>

      {err && <p className="mt-4 text-xs text-rose-400">{err}</p>}
      {data?.source === "mock" && (
        <p className="mt-4 text-xs text-amber-200/80">
          Showing illustrative figures. Add <code className="rounded bg-black/30 px-1">RWA_API_KEY</code> in{" "}
          <code className="rounded bg-black/30 px-1">.env.local</code> for live RWA.xyz data.
        </p>
      )}
    </section>
  );
}
