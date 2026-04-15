const STOCKS_URL = "https://app.rwa.xyz/stocks";

export type StocksToplineMetric = {
  label: string;
  value: string;
  change30d: string | null;
};

export type StocksPlatformRow = {
  rank: number;
  platform: string;
  rwaCount: number | null;
  distributedValue: string;
  distributedValueUsd: number | null;
  change30d: string | null;
  marketShare: string | null;
};

export type TokenizedStocksData = {
  source: "scraped" | "fallback";
  metrics: StocksToplineMetric[];
  rows: StocksPlatformRow[];
  rwaUrl: string;
};

const METRIC_LABELS = [
  "Distributed Value",
  "Represented Value",
  "Monthly Transfer Volume",
  "Monthly Active Addresses",
  "Holders",
] as const;

const FALLBACK_METRICS: StocksToplineMetric[] = [
  { label: "Distributed Value", value: "$1.05B", change30d: "+7.47%" },
  { label: "Represented Value", value: "$3.50M", change30d: "-76.21%" },
  { label: "Monthly Transfer Volume", value: "$2.77B", change30d: "+21.04%" },
  { label: "Monthly Active Addresses", value: "44,611", change30d: "-53.43%" },
  { label: "Holders", value: "209.58K", change30d: "+15.57%" },
];

const FALLBACK_ROWS: StocksPlatformRow[] = [
  { rank: 1, platform: "Backed Finance", rwaCount: 230, distributedValue: "$649.5M", distributedValueUsd: 649_500_000, change30d: "+21.79%", marketShare: "60.88%" },
  { rank: 2, platform: "Dinari", rwaCount: 131, distributedValue: "$260.9M", distributedValueUsd: 260_900_000, change30d: "+4.85%", marketShare: "24.45%" },
  { rank: 3, platform: "xStocks", rwaCount: 1, distributedValue: "$61.7M", distributedValueUsd: 61_700_000, change30d: "-26.29%", marketShare: "5.79%" },
  { rank: 4, platform: "SwarmX", rwaCount: 3, distributedValue: "$25.8M", distributedValueUsd: 25_800_000, change30d: "-10.87%", marketShare: "2.42%" },
  { rank: 5, platform: "Ondo Global Markets", rwaCount: 6, distributedValue: "$23.8M", distributedValueUsd: 23_800_000, change30d: "+4.60%", marketShare: "2.23%" },
  { rank: 6, platform: "Midas", rwaCount: 1, distributedValue: "$21.2M", distributedValueUsd: 21_200_000, change30d: "-41.18%", marketShare: "1.99%" },
  { rank: 7, platform: "Libre", rwaCount: 2, distributedValue: "$7.4M", distributedValueUsd: 7_400_000, change30d: "-13.49%", marketShare: "0.70%" },
  { rank: 8, platform: "Republic", rwaCount: 2, distributedValue: "$6.3M", distributedValueUsd: 6_300_000, change30d: "+1891%", marketShare: "0.59%" },
  { rank: 9, platform: "Arca", rwaCount: 8, distributedValue: "$5.1M", distributedValueUsd: 5_100_000, change30d: "-2.43%", marketShare: "0.48%" },
  { rank: 10, platform: "Securitize", rwaCount: 82, distributedValue: "$2.7M", distributedValueUsd: 2_700_000, change30d: "-1.55%", marketShare: "0.25%" },
];

function stripTags(input: string): string {
  return input
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/\s+/g, " ")
    .trim();
}

function parseCompactUsd(raw: string): number | null {
  const m = raw.trim().match(/^\$?([\d,.]+)\s*([KMBT])?$/i);
  if (!m) return null;
  const value = Number(m[1].replace(/,/g, ""));
  if (!Number.isFinite(value)) return null;
  const unit = (m[2] ?? "").toUpperCase();
  const mult = unit === "K" ? 1e3 : unit === "M" ? 1e6 : unit === "B" ? 1e9 : unit === "T" ? 1e12 : 1;
  return value * mult;
}

