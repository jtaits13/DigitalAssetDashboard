/**
 * SEC EDGAR filing resolution aligned with halestorm9352/ETF-Dashboard (sec_filings + sec_parsers).
 * Resolves the filing index URL (.../{accession}-index.htm) for a trust CIK + fund ticker match.
 */

const FORMS = new Set(["S-1", "N-1A", "485BPOS", "485APOS"]);
const INVALID_TICKERS = new Set(["CIK", "ETF", "FUND"]);
const INDEX_PAGE_MAX_CHARS = 60_000;
const PRIMARY_MAX_CHARS = 300_000;
const SUPPORTING_MAX_CHARS = 120_000;
const MAX_FILINGS_TO_SCAN = 28;
const MAX_SUPPORTING_DOCS = 4;
const REQUEST_DELAY_MS = 320;

function secHeaders(): HeadersInit {
  const ua =
    process.env.SEC_FILING_USER_AGENT?.trim() ||
    "JPM Digital Project (digital-markets@example.com)";
  return {
    "User-Agent": ua,
    Accept: "application/json,text/html;q=0.9,*/*;q=0.8",
  };
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export function padCik(cik: string): string {
  const digits = cik.replace(/\D/g, "");
  return digits.padStart(10, "0");
}

function cleanHtmlText(value: string): string {
  const withoutTags = value.replace(/<[^>]+>/g, " ");
  let decoded = withoutTags
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)));
  decoded = decoded.replace(/[\u2000-\u200f\u2028-\u202f\u205f\u2060\ufeff]/g, " ");
  return decoded.split(/\s+/).join(" ").trim();
}

export function sanitizeTicker(value: string | undefined | null): string {
  const ticker = String(value ?? "")
    .trim()
    .toUpperCase();
  if (/^[A-Z]{1,8}$/.test(ticker) && !INVALID_TICKERS.has(ticker)) {
    return ticker;
  }
  return "Not Listed";
}

function extractTicker(text: string): string {
  const cleaned = cleanHtmlText(text);

  const bracketedPipe = cleaned.match(
    /\[\s*([A-Z]{1,8})\s*\]\s*\|\s*([A-Za-z0-9&.\-\s]{3,120}?(?:ETF|Fund))/i,
  );
  if (bracketedPipe) {
    const t = bracketedPipe[1].toUpperCase();
    if (!INVALID_TICKERS.has(t)) return t;
  }

  const contractRow = text.match(/<tr[^>]*class="contractRow"[^>]*>(.*?)<\/tr>/is);
  if (contractRow) {
    const tds = [...contractRow[1].matchAll(/<td[^>]*>(.*?)<\/td>/gis)].map((m) =>
      cleanHtmlText(m[1]),
    );
    if (tds.length) {
      const candidate = tds[tds.length - 1].toUpperCase();
      if (/^[A-Z]{1,8}$/.test(candidate) && !INVALID_TICKERS.has(candidate)) {
        return candidate;
      }
    }
  }

  const rawLabel = text.search(/Ticker Symbol/i);
  if (rawLabel >= 0) {
    const snippet = cleanHtmlText(text.slice(rawLabel, rawLabel + 2000));
    const m = snippet.match(/Ticker Symbol\s*:?\s*([A-Z]{2,8})\b/i);
    if (m) {
      const t = m[1].toUpperCase();
      if (!INVALID_TICKERS.has(t)) return t;
    }
  }

  const prospectusTable = cleaned.match(
    /Fund\s+Ticker\s+Principal U\.S\. Listing Exchange.*?(?:ETF|Fund)\s+([A-Z]{1,8})\b/i,
  );
  if (prospectusTable) {
    const t = prospectusTable[1].toUpperCase();
    if (!INVALID_TICKERS.has(t)) return t;
  }

  const pipe = cleaned.match(
    /([A-Z]{2,6})\s*\|\s*([A-Za-z0-9&.\-\s]{3,120}?(?:ETF|Fund))/i,
  );
  if (pipe) {
    const t = pipe[1].toUpperCase();
    if (!INVALID_TICKERS.has(t)) return t;
  }

  const tickerCell = cleaned.match(/Ticker Symbol\s+([A-Z]{1,8})/i);
  if (tickerCell) {
    const t = tickerCell[1].toUpperCase();
    if (!INVALID_TICKERS.has(t)) return t;
  }

  return "";
}

type SeriesEntry = { etf_name: string; ticker: string };

function extractSeriesEntries(text: string): SeriesEntry[] {
  const entries: SeriesEntry[] = [];
  const re =
    /<tr[^>]*class="contractRow"[^>]*>.*?<td[^>]*>.*?<\/td>\s*<td[^>]*>.*?<\/td>\s*<td[^>]*>(.*?)<\/td>\s*<td[^>]*>(.*?)<\/td>\s*<\/tr>/gis;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    const name = cleanHtmlText(m[1]);
    let ticker = cleanHtmlText(m[2]).toUpperCase();
    if (!name) continue;
    if (ticker && !/^[A-Z]{1,8}$/.test(ticker)) ticker = "";
    if (ticker && INVALID_TICKERS.has(ticker)) ticker = "";
    entries.push({ etf_name: name, ticker });
  }
  return entries;
}

function buildSecUrl(pathOrUrl: string): string {
  if (pathOrUrl.startsWith("http")) return pathOrUrl;
  return `https://www.sec.gov${pathOrUrl}`;
}

