# JPM Digital — Crypto News

**Streamlit Community Cloud:** set **Main file path** to `streamlit_app.py` (must sit at the **root** of the repository, next to `requirements.txt`).

## Layout

```
streamlit_app.py
requirements.txt
.gitignore
.streamlit/config.toml

sec_filings/                 # SEC EDGAR fund-filing widget (home page, right column)
  client.py
  widgets.py
```

## SEC fund filings widget

The home page lists **EDGAR filings** that match a **full-text OR search** over crypto / digital-asset / blockchain / tokenization keywords, then **keeps only** these form types: **N-1A**, **N-2**, **485BPOS**, **485APOS**, **497**, **S-1**, **424B2** (including common variants by prefix, e.g. 497K, N-1A/A). Data comes from the same index as [EDGAR search](https://www.sec.gov/edgar/search/) (`efts.sec.gov`, no API key).

**Important — User-Agent:** SEC requires automated requests to identify the caller and include **contact information**. Set in `.streamlit/secrets.toml` (local) or Streamlit Cloud **Secrets**:

```toml
SEC_EDGAR_USER_AGENT = "YourAppName/1.0 (your.email@example.com)"
```

If unset, a generic placeholder is used; for production you should set your own string. See [SEC fair access / EDGAR data](https://www.sec.gov/os/accessing-edgar-data).

Results are **cached for one hour**; use **Refresh feeds** to clear the cache.
