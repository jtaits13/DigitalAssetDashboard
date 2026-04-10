import { findFundFilingForTicker } from "@/lib/secFilings";

export const maxDuration = 60;

type Body = {
  funds?: { ticker: string; cik: string; name?: string }[];
};

export async function POST(request: Request) {
  let body: Body;
  try {
    body = (await request.json()) as Body;
  } catch {
    return Response.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const funds = body.funds;
  if (!Array.isArray(funds) || funds.length === 0) {
    return Response.json(
      { error: "Expected body: { funds: [{ ticker, cik }, ...] }" },
      { status: 400 },
    );
  }

  if (funds.length > 40) {
    return Response.json({ error: "Maximum 40 funds per request" }, { status: 400 });
  }

  const results: {
    ticker: string;
    cik: string;
    name?: string;
    filingUrl: string | null;
    primaryDocumentUrl: string | null;
    form: string | null;
    filingDate: string | null;
    error?: string;
  }[] = [];

  for (const f of funds) {
    const ticker = String(f.ticker ?? "").trim();
    const cik = String(f.cik ?? "").trim();
    if (!ticker || !cik) {
      results.push({
        ticker,
        cik,
        name: f.name,
        filingUrl: null,
        primaryDocumentUrl: null,
        form: null,
        filingDate: null,
        error: "Missing ticker or cik",
      });
      continue;
    }

    try {
      const match = await findFundFilingForTicker(cik, ticker);
      if (!match) {
        results.push({
          ticker,
          cik,
          name: f.name,
          filingUrl: null,
          primaryDocumentUrl: null,
          form: null,
          filingDate: null,
          error: "No matching filing in recent forms (S-1, N-1A, 485BPOS, 485APOS)",
        });
      } else {
        results.push({
          ticker,
          cik,
          name: f.name,
          filingUrl: match.filingUrl,
          primaryDocumentUrl: match.primaryDocumentUrl,
          form: match.form,
          filingDate: match.filingDate,
        });
      }
    } catch (e) {
      results.push({
        ticker,
        cik,
        name: f.name,
        filingUrl: null,
        primaryDocumentUrl: null,
        form: null,
        filingDate: null,
        error: e instanceof Error ? e.message : "Lookup failed",
      });
    }
  }

  return Response.json({ results });
}
