/**
 * Collapsible "Data sources & definitions" panels for snapshot pages.
 */
(function (global) {
  var RWA = '<a href="https://app.rwa.xyz/" target="_blank" rel="noopener noreferrer">RWA.xyz</a>';

  var EXPLORE_ASSET = {
    stablecoins: [
      "<strong>KPI strip</strong> — headline totals from the " +
        RWA +
        " <strong>Stablecoins</strong> overview; colored <strong>%</strong> figures are <strong>30-day (30D)</strong> changes.",
      "<strong>Network preview</strong> — first rows from the Stablecoins · <strong>Networks</strong> league; <strong>Total Value</strong> is aggregate stablecoin market cap on that network (current level).",
      "<strong>7D Δ value</strong> uses the embed field <code>value_7d_change</code>; <strong>30D Δ share</strong> is change in market share vs ~30 days ago.",
      "<strong>Full view</strong> — use <strong>Open full overview</strong> for searchable tables and charts on the Stablecoins page.",
    ],
    treasuries: [
      "<strong>KPI strip</strong> — " +
        RWA +
        " <strong>US Treasuries</strong> overview totals; top-line <strong>%</strong> figures are <strong>30-day (30D)</strong>.",
      "<strong>Network preview</strong> — distributed tokenized Treasury value by network (current levels). <strong>7D</strong> and <strong>30D</strong> columns follow the same conventions as other RWA league tables.",
      "<strong>Full view</strong> — open the US Treasuries page for platform leagues and full-screen tables.",
    ],
    tokenized_stocks: [
      "<strong>KPI strip</strong> — " +
        RWA +
        " <strong>Tokenized Stocks</strong> overview; colored <strong>%</strong> figures are <strong>30-day (30D)</strong>.",
      "<strong>Preview tables</strong> — distributed value by network and platform (current levels) from the live Tokenized Stocks views.",
      "<strong>Full view</strong> — open the Tokenized Stocks page for complete leagues and charts.",
    ],
    tokenized_mmf: [
      "<strong>KPI strip</strong> — totals for a <strong>curated</strong> set of tokenized <strong>money market funds</strong> on " +
        RWA +
        ' <a href="https://app.rwa.xyz/treasuries" target="_blank" rel="noopener noreferrer">US Treasuries</a> and ' +
        '<a href="https://app.rwa.xyz/government-bonds" target="_blank" rel="noopener noreferrer">Non-U.S. Government Debt</a> (fixed fund list).',
      "<strong>Network preview</strong> — distributed value summed across each fund's on-chain token deployments by network.",
      "<strong>Full view</strong> — open the Tokenized MMF page for platform (asset-manager) leagues and full tables.",
    ],
  };

  var EXPLORE_PARTICIPANT = {
    participant_networks: [
      "<strong>KPI strip</strong> — " +
        RWA +
        ' <a href="https://app.rwa.xyz/networks" target="_blank" rel="noopener noreferrer">Networks</a> overview; <strong>%</strong> on tiles are <strong>30-day (30D)</strong>.',
      "<strong>Table preview</strong> — distributed RWA value, market share, and holder metrics by network (levels plus 7D / 30D change fields from the page embed).",
      "<strong>Full view</strong> — open the Networks page for search and full-screen tables.",
    ],
    participant_platforms: [
      "<strong>KPI strip</strong> — " +
        RWA +
        ' <a href="https://app.rwa.xyz/platforms" target="_blank" rel="noopener noreferrer">Platforms</a> overview; <strong>%</strong> on tiles are <strong>30-day (30D)</strong>.',
      "<strong>Table preview</strong> — issuer-level distributed value and share metrics (current levels with 7D / 30D changes when present).",
      "<strong>Full view</strong> — open the Platforms page for the complete issuer league.",
    ],
    participant_asset_managers: [
      "<strong>KPI strip</strong> — " +
        RWA +
        ' <a href="https://app.rwa.xyz/asset-managers" target="_blank" rel="noopener noreferrer">Asset Managers</a> overview; <strong>%</strong> on tiles are <strong>30-day (30D)</strong>.',
      "<strong>Table preview</strong> — distributed value and share by manager from the live Asset Managers view.",
      "<strong>Full view</strong> — open the Asset Managers page for the full table.",
    ],
  };

  var PAGE = {
    crypto: {
      before: "#js-crypto-kpi",
      bullets: [
        "<strong>KPI strip</strong> — <strong>Total market cap</strong> and its ~1-month <strong>%</strong> from <a href=\"https://coinpaprika.com/\" target=\"_blank\" rel=\"noopener noreferrer\">CoinPaprika</a> global data. <strong>BTC dominance</strong> compares Bitcoin’s cap to that total; <strong>Stablecoin share</strong> is stablecoin cap vs the sum of this top-50 list (approximate 1M % on share).",
        "<strong>Market-cap chart</strong> — <a href=\"https://www.tradingview.com/symbols/TOTAL/\" target=\"_blank\" rel=\"noopener noreferrer\">TradingView TOTAL</a> (~top 125 coins). The chart level can differ from the KPI total because sources and universes differ.",
        "<strong>Top-50 table</strong> — spot prices and ~1-month <strong>%</strong> from <a href=\"https://www.coingecko.com/\" target=\"_blank\" rel=\"noopener noreferrer\">CoinGecko</a> (CoinCap fallback when 30-day change is missing). Hover tickers for short <strong>About</strong> summaries.",
      ],
    },
    "rwa-global": {
      before: "#js-rwa-global-kpis",
      bullets: [
        "<strong>Source</strong> — " +
          RWA +
          " homepage <strong>Global Market Overview</strong> headline figures and the <strong>Networks</strong> league (distributed / parent networks), scraped from the live site (not the public API product).",
        "<strong>KPI strip</strong> — all colored <strong>%</strong> figures are <strong>30-day (30D)</strong> changes on overview totals.",
        "<strong>Networks table</strong> — searchable preview of distributed RWA value, share, and holder fields; <strong>↗</strong> opens the network on RWA.xyz.",
        "<strong>Explore links</strong> — asset-type and participant index pages show short previews; deep-dive pages hold full tables and charts.",
      ],
    },
    "rwa-stablecoins": {
      before: "#js-deep-kpis",
      bullets: [
        "<strong>Source</strong> — " +
          RWA +
          ' <a href="https://app.rwa.xyz/stablecoins" target="_blank" rel="noopener noreferrer">Stablecoins</a> (Networks and Platforms tabs).',
        "<strong>KPI strip</strong> — overview totals; colored <strong>%</strong> are typically <strong>30-day (30D)</strong>.",
        "<strong>Networks table</strong> — <strong>Total Value</strong> is aggregate stablecoin market cap on that network; <strong>7D Δ value</strong> uses <code>value_7d_change</code> from the embed.",
        "<strong>Platforms table</strong> — issuer-level stablecoin market cap with the same 7D / 30D conventions.",
      ],
    },
    "rwa-treasuries": {
      before: "#js-deep-kpis",
      bullets: [
        "<strong>Source</strong> — " +
          RWA +
          ' <a href="https://app.rwa.xyz/treasuries" target="_blank" rel="noopener noreferrer">US Treasuries</a> distributed views.',
        "<strong>KPI strip</strong> — overview totals; top-line <strong>%</strong> figures are <strong>30-day (30D)</strong>.",
        "<strong>Networks / Platforms</strong> — <strong>Distributed Value</strong> is a current level; 7D and 30D columns follow fields on the live RWA.xyz tables.",
      ],
    },
    "rwa-mmf": {
      before: "#js-deep-kpis",
      bullets: [
        "<strong>Source</strong> — a <strong>fixed curated</strong> set of tokenized <strong>money market funds</strong> on " +
          RWA +
          ' <a href="https://app.rwa.xyz/treasuries" target="_blank" rel="noopener noreferrer">US Treasuries</a> and ' +
          '<a href="https://app.rwa.xyz/government-bonds" target="_blank" rel="noopener noreferrer">Non-U.S. Government Debt</a>.',
        "<strong>KPI strip</strong> — <strong>Distributed value</strong> uses a <strong>30-day (30D)</strong> % vs summed token values 30 days ago; <strong>30D net change</strong> is the dollar change across that same fund set.",
        "<strong>Networks / Platforms / charts</strong> — same curated population; aggregates each fund's token rows by chain and by asset manager.",
      ],
    },
    "rwa-tokenized-stocks": {
      before: "#js-deep-kpis",
      bullets: [
        "<strong>Source</strong> — " +
          RWA +
          ' <a href="https://app.rwa.xyz/stocks" target="_blank" rel="noopener noreferrer">Tokenized Stocks</a> distributed Networks and Platforms views.',
        "<strong>KPI strip</strong> — overview totals; colored <strong>%</strong> are <strong>30-day (30D)</strong>.",
        "<strong>League tables</strong> — distributed value and share metrics (levels plus 7D / 30D changes from the page embed).",
      ],
    },
    "rwa-participants-networks": {
      before: "#js-deep-kpis",
      bullets: [
        "<strong>Source</strong> — " +
          RWA +
          ' <a href="https://app.rwa.xyz/networks" target="_blank" rel="noopener noreferrer">Networks</a> (distributed league).',
        "<strong>KPI strip</strong> — Networks overview totals; <strong>%</strong> on tiles are <strong>30-day (30D)</strong>.",
        "<strong>Table</strong> — RWA value (distributed), market share, holders, and link to each network on RWA.xyz.",
      ],
    },
    "rwa-participants-platforms": {
      before: "#js-deep-kpis",
      bullets: [
        "<strong>Source</strong> — " +
          RWA +
          ' <a href="https://app.rwa.xyz/platforms" target="_blank" rel="noopener noreferrer">Platforms</a> (distributed issuers).',
        "<strong>KPI strip</strong> — Platforms overview totals; <strong>%</strong> on tiles are <strong>30-day (30D)</strong>.",
        "<strong>Table</strong> — issuer-level distributed value and share (current levels with 7D / 30D when present).",
      ],
    },
    "rwa-participants-asset-managers": {
      before: "#js-deep-kpis",
      bullets: [
        "<strong>Source</strong> — " +
          RWA +
          ' <a href="https://app.rwa.xyz/asset-managers" target="_blank" rel="noopener noreferrer">Asset Managers</a>.',
        "<strong>KPI strip</strong> — Asset Managers overview totals; <strong>%</strong> on tiles are <strong>30-day (30D)</strong>.",
        "<strong>Table</strong> — distributed value and share by manager from the live view.",
      ],
    },
    etp: {
      before: "#js-etp-kpi",
      bullets: [
        "<strong>Total AUM / IBIT / ETHA</strong> — latest listed assets from <a href=\"https://stockanalysis.com/list/crypto-etfs/\" target=\"_blank\" rel=\"noopener noreferrer\">StockAnalysis</a>; colored <strong>%</strong> on AUM tiles use Yahoo Finance adjusted closes (~1 mo when available).",
        "<strong>Aggregate AUM %</strong> — estimated weekly aggregate AUM (Yahoo prices — latest reported AUM per fund).",
        "<strong>BTC &amp; ETH Fund flows</strong> — sum of daily net creations/redemptions over ~30 calendar days from <a href=\"https://farside.co.uk/bitcoin-etf-flow-all-data/\" target=\"_blank\" rel=\"noopener noreferrer\">Farside BTC flows</a> and <a href=\"https://farside.co.uk/ethereum-etf-flow-all-data/\" target=\"_blank\" rel=\"noopener noreferrer\">Farside ETH flows</a> (spot ETFs on those tables only). The flow <strong>%</strong> compares that 30-day total to the prior 30 days—not fund performance.",
        "<strong>Table 1Y Flow</strong> — trailing ~12-month sum of the same Farside daily flows per fund.",
      ],
    },
  };

  function panelHtml(bullets) {
    if (!bullets || !bullets.length) return "";
    var lis = bullets
      .map(function (b) {
        return "<li>" + b + "</li>";
      })
      .join("");
    return (
      '<details class="methodology-panel">' +
      "<summary>Data sources &amp; definitions</summary>" +
      '<div class="methodology-panel__body"><ul>' +
      lis +
      "</ul></div></details>"
    );
  }

  function buildElement(bullets) {
    var wrap = document.createElement("div");
    wrap.innerHTML = panelHtml(bullets);
    return wrap.firstElementChild;
  }

  function mountPagePanel() {
    var key = document.body && document.body.getAttribute("data-methodology");
    if (!key || !PAGE[key]) return;
    var cfg = PAGE[key];
    var anchor = document.querySelector(cfg.before);
    if (!anchor || !cfg.bullets) return;
    var el = buildElement(cfg.bullets);
    if (el) anchor.parentNode.insertBefore(el, anchor);
  }

  function exploreBullets(page, sectionId) {
    if (page === "asset") return EXPLORE_ASSET[sectionId] || null;
    if (page === "participant") return EXPLORE_PARTICIPANT[sectionId] || null;
    return null;
  }

  function boot() {
    mountPagePanel();
  }

  global.__PAGE_METHODOLOGY = {
    buildElement: buildElement,
    exploreBullets: exploreBullets,
    panelHtml: panelHtml,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(typeof window !== "undefined" ? window : this);
