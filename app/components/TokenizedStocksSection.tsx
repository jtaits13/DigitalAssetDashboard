"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { StocksPlatformRow, StocksToplineMetric, TokenizedStocksData } from "@/lib/tokenizedStocks";

type Props = {
  compact?: boolean;
};

function metricTone(change: string | null): string {
  if (!change) return "text-zinc-400";
  return change.startsWith("-") ? "text-rose-400" : "text-emerald-400";
}

function rowTone(change: string | null): string {
  if (!change) return "text-zinc-500";
  return change.startsWith("-") ? "text-rose-400" : "text-emerald-400";
}

export function TokenizedStocksSection({ compact = false }: Props) {
  const [data, setData] = useState<TokenizedStocksData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/tokenized-stocks");
        if (!res.ok) throw new Error("Request failed");
        const json = (await res.json()) as TokenizedStocksData;
        if (!cancelled) setData(json);
      } catch {
        if (!cancelled) setErr("Could not load Tokenized Stocks data.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const metrics: StocksToplineMetric[] = data?.metrics ?? [];
  const rows = useMemo(() => {
    const all = data?.rows ?? [];
    if (compact) return all.slice(0, 10);
    if (!query.trim()) return all;
    const q = query.trim().toLowerCase();
    return all.filter((r) => r.platform.toLowerCase().includes(q));
  }, [compact, data?.rows, query]);

  return (
    <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-6 shadow-lg shadow-black/20">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-500">Tokenized Stocks</h2>
      <p className="mt-1 max-w-4xl text-xs text-zinc-600">
        Distributed table from RWA.xyz Tokenized Stocks, scraped from the page HTML and sorted by platform.
      </p>

      {metrics.length > 0 && (
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {metrics.map((m) => (
            <div key={m.label} className="rounded-lg border border-[var(--border)] bg-black/20 p-4">
              <p className="text-xs text-zinc-500">{m.label}</p>
              <p className="mt-1 text-lg font-semibold tabular-nums text-white">{m.value}</p>
              <p className={`mt-1 text-xs tabular-nums ${metricTone(m.change30d)}`}>{m.change30d ?? "—"}</p>
            </div>
          ))}
        </div>
      )}

      {!compact && (
        <div className="mt-5">
          <label className="text-xs text-zinc-500" htmlFor="stocks-platform-filter">
            Search platform
          </label>
          <input
            id="stocks-platform-filter"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter by platform..."
            className="mt-2 w-full rounded-md border border-[var(--border)] bg-black/20 px-3 py-2 text-sm text-zinc-100 outline-none ring-blue-400/40 placeholder:text-zinc-500 focus:ring-2"
          />
        </div>
      )}

      <div className="mt-6 overflow-x-auto rounded-lg border border-[var(--border)]">
        <table className="w-full min-w-[760px] border-collapse text-left text-sm">
          <thead className="bg-[#0f141c]">
            <tr className="border-b border-[var(--border)] text-xs uppercase tracking-wide text-zinc-500">
              <th className="px-3 py-2 font-medium">#</th>
              <th className="px-3 py-2 font-medium">Platform</th>
              <th className="px-3 py-2 font-medium">RWA Count</th>
              <th className="px-3 py-2 font-medium">Distributed Value</th>
              <th className="px-3 py-2 font-medium">30D %</th>
              <th className="px-3 py-2 font-medium">Market Share</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row: StocksPlatformRow, idx) => (
              <tr key={`${row.platform}-${idx}`} className="border-b border-[var(--border)]/80 hover:bg-white/5">
                <td className="px-3 py-3 text-zinc-400">{row.rank}</td>
                <td className="px-3 py-3 font-medium text-zinc-200">{row.platform}</td>
                <td className="px-3 py-3 tabular-nums text-zinc-400">
                  {row.rwaCount != null ? row.rwaCount.toLocaleString() : "—"}
                </td>
                <td className="px-3 py-3 tabular-nums text-zinc-300">{row.distributedValue}</td>
                <td className={`px-3 py-3 tabular-nums ${rowTone(row.change30d)}`}>{row.change30d ?? "—"}</td>
                <td className="px-3 py-3 tabular-nums text-zinc-400">{row.marketShare ?? "—"}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-zinc-500">
                  No rows found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {compact ? (
        <>
          <Link
            href="/tokenized-stocks"
            className="mt-5 inline-flex w-full items-center justify-center rounded-md border border-[var(--border)] bg-cyan-700/90 px-3 py-2 text-sm font-medium text-white transition hover:bg-cyan-600"
          >
            Open full Tokenized Stocks table
          </Link>
          <a
            href={data?.rwaUrl ?? "https://app.rwa.xyz/stocks"}
            target="_blank"
            rel="noreferrer"
            className="mt-2 inline-flex w-full items-center justify-center rounded-md border border-[var(--border)] bg-zinc-900/80 px-3 py-2 text-sm text-zinc-200 transition hover:border-blue-500/50 hover:bg-zinc-800"
          >
            See Tokenized Stocks on RWA.xyz
          </a>
        </>
      ) : (
        <div className="mt-4 flex flex-wrap gap-4 text-sm">
          <Link href="/" className="text-zinc-400 underline-offset-2 hover:text-white hover:underline">
            ← Back to home
          </Link>
          <a
            href={data?.rwaUrl ?? "https://app.rwa.xyz/stocks"}
            target="_blank"
            rel="noreferrer"
            className="text-blue-400 underline-offset-2 hover:underline"
          >
            See Tokenized Stocks on RWA.xyz
          </a>
        </div>
      )}

      {err && <p className="mt-4 text-xs text-rose-400">{err}</p>}
      {data?.source === "fallback" && (
        <p className="mt-4 text-xs text-amber-200/80">
          Live scrape fallback is active. Values are from the latest captured Tokenized Stocks snapshot.
        </p>
      )}
    </section>
  );
}
