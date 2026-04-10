# JPM Digital — Crypto News

**Streamlit Community Cloud:** set **Main file path** to `streamlit_app.py` (must sit at the **root** of the repository, next to `requirements.txt`).

## Layout

The **home page** is a hub (CoinDesk-style): each block shows a **short preview** (fewer headlines, smaller tables) with buttons or nav links to **full pages** under `pages/` (all articles, regulatory, U.S. crypto ETPs, RWA league).

```
streamlit_app.py
requirements.txt
.gitignore
.streamlit/config.toml

pages/
  All_Articles.py, All_Regulatory.py, US_Crypto_ETPs.py, RWA_League.py

sec_filings/                 # SEC EDGAR fund-filing widget (optional / elsewhere)
  client.py
  widgets.py
```

## SEC fund filings widget

The home page lists **EDGAR filings** that match a **full-text OR search** over crypto / digital-asset / blockchain / tokenization keywords, then **keeps only** the form types in `FORM_TYPES_LABEL` in `sec_filings/client.py` (N-1A, 485APOS, 485BPOS, S-1, 424B2, 424B3, 424I, including common variants by prefix). Data comes from the same index as [EDGAR search](https://www.sec.gov/edgar/search/) (`efts.sec.gov`, no API key).

**Important — User-Agent:** SEC requires automated requests to identify the caller and include **contact information**. Set in `.streamlit/secrets.toml` (local) or Streamlit Cloud **Secrets**:

```toml
SEC_EDGAR_USER_AGENT = "YourAppName/1.0 (your.email@example.com)"
```

If unset, a generic placeholder is used; for production you should set your own string. See [SEC fair access / EDGAR data](https://www.sec.gov/os/accessing-edgar-data).

Results are **cached for one hour**; use **Refresh feeds** to clear the cache.

## U.S. Crypto ETPs — Fund Filing column

The home widget and **U.S. Crypto ETPs** page (`pages/US_Crypto_ETPs.py`) include a **Fund Filing** column (replacing the previous S-1-only link). Resolution follows the same approach as [ETF-Dashboard](https://github.com/halestorm9352/ETF-Dashboard): for each fund ticker, load SEC `company_tickers` → registrant **submissions** JSON, scan recent **S-1 / N-1A / 485BPOS / 485APOS** (and common variants), fetch each filing’s index and primary/supporting documents, parse tickers, and use the filing **index** URL (`…-index.htm`) when the ticker matches. If no match is found, the app falls back to the previous behavior (newest S-1 primary document, S-1 browse, or EDGAR search).

Implementation: `crypto_etps/fund_filing.py`, `crypto_etps/edgar_parsers.py`, and `resolve_fund_filing_url` in `crypto_etps/sec_prospectus.py`. Uses the same **User-Agent** as other SEC calls (`STOCKANALYSIS_USER_AGENT` / app default).
