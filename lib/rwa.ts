const RWA_BASE = "https://api.rwa.xyz";

export type MetricObj = {
  val?: number;
  val_30d?: number;
  chg_30d_pct?: number;
};

export type StablecoinSummary = {
  totalValueUsd: number;
  change30dPct: number | null;
  source: "rwa" | "mock";
};

export type IssuerRow = {
  name: string;
  totalValueUsd: number;
  change30dPct: number | null;
  marketSharePct: number;
};

export type VolumePoint = { date: string; volumeUsd: number };

const MOCK_SUMMARY: StablecoinSummary = {
  totalValueUsd: 308_400_000_000,
  change30dPct: 3.42,
  source: "mock",
};

const MOCK_ISSUERS: IssuerRow[] = [
  { name: "Tether", totalValueUsd: 144_000_000_000, change30dPct: 2.1, marketSharePct: 46.7 },
  { name: "Circle", totalValueUsd: 52_000_000_000, change30dPct: 4.8, marketSharePct: 16.9 },
  { name: "Paxos", totalValueUsd: 6_200_000_000, change30dPct: 1.2, marketSharePct: 2.0 },
  { name: "MakerDAO", totalValueUsd: 5_100_000_000, change30dPct: -0.4, marketSharePct: 1.7 },
  { name: "Ethena", totalValueUsd: 4_900_000_000, change30dPct: 12.4, marketSharePct: 1.6 },
  { name: "First Digital", totalValueUsd: 2_800_000_000, change30dPct: 5.6, marketSharePct: 0.9 },
  { name: "PayPal", totalValueUsd: 1_900_000_000, change30dPct: 3.1, marketSharePct: 0.6 },
  { name: "Frax", totalValueUsd: 650_000_000, change30dPct: -2.3, marketSharePct: 0.2 },
  { name: "Avalanche Foundation", totalValueUsd: 120_000_000, change30dPct: 0.8, marketSharePct: 0.04 },
  { name: "Other", totalValueUsd: 90_630_000_000, change30dPct: 2.9, marketSharePct: 29.4 },
];

function seededNoise(seed: number, i: number): number {
  const x = Math.sin(seed * 12.9898 + i * 78.233) * 43758.5453;
  return x - Math.floor(x);
}

function buildMockVolume(days: number): VolumePoint[] {
  const out: VolumePoint[] = [];
  const end = new Date();
  let base = 18_000_000_000;
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(end);
    d.setUTCDate(d.getUTCDate() - i);
    const wobble = (seededNoise(42, i) - 0.5) * 2_500_000_000;
    base += (seededNoise(7, i) - 0.48) * 120_000_000;
    const vol = Math.max(5_000_000_000, base + wobble);
    out.push({ date: d.toISOString().slice(0, 10), volumeUsd: vol });
  }
  return out;
}

function getMetric(asset: { circulating_market_value_dollar?: MetricObj }): MetricObj | undefined {
  return asset.circulating_market_value_dollar;
}

function summarizeFromAssets(assets: { circulating_market_value_dollar?: MetricObj }[]): StablecoinSummary {
  let total = 0;
  let sum30 = 0;
  let has30 = false;
  for (const a of assets) {
    const m = getMetric(a);
    if (!m?.val) continue;
    total += m.val;
    if (m.val_30d != null) {
      sum30 += m.val_30d;
      has30 = true;
    }
  }
  let change30dPct: number | null = null;
  if (has30 && sum30 > 0) {
    change30dPct = ((total - sum30) / sum30) * 100;
  }
  return { totalValueUsd: total, change30dPct, source: "rwa" };
}

function issuersFromAssets(
  assets: { issuer_name?: string; circulating_market_value_dollar?: MetricObj }[],
): IssuerRow[] {
  const map = new Map<
    string,
    { val: number; val30: number; has30: boolean }
  >();
  for (const a of assets) {
    const name = a.issuer_name?.trim() || "Unknown";
    const m = getMetric(a);
    if (!m?.val) continue;
    const cur = map.get(name) ?? { val: 0, val30: 0, has30: false };
    cur.val += m.val;
    if (m.val_30d != null) {
      cur.val30 += m.val_30d;
      cur.has30 = true;
    }
    map.set(name, cur);
  }
  const total = [...map.values()].reduce((s, x) => s + x.val, 0);
  const rows: IssuerRow[] = [...map.entries()].map(([name, agg]) => {
    let change30dPct: number | null = null;
    if (agg.has30 && agg.val30 > 0) {
      change30dPct = ((agg.val - agg.val30) / agg.val30) * 100;
    }
    return {
      name,
      totalValueUsd: agg.val,
      change30dPct,
      marketSharePct: total > 0 ? (agg.val / total) * 100 : 0,
    };
  });
  rows.sort((a, b) => b.totalValueUsd - a.totalValueUsd);
  return rows.slice(0, 10);
}