function extractSupportingDocumentUrls(indexText: string): string[] {
  const prioritized: string[] = [];
  const pushMatches = (iter: IterableIterator<RegExpMatchArray>) => {
    for (const match of iter) {
      const path = match[1];
      if (!path) continue;
      const filename = path.split("/").pop()?.toLowerCase() ?? "";
      if (filename === "index.htm" || filename === "index.html") continue;
      const full = buildSecUrl(path);
      if (!prioritized.includes(full)) prioritized.push(full);
    }
  };
  pushMatches(
    indexText.matchAll(/href="\/ix\?doc=(\/Archives\/edgar\/data\/[^"]+\.(?:htm|html))"/gi),
  );
  pushMatches(
    indexText.matchAll(
      /<tr[^>]*>\s*<td[^>]*>\s*1\s*<\/td>[\s\S]*?href="(\/Archives\/edgar\/data\/[^"]+\.(?:htm|html))"/gi,
    ),
  );
  pushMatches(indexText.matchAll(/href="(\/Archives\/edgar\/data\/[^"]+_htm\.xml)"/gi));
  pushMatches(indexText.matchAll(/href="(\/Archives\/edgar\/data\/[^"]+\.txt)"/gi));
  pushMatches(indexText.matchAll(/href="(\/Archives\/edgar\/data\/[^"]+\.(?:htm|html))"/gi));
  return prioritized;
}

async function fetchText(url: string, maxChars: number): Promise<string> {
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const res = await fetch(url, { headers: secHeaders(), next: { revalidate: 0 } });
      if (!res.ok) throw new Error(String(res.status));
      const t = await res.text();
      return t.slice(0, maxChars);
    } catch {
      if (attempt === 2) return "";
      await sleep(800 + attempt * 400);
    }
  }
  return "";
}

export type FundFilingMatch = {
  /** SEC filing index page (same as ETF-Dashboard "link" column) */
  filingUrl: string;
  /** Main registration statement HTML/XML when identifiable */
  primaryDocumentUrl: string | null;
  form: string;
  filingDate: string;
};

function tickerMatchesTarget(parsed: string, target: string): boolean {
  if (!parsed) return false;
  return sanitizeTicker(parsed) === sanitizeTicker(target);
}

async function collectTickersForFiling(
  indexText: string,
  primaryDocumentUrl: string,
): Promise<Set<string>> {
  const tickers = new Set<string>();

  if (primaryDocumentUrl) {
    const maxChars = primaryDocumentUrl.toLowerCase().endsWith("_htm.xml")
      ? 120_000
      : PRIMARY_MAX_CHARS;
    const primaryText = await fetchText(primaryDocumentUrl, maxChars);
    await sleep(REQUEST_DELAY_MS);
    const pt = extractTicker(primaryText);
    if (pt) tickers.add(pt);
  }

  const series = extractSeriesEntries(indexText);
  for (const e of series) {
    if (e.ticker) tickers.add(sanitizeTicker(e.ticker));
  }

  if (tickers.size === 0 || series.some((e) => !e.ticker)) {
    const supporting = extractSupportingDocumentUrls(indexText).slice(0, MAX_SUPPORTING_DOCS);
    for (const url of supporting) {
      const maxChars = url.toLowerCase().endsWith("_htm.xml") ? SUPPORTING_MAX_CHARS : PRIMARY_MAX_CHARS;
      const st = await fetchText(url, maxChars);
      await sleep(REQUEST_DELAY_MS);
      const t = extractTicker(st);
      if (t) tickers.add(t);
    }
  }

  return tickers;
}

/**
 * Find the most recent EDGAR filing (allowed forms) for this trust whose parsed ticker matches `ticker`.
 */
export async function findFundFilingForTicker(
  cik: string,
  ticker: string,
): Promise<FundFilingMatch | null> {
  const cikPadded = padCik(cik);
  const cikNum = parseInt(cikPadded, 10);
  const submissionsUrl = `https://data.sec.gov/submissions/CIK${cikPadded}.json`;

  const jsonText = await fetchText(submissionsUrl, 2_000_000);
  await sleep(REQUEST_DELAY_MS);
  if (!jsonText) return null;

  let data: {
    filings?: { recent?: Record<string, string[]> };
  };
  try {
    data = JSON.parse(jsonText);
  } catch {
    return null;
  }

  const recent = data.filings?.recent;
  if (!recent) return null;

  const forms = recent.form ?? [];
  const filingDates = recent.filingDate ?? [];
  const accessionNumbers = recent.accessionNumber ?? [];
  const primaryDocuments = recent.primaryDocument ?? [];

  const target = ticker.trim().toUpperCase();
  let scanned = 0;

  for (let index = 0; index < forms.length; index++) {
    if (scanned >= MAX_FILINGS_TO_SCAN) break;
    const form = forms[index];
    if (!FORMS.has(form)) continue;

    if (
      index >= filingDates.length ||
      index >= accessionNumbers.length
    ) {
      continue;
    }

    scanned += 1;

    const dateStr = filingDates[index];
    const accessionNumber = accessionNumbers[index];
    const primaryDocument =
      index < primaryDocuments.length ? primaryDocuments[index] : "";

    const accessionClean = accessionNumber.replace(/-/g, "");
    const filingUrl = `https://www.sec.gov/Archives/edgar/data/${cikNum}/${accessionClean}/${accessionNumber}-index.htm`;

    let primaryDocumentUrl: string | null = null;
    if (primaryDocument) {
      primaryDocumentUrl = `https://www.sec.gov/Archives/edgar/data/${cikNum}/${accessionClean}/${primaryDocument}`;
    }

    const indexText = await fetchText(filingUrl, INDEX_PAGE_MAX_CHARS);
    await sleep(REQUEST_DELAY_MS);

    if (!indexText) continue;

    const tickers = await collectTickersForFiling(indexText, primaryDocumentUrl ?? "");

    for (const t of tickers) {
      if (tickerMatchesTarget(t, target)) {
        return {
          filingUrl,
          primaryDocumentUrl,
          form,
          filingDate: dateStr,
        };
      }
    }
  }

  return null;
}
