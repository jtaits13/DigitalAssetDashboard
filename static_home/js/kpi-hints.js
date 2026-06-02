/**
 * Top-line KPI label tooltips (same hover pattern as crypto table tickers).
 */
(function (global) {
  function esc(s) {
    if (typeof global.escapeHtml === "function") return global.escapeHtml(s);
    if (s == null) return "";
    return String(s);
  }

  function normKey(label) {
    return String(label || "")
      .trim()
      .toLowerCase()
      .replace(/\s+/g, " ")
      .replace(/\s*·\s*/g, " · ");
  }

  var RWA_CLASS_LIST =
    "U.S. Treasuries, stablecoins, tokenized stocks, credit, commodities, real estate, private equity, active strategies, and other tokenized asset classes";

  /** Normalized label → definition shown on hover. */
  var KPI_HINTS = {
    // —— Crypto snapshot ——
    "total market cap":
      "Aggregate USD market capitalization for the crypto market from CoinPaprika global data. The 1M % change uses CoinPaprika’s ~30-day market overview history.",
    "btc dominance":
      "Bitcoin’s share of total crypto market cap (BTC cap ÷ CoinPaprika total). The 1M % change approximates how that share moved using the same total-cap window and BTC’s 30-day cap change from the top-50 list.",
    "stablecoin share":
      "Stablecoin market cap in the top-50 table as a share of the sum of that list (not the global total). The 1M % uses row-level 30-day cap changes and is approximate.",
    "btc price":
      "Bitcoin spot price from the top-50 CoinGecko list (CoinCap fallback when 30-day change is missing).",
    "eth price":
      "Ethereum spot price from the top-50 CoinGecko list (CoinCap fallback when 30-day change is missing).",

    // —— RWA global / home / participants ——
    "distributed asset value":
      "Sum of distributed (on-chain, wallet-transferable) value across " +
      RWA_CLASS_LIST +
      ".",
    "represented asset value":
      "Sum of represented value for the same asset classes—" +
      RWA_CLASS_LIST +
      "—where tokens remain on the issuing platform and are not freely transferable between wallets.",
    "distributed value":
      "Distributed value for the asset type on this page—for example U.S. Treasuries, stablecoins, tokenized stocks, or (on TMMFs) the fixed curated fund population only.",
    "tokenized funds":
      "Count of curated tokenized money market fund products in this view (fixed fund list on RWA.xyz US Treasuries and Non-U.S. Government Debt listings).",
    "active networks":
      "Blockchain networks with at least one on-chain deployment among the curated TMMF population on this page.",
    "30d net change":
      "Net change in total distributed value across the curated TMMF population vs summed token values 30 days ago—a proxy for net inflows/outflows when subscription and redemption data are unavailable.",
    "represented value":
      "Represented value for the asset type on this page (platform-bound tokens, not freely transferable between wallets).",
    "total asset holders":
      "Unique holders across tokenized assets in the global market overview.",
    "total rwa holders":
      "Unique holders across tokenized assets in this participant or market view.",
    "rwa holders":
      "Holder count for tokenized assets attributed to this network, platform, or asset manager.",
    "total stablecoin value":
      "Aggregate market value of stablecoins in the global overview.",
    "stablecoin value":
      "Stablecoin market value in this overview (global totals or participant-scoped).",
    "total stablecoin holders":
      "Unique addresses or accounts holding stablecoins in this view.",
    "total networks":
      "Count of blockchain networks with tokenized asset activity in this overview.",
    "total platforms":
      "Count of issuer or platform entities listing or distributing tokenized assets in this view.",
    "distributed aum":
      "Distributed assets under management for asset managers—on-chain, transferable exposure across credit, Treasuries, stocks, and other classes.",
    "represented aum":
      "Represented AUM for asset managers—platform-bound tokenized exposure in the same asset classes.",
    "rwa count":
      "Count of distinct tokenized instruments or listings for this manager or scope.",
    "rwa managers count":
      "Number of distinct asset managers with tokenized asset exposure in this league.",

    // —— Stablecoins / treasuries / stocks page KPIs ——
    "market cap":
      "Total market capitalization for stablecoins on this page (USD-, EUR-, and other fiat-pegged tokens).",
    "monthly transfer volume":
      "Estimated on-chain transfer volume over the last month for this asset type.",
    "monthly active addresses":
      "Distinct addresses that transacted at least once in the last month.",
    holders:
      "Unique holder count for this asset type or instrument set.",
    assets:
      "Count of distinct tokenized instruments in this overview.",
    "7d apy":
      "Seven-day annualized yield proxy for U.S. Treasury and money-market-style products on this page (varies by issuer and structure).",

    // —— U.S. ETP snapshot ——
    "total aum (listed)":
      "Sum of estimated assets under management across U.S.-listed crypto ETPs in our table (StockAnalysis fund list). Aggregate 1M % uses an estimated weekly AUM series.",
    "btc & eth fund flows (listed)":
      "Net spot BTC + ETH ETF flow estimate over ~30 days from Farside data, compared with the prior 30-day window for the % change.",
    "ibit · aum":
      "Estimated AUM for the iShares Bitcoin Trust (IBIT). 1M % from Yahoo when available; may fall back to 1Y if 1M data is missing.",
    "etha · aum":
      "Estimated AUM for the iShares Ethereum Trust (ETHA). 1M % from Yahoo when available; may fall back to 1Y if 1M data is missing.",
  };

  function kpiHintForLabel(label, optionalHint) {
    if (optionalHint != null && String(optionalHint).trim()) {
      return String(optionalHint).trim();
    }
    var key = normKey(label);
    if (KPI_HINTS[key]) return KPI_HINTS[key];
    if (key.indexOf("distributed asset") >= 0) return KPI_HINTS["distributed asset value"];
    if (key.indexOf("represented asset") >= 0) return KPI_HINTS["represented asset value"];
    if (key === "distributed value") return KPI_HINTS["distributed value"];
    if (key === "represented value") return KPI_HINTS["represented value"];
    return null;
  }

  function wrapKpiLabel(label, optionalHint) {
    var text = label == null ? "" : String(label);
    var hint = kpiHintForLabel(text, optionalHint);
    if (!hint || typeof global.wrapCryptoHint !== "function") {
      return esc(text);
    }
    return global.wrapCryptoHint(text, hint, "kpi-hint");
  }

  function bindKpiHints(root) {
    if (typeof global.bindCryptoHints === "function") {
      global.bindCryptoHints(root);
    }
  }

  global.__KPI_HINTS = {
    kpiHintForLabel: kpiHintForLabel,
    wrapKpiLabel: wrapKpiLabel,
    bindKpiHints: bindKpiHints,
  };
})(typeof window !== "undefined" ? window : this);