async function rwaGet<T>(path: string, apiKey: string): Promise<T> {
  const url = `${RWA_BASE}${path}`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${apiKey}` },
    next: { revalidate: 1800 },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`RWA ${res.status}: ${text.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

type AssetsPage = {
  results: {
    issuer_name?: string;
    circulating_market_value_dollar?: MetricObj;
  }[];
  pagination: { page: number; pageCount: number; perPage: number; resultCount: number };
};

export async function fetchStablecoinAssets(apiKey: string) {
  const all: AssetsPage["results"] = [];
  let page = 1;
  const perPage = 100;
  for (;;) {
    const query = {
      filter: { operator: "equals" as const, field: "asset_class_name", value: "Stablecoins" },
      sort: { field: "circulating_market_value_dollar", direction: "desc" as const },
      pagination: { page, perPage },
    };
    const enc = encodeURIComponent(JSON.stringify(query));
    const data = await rwaGet<AssetsPage>(`/v4/assets?query=${enc}`, apiKey);
    all.push(...data.results);
    if (page >= data.pagination.pageCount) break;
    page += 1;
    if (page > 50) break;
  }
  return all;
}

export async function getStablecoinSummary(apiKey: string | undefined): Promise<StablecoinSummary> {
  if (!apiKey) return MOCK_SUMMARY;
  try {
    const assets = await fetchStablecoinAssets(apiKey);
    return summarizeFromAssets(assets);
  } catch {
    return { ...MOCK_SUMMARY, source: "mock" };
  }
}

export async function getTopIssuers(apiKey: string | undefined): Promise<IssuerRow[]> {
  if (!apiKey) return MOCK_ISSUERS;
  try {
    const assets = await fetchStablecoinAssets(apiKey);
    const rows = issuersFromAssets(assets);
    if (rows.length === 0) return MOCK_ISSUERS;
    return rows;
  } catch {
    return MOCK_ISSUERS;
  }
}

export type VolumeRange = "1m" | "3m" | "6m" | "1y" | "5y";

export function rangeToDays(range: VolumeRange): number {
  switch (range) {
    case "1m":
      return 31;
    case "3m":
      return 92;
    case "6m":
      return 183;
    case "1y":
      return 365;
    case "5y":
      return 365 * 5;
    default:
      return 31;
  }
}

type TsResult = {
  results: {
    measure?: { slug?: string };
    group?: { type?: string; name?: string };
    points?: [string, number][];
  }[];
};

export async function getStablecoinVolumeSeries(
  apiKey: string | undefined,
  range: VolumeRange,
): Promise<{ points: VolumePoint[]; source: "rwa" | "mock" }> {
  const days = rangeToDays(range);
  if (!apiKey) {
    return { points: buildMockVolume(Math.min(days, 2000)), source: "mock" };
  }
  const start = new Date();
  start.setUTCDate(start.getUTCDate() - days);
  const startStr = start.toISOString().slice(0, 10);
  const query = {
    filter: {
      operator: "and" as const,
      filters: [
        { operator: "equals" as const, field: "asset_class_name", value: "Stablecoins" },
        { operator: "equals" as const, field: "measure_slug", value: "daily_transfer_volume_dollar" },
        { operator: "onOrAfter" as const, field: "date", value: startStr },
      ],
    },
    aggregate: {
      groupBy: "date",
      aggregateFunction: "sum" as const,
      interval: "day" as const,
      mode: "flow" as const,
    },
    pagination: { page: 1, perPage: 5000 },
  };
  const tryEndpoints = [`/v4/tokens/aggregates/timeseries?query=`, `/v4/assets/aggregates/timeseries?query=`];
  try {
    for (const prefix of tryEndpoints) {
      const enc = encodeURIComponent(JSON.stringify(query));
      const data = await rwaGet<TsResult>(`${prefix}${enc}`, apiKey);
      const first = data.results?.[0];
      const pts = first?.points ?? [];
      const points: VolumePoint[] = pts.map(([date, volumeUsd]) => ({
        date: String(date).slice(0, 10),
        volumeUsd: Number(volumeUsd),
      }));
      if (points.length > 0) {
        return { points, source: "rwa" };
      }
    }
    return { points: buildMockVolume(Math.min(days, 2000)), source: "mock" };
  } catch {
    return { points: buildMockVolume(Math.min(days, 2000)), source: "mock" };
  }
}
