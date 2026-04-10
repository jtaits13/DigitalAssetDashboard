"use client";

import { CRYPTO_ETP_FUNDS } from "@/lib/cryptoEtps";
import { useCallback, useEffect, useState } from "react";

type ResolveRow = {
  ticker: string;
  cik: string;
  name?: string;
  filingUrl: string | null;
  primaryDocumentUrl: string | null;
  form: string | null;
  filingDate: string | null;
  error?: string;
};

export function CryptoETPsSection() {
  const [rows, setRows] = useState<ResolveRow[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const res = await fetch("/api/crypto-etps/resolve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          funds: CRYPTO_ETP_FUNDS.map((f) => ({
            ticker: f.ticker,
            cik: f.cik,
            name: f.name,
          })),
        }),
      });
      const json = (await res.json()) as { results?: ResolveRow[]; error?: string };
      if (!res.ok) {
        setErr(json.error ?? "Request failed");
        setRows(null);
        return;
      }
      setRows(json.results ?? []);
    } catch {
      setErr("Could not load fund filings.");
      setRows(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-6 shadow-lg shadow-black/20">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-500">Crypto ETPs</h2>
          <p className="mt-1 max-w-2xl text-xs text-zinc-600">
            Fund Filing links resolve to the SEC EDGAR filing index page for the most recent S-1 / N-1A /
            485BPOS / 485APOS where the filing text matches the ticker (same method as the ETF-Dashboard
            reference). Set <code className="text-zinc-500">SEC_FILING_USER_AGENT</code> in{" "}
            <code className="text-zinc-500">.env.local</code> with a contact email per SEC fair-access
            policy.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="rounded-md border border-[var(--border)] bg-zinc-900/80 px-3 py-1.5 text-xs font-medium text-zinc-200 transition hover:border-blue-500/50 hover:bg-zinc-800 disabled:opacity-50"
        >
          {loading ? "Refreshing…" : "Refresh links"}
        </button>
      </div>

      <div className="mt-6 overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-xs uppercase tracking-wide text-zinc-500">
              <th className="px-3 py-2 font-medium">Fund</th>
              <th className="px-3 py-2 font-medium">Ticker</th>
              <th className="px-3 py-2 font-medium">CIK</th>
              <th className="px-3 py-2 font-medium">Fund Filing</th>
            </tr>
          </thead>
          <tbody>
            {loading && rows === null && (
              <tr>
                <td colSpan={4} className="px-3 py-6 text-zinc-500">
                  Resolving SEC filing links…
                </td>
              </tr>
            )}
            {err && (
              <tr>
                <td colSpan={4} className="px-3 py-4 text-rose-400">
                  {err}
                </td>
              </tr>
            )}
            {rows?.map((r) => (
              <tr key={`${r.cik}-${r.ticker}`} className="border-b border-[var(--border)]/80 hover:bg-white/5">
                <td className="px-3 py-3 text-zinc-200">{r.name ?? "—"}</td>
                <td className="px-3 py-3 font-medium tabular-nums text-zinc-300">{r.ticker}</td>
                <td className="px-3 py-3 tabular-nums text-zinc-500">{r.cik}</td>
                <td className="px-3 py-3">
                  {r.filingUrl ? (
                    <a
                      href={r.filingUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 underline-offset-2 hover:underline"
                    >
                      {r.form} · {r.filingDate}
                    </a>
                  ) : (
                    <span className="text-zinc-500" title={r.error}>
                      {r.error ?? "—"}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