function parseCount(raw: string): number | null {
  const m = raw.trim().match(/^([\d,.]+)\s*([KMB])?$/i);
  if (!m) return null;
  const value = Number(m[1].replace(/,/g, ""));
  if (!Number.isFinite(value)) return null;
  const unit = (m[2] ?? "").toUpperCase();
  const mult = unit === "K" ? 1e3 : unit === "M" ? 1e6 : unit === "B" ? 1e9 : 1;
  return Math.round(value * mult);
}

function normalizeChange(raw: string | null): string | null {
  if (!raw) return null;
  const pct = raw.match(/([+-]?\d[\d,.]*%)/);
  return pct ? pct[1].replace(/,/g, "") : null;
}

function extractMetrics(text: string): StocksToplineMetric[] {
  return METRIC_LABELS.map((label) => {
    const rx = new RegExp(`${label}\\s*([$\\d][\\d.,]*\\s*[KMBT]?)\\s*([▲▼]?\\s*[+-]?[\\d,.]+%\\s*from\\s*30d\\s*ago)?`, "i");
    const match = text.match(rx);
    return {
      label,
      value: match?.[1]?.trim() ?? "—",
      change30d: normalizeChange(match?.[2]?.trim() ?? null),
    };
  });
}

function cleanCell(htmlCell: string): string {
  return stripTags(htmlCell).replace(/\s+/g, " ").trim();
}

function extractRows(html: string): StocksPlatformRow[] {
  const sectionIdx = html.indexOf("Tokenized Stocks League Table");
  if (sectionIdx < 0) return [];
  const tableStart = html.indexOf("<table", sectionIdx);
  const tableEnd = html.indexOf("</table>", tableStart);
  if (tableStart < 0 || tableEnd < 0) return [];
  const tableHtml = html.slice(tableStart, tableEnd + 8);

  const rows: StocksPlatformRow[] = [];
  const trRegex = /<tr[\s\S]*?<\/tr>/gi;
  const tdRegex = /<t[dh][^>]*>([\s\S]*?)<\/t[dh]>/gi;

  for (const tr of tableHtml.match(trRegex) ?? []) {
    const cells: string[] = [];
    let tdMatch: RegExpExecArray | null;
    while ((tdMatch = tdRegex.exec(tr)) !== null) {
      const val = cleanCell(tdMatch[1]);
      if (val && val !== "▲" && val !== "▼") cells.push(val);
    }
    if (cells.length < 6) continue;
    const rank = Number.parseInt(cells[0], 10);
    if (!Number.isFinite(rank)) continue;
    const platform = cells[1];
    const rwaCount = parseCount(cells[2]);
    const distributedValue = cells[3];
    const distributedValueUsd = parseCompactUsd(distributedValue);
    const change30d = normalizeChange(cells[4]);
    const marketShare = cells[5].includes("%") ? cells[5] : null;
    rows.push({
      rank,
      platform,
      rwaCount,
      distributedValue,
      distributedValueUsd,
      change30d,
      marketShare,
    });
  }

  return rows;
}

function fallbackData(): TokenizedStocksData {
  return {
    source: "fallback",
    metrics: FALLBACK_METRICS,
    rows: [...FALLBACK_ROWS].sort((a, b) => a.platform.localeCompare(b.platform)),
    rwaUrl: STOCKS_URL,
  };
}

export async function getTokenizedStocksData(): Promise<TokenizedStocksData> {
  try {
    const res = await fetch(STOCKS_URL, {
      headers: {
        "User-Agent": "Mozilla/5.0 (compatible; JPM-Digital-Dashboard/1.0)",
      },
      next: { revalidate: 3600 },
    });
    if (!res.ok) return fallbackData();
    const html = await res.text();
    const text = stripTags(html);
    const metrics = extractMetrics(text);
    const rows = extractRows(html);
    if (rows.length === 0) return fallbackData();
    return {
      source: "scraped",
      metrics,
      rows: [...rows].sort((a, b) => a.platform.localeCompare(b.platform)),
      rwaUrl: STOCKS_URL,
    };
  } catch {
    return fallbackData();
  }
}
