"use client";

import { formatPct, formatUsdCompact } from "@/lib/format";
import type { IssuerRow, VolumePoint, VolumeRange } from "@/lib/rwa";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const RANGES: { id: VolumeRange; label: string }[] = [
  { id: "1m", label: "1M" },
  { id: "3m", label: "3M" },
  { id: "6m", label: "6M" },
  { id: "1y", label: "1Y" },
  { id: "5y", label: "5Y" },
];

const BAR_FILL = "#3b82f6";

export function StablecoinAnalytics() {
  const [range, setRange] = useState<VolumeRange>("1m");
  const [volume, setVolume] = useState<VolumePoint[]>([]);
  const [volSource, setVolSource] = useState<"rwa" | "mock">("mock");
  const [issuers, setIssuers] = useState<IssuerRow[]>([]);
  const [loadingVol, setLoadingVol] = useState(true);

  const loadVolume = useCallback(async (r: VolumeRange) => {
    setLoadingVol(true);
    try {
      const res = await fetch(`/api/stablecoins/volume?range=${r}`);
      const json = (await res.json()) as { points: VolumePoint[]; source: "rwa" | "mock" };
      setVolume(json.points ?? []);
      setVolSource(json.source ?? "mock");
    } catch {
      setVolume([]);
    } finally {
      setLoadingVol(false);
    }
  }, []);

  useEffect(() => {
    loadVolume(range);
  }, [range, loadVolume]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/stablecoins/issuers");
        const json = (await res.json()) as { issuers: IssuerRow[] };
        if (!cancelled) setIssuers(json.issuers ?? []);
      } catch {
        if (!cancelled) setIssuers([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const chartData = useMemo(
    () =>
      volume.map((p) => ({
        ...p,
        label: p.date.slice(5),
      })),
    [volume],
  );

  const barData = useMemo(
    () =>
      [...issuers]
        .sort((a, b) => b.totalValueUsd - a.totalValueUsd)
        .map((r) => ({
          name: r.name.length > 28 ? `${r.name.slice(0, 26)}…` : r.name,
          fullName: r.name,
          value: r.totalValueUsd,
          change30: r.change30dPct,
          share: r.marketSharePct,
        })),
    [issuers],
  );

  return (
    <div className="space-y-10">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white">Stablecoin metrics</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Aggregates from{" "}
            <a
              href="https://rwa.xyz"
              target="_blank"
              rel="noreferrer"
              className="text-blue-400 underline-offset-2 hover:underline"
            >
              RWA.xyz
            </a>{" "}
            when <code className="rounded bg-black/30 px-1 text-xs">RWA_API_KEY</code> is set.
          </p>
        </div>
        <Link
          href="/"
          className="text-sm text-zinc-400 underline-offset-2 hover:text-white hover:underline"
        >
          ← Back to home
        </Link>
      </div>

      <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-medium text-zinc-100">Total stablecoin transfer volume</h2>
          <div className="flex flex-wrap gap-1 rounded-lg border border-[var(--border)] bg-black/20 p-1">
            {RANGES.map((r) => (
              <button
                key={r.id}
                type="button"
                onClick={() => setRange(r.id)}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                  range === r.id
                    ? "bg-blue-600 text-white"
                    : "text-zinc-400 hover:bg-zinc-800 hover:text-white"
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>
        {volSource === "mock" && (
          <p className="mt-2 text-xs text-amber-200/80">
            Volume series is illustrative until live RWA.xyz timeseries is available for your key.
          </p>
        )}
        <div className="mt-6 h-80 w-full min-w-0">
          {loadingVol ? (
            <div className="flex h-full items-center justify-center text-sm text-zinc-500">Loading chart…</div>
          ) : chartData.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-zinc-500">No data</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="volFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a3140" />
                <XAxis
                  dataKey="label"
                  tick={{ fill: "#71717a", fontSize: 11 }}
                  interval="preserveStartEnd"
                  minTickGap={24}
                />
                <YAxis
                  tick={{ fill: "#71717a", fontSize: 11 }}
                  tickFormatter={(v: number) => formatUsdCompact(v)}
                  width={72}
                />
                <Tooltip
                  contentStyle={{
                    background: "#141922",
                    border: "1px solid #2a3140",
                    borderRadius: 8,
                  }}
                  labelFormatter={(_, payload) => {
                    const p = payload?.[0]?.payload as VolumePoint & { label?: string };
                    return p?.date ?? "";
                  }}
                  formatter={(value: number) => [formatUsdCompact(value), "Volume"]}
                />
                <Area
                  type="monotone"
                  dataKey="volumeUsd"
                  stroke="#60a5fa"
                  strokeWidth={2}
                  fill="url(#volFill)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>

      <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-6">
        <h2 className="text-lg font-medium text-zinc-100">Top issuers by value</h2>
        <p className="mt-1 text-sm text-zinc-500">
          Ranked by aggregated circulating market value of stablecoin assets; 1M % is issuer-level change vs 30 days
          ago.
        </p>

        <div className="mt-6 max-h-80 overflow-y-auto overflow-x-auto rounded-lg border border-[var(--border)]">
          <table className="w-full min-w-[640px] border-collapse text-left text-sm">
            <thead className="sticky top-0 z-10 bg-[#0f141c]">
              <tr className="border-b border-[var(--border)] text-xs uppercase tracking-wide text-zinc-500">
                <th className="px-4 py-3 font-medium">Issuer</th>
                <th className="px-4 py-3 font-medium">Total value</th>
                <th className="px-4 py-3 font-medium">1M %</th>
                <th className="px-4 py-3 font-medium">Share</th>
              </tr>
            </thead>
            <tbody>
              {issuers.map((row) => (
                <tr key={row.name} className="border-b border-[var(--border)]/80 hover:bg-white/5">
                  <td className="px-4 py-3 font-medium text-zinc-200">{row.name}</td>
                  <td className="px-4 py-3 tabular-nums text-zinc-300">{formatUsdCompact(row.totalValueUsd)}</td>
                  <td
                    className={`px-4 py-3 tabular-nums ${
                      row.change30dPct == null
                        ? "text-zinc-500"
                        : row.change30dPct >= 0
                          ? "text-emerald-400"
                          : "text-rose-400"
                    }`}
                  >
                    {formatPct(row.change30dPct)}
                  </td>
                  <td className="px-4 py-3 tabular-nums text-zinc-400">{row.marketSharePct.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-8">
          <h3 className="text-sm font-medium text-zinc-400">Market share (horizontal)</h3>
          <div className="mt-3 h-[420px] w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={barData}
                layout="vertical"
                margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#2a3140" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fill: "#71717a", fontSize: 11 }}
                  tickFormatter={(v: number) => `${v.toFixed(0)}%`}
                  domain={[0, 100]}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={120}
                  tick={{ fill: "#a1a1aa", fontSize: 11 }}
                />
                <Tooltip
                  cursor={{ fill: "rgba(255,255,255,0.04)" }}
                  contentStyle={{
                    background: "#141922",
                    border: "1px solid #2a3140",
                    borderRadius: 8,
                  }}
                  formatter={(value: number, _name, item) => {
                    const payload = item?.payload as {
                      fullName?: string;
                      change30?: number | null;
                      value?: number;
                    };
                    const usd = formatUsdCompact(Number(payload?.value ?? 0));
                    const ch = formatPct(payload?.change30 ?? null);
                    return [`${Number(value).toFixed(1)}% share · ${usd} · ${ch} 1M`, "Issuer"];
                  }}
                />
                <Bar dataKey="share" radius={[0, 4, 4, 0]}>
                  {barData.map((_, i) => (
                    <Cell key={i} fill={BAR_FILL} fillOpacity={0.75 + (i % 3) * 0.05} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>
    </div>
  );
}
