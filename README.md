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

The home page lists **EDGAR filings** that match a **full-text OR search** over crypto / digital-asset / blockchain / tokenization keywords, then **keeps only** the form types in `FORM_TYPES_LABEL` in `sec_filings/client.py` (N-1A, 485APOS, 485BPOS, S-1, 424B2, 424B3, 424I, including common variants by prefix). Data comes from the same index as [EDGAR search](https://www.sec.gov/edgar/search/) (`efts.sec.gov`, no API key).

**Important — User-Agent:** SEC requires automated requests to identify the caller and include **contact information**. Set in `.streamlit/secrets.toml` (local) or Streamlit Cloud **Secrets**:

```toml
SEC_EDGAR_USER_AGENT = "YourAppName/1.0 (your.email@example.com)"
```

If unset, a generic placeholder is used; for production you should set your own string. See [SEC fair access / EDGAR data](https://www.sec.gov/os/accessing-edgar-data).

Results are **cached for one hour**; use **Refresh feeds** to clear the cache.
