(function () {
  var DEFAULT_CHART_META = {
    title: "Crypto total market cap",
    provider_url: "https://www.tradingview.com/symbols/TOTAL/",
    symbol: "CRYPTOCAP:TOTAL",
    caption: "TradingView TOTAL represents crypto market capitalization using the top 125 coins.",
    method_note:
      "The interactive market-cap chart is rendered client-side from TradingView so it does not depend on rate-limited historical API calls.",
  };
  var TV_WIDGET_SRC = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";

  var CATEGORY_TABS = [
    { id: "all", label: "All" },
    { id: "l1", label: "Layer 1" },
    { id: "stablecoin", label: "Stablecoin" },
    { id: "cex", label: "CEX" },
    { id: "defi", label: "DeFi" },
    { id: "meme", label: "Meme" },
    { id: "rwa", label: "RWA / Tokenized" },
    { id: "other", label: "Other" },
  ];

  var state = {
    rows: [],
    filtered: [],
    sortKey: "market_cap_usd",
    sortDir: -1,
    category: "all",
  };

  var els = {
    banner: document.getElementById("js-data-banner"),
    kpi: document.getElementById("js-crypto-kpi"),
    keyObs: document.getElementById("js-crypto-key-obs"),
    chart: document.getElementById("crypto-market-cap-chart"),
    search: document.getElementById("js-crypto-search"),
    tabs: document.getElementById("js-crypto-category-tabs"),
    toolbar: document.getElementById("js-crypto-toolbar"),
    tbody: document.getElementById("js-crypto-tbody"),
    thead: document.getElementById("js-crypto-thead"),
    ts: document.getElementById("js-crypto-generated"),
    caption: document.getElementById("js-crypto-chart-caption"),
    method: document.getElementById("js-crypto-chart-method"),
    chartHeading: document.getElementById("js-crypto-chart-heading"),
    chartLink: document.getElementById("js-crypto-chart-link"),
  };

  function escapeHtml(s) {
    if (typeof window !== "undefined" && typeof window.escapeHtml === "function") {
      return window.escapeHtml(s);
    }
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function cryptoKpiApi() {
    return (typeof window !== "undefined" && window.__CRYPTO_KPI) || {};
  }

  function categoryLabel(row) {
    if (row.category_label) return row.category_label;
    var api = cryptoKpiApi();
    return api.categoryLabel ? api.categoryLabel(row.category || "other") : row.category || "Other";
  }

  function categoryClass(row) {
    var slug = row.category || "other";
    var api = cryptoKpiApi();
    return api.categoryClass ? api.categoryClass(slug) : "crypto-cat crypto-cat--" + slug;
  }

  function showErr(msg) {
    if (!els.banner) return;
    els.banner.hidden = false;
    els.banner.textContent = msg;
  }

  function fmtPrice(usd) {
    if (usd == null) return "—";
    var n = Number(usd);
    if (!isFinite(n)) return "—";
    if (n >= 1000) return "$" + n.toLocaleString(undefined, { maximumFractionDigits: 0 });
    if (n >= 1) return "$" + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (n >= 0.01) return "$" + n.toLocaleString(undefined, { minimumFractionDigits: 4, maximumFractionDigits: 4 });
    return "$" + n.toPrecision(4);
  }

  function fmtCap(usd) {
    if (usd == null) return "—";
    var n = Number(usd);
    if (!isFinite(n)) return "—";
    if (n >= 1e12) return "$" + (n / 1e12).toFixed(2) + "T";
    if (n >= 1e9) return "$" + (n / 1e9).toFixed(2) + "B";
    if (n >= 1e6) return "$" + (n / 1e6).toFixed(1) + "M";
    return "$" + n.toLocaleString();
  }

  function fmtPctCell(pct) {
    if (pct == null) return '<td class="num">—</td>';
    var n = Number(pct);
    if (!isFinite(n)) return '<td class="num">—</td>';
    var cls = n >= 0 ? "pct up" : "pct down";
    return '<td class="num ' + cls + '">' + (n >= 0 ? "+" : "") + n.toFixed(2) + "%</td>";
  }

  function cmp(a, b, key) {
    var va = a[key];
    var vb = b[key];
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    if (typeof va === "number" && typeof vb === "number") {
      if (!isFinite(va) && !isFinite(vb)) return 0;
      if (!isFinite(va)) return 1;
      if (!isFinite(vb)) return -1;
      return va - vb;
    }
    return String(va).localeCompare(String(vb));
  }

  function sortRows(rows) {
    var key = state.sortKey;
    var dir = state.sortDir;
    return rows.slice().sort(function (a, b) {
      var va = a[key];
      var vb = b[key];
      var aBad = va == null || (typeof va === "number" && !isFinite(va));
      var bBad = vb == null || (typeof vb === "number" && !isFinite(vb));
      if (aBad && bBad) return String(a.symbol || "").localeCompare(String(b.symbol || ""));
      if (aBad) return 1;
      if (bBad) return -1;
      if (typeof va === "number" && typeof vb === "number") {
        return dir < 0 ? vb - va : va - vb;
      }
      return dir * cmp(a, b, key);
    });
  }

  var lastKpisPayload = null;

  function renderKpiStrip(payload) {
    var api = cryptoKpiApi();
    if (api.renderCryptoKpis && els.kpi) {
      api.renderCryptoKpis(els.kpi, payload || {});
    }
  }

  function renderKeyObservationsBlock(kpis) {
    if (!els.keyObs) return;
    var api = cryptoKpiApi();
    var html = (kpis && kpis.key_observations_html) || "";
    if (api.renderKeyObservationsCallout && api.renderKeyObservationsCallout(els.keyObs, html)) {
      return;
    }
    els.keyObs.hidden = true;
    els.keyObs.innerHTML = "";
  }

  function renderKpi(payload, priceRows) {
    lastKpisPayload = payload || null;
    renderKpiStrip(payload);
    renderKeyObservationsBlock(payload);
  }

  function chartWidgetConfig(meta) {
    return {
      width: "100%",
      height: 460,
      symbol: meta.symbol || DEFAULT_CHART_META.symbol,
      interval: "1W",
      timeframe: "12M",
      timezone: "Etc/UTC",
      theme: "light",
      style: "1",
      locale: "en",
      withdateranges: true,
      hide_side_toolbar: false,
      allow_symbol_change: false,
      save_image: false,
      calendar: false,
      details: false,
      hotlist: false,
      studies: [],
    };
  }

  function renderChart(meta) {
    meta = meta || DEFAULT_CHART_META;
    if (els.chartHeading && meta && meta.title) {
      els.chartHeading.textContent = meta.title || DEFAULT_CHART_META.title;
    }
    if (els.caption) {
      els.caption.textContent = meta.caption || DEFAULT_CHART_META.caption;
    }
    if (els.method) {
      els.method.textContent = meta.method_note || DEFAULT_CHART_META.method_note;
    }
    if (els.chartLink) {
      els.chartLink.href = meta.provider_url || DEFAULT_CHART_META.provider_url;
    }
    if (!els.chart) return;
    els.chart.innerHTML = "";
    var shell = document.createElement("div");
    shell.className = "tradingview-widget-container tv-chart-shell";
    var host = document.createElement("div");
    host.className = "tradingview-widget-container__widget tv-chart-shell__widget";
    shell.appendChild(host);
    els.chart.appendChild(shell);

    var script = document.createElement("script");
    script.type = "text/javascript";
    script.async = true;
    script.src = TV_WIDGET_SRC;
    script.innerHTML = JSON.stringify(chartWidgetConfig(meta));
    script.onerror = function () {
      els.chart.innerHTML =
        '<p class="chart-fallback">The TradingView chart could not load here. Use the link below to open it directly.</p>';
    };
    shell.appendChild(script);
  }

  function renderChartFallback(msg) {
    if (!els.chart) return;
    els.chart.innerHTML = '<p class="chart-fallback">' + escapeHtml(msg) + "</p>";
  }

  function renderChartLegacy(payload) {
    if (!payload || !payload.series || !payload.series.length) {
      renderChartFallback("Chart data is unavailable right now.");
      return;
    }
    renderChartFallback("A legacy chart payload was loaded unexpectedly.");
  }

  function renderCategoryTabs() {
    if (!els.tabs) return;
    els.tabs.innerHTML = "";
    els.tabs.setAttribute("role", "tablist");
    els.tabs.setAttribute("aria-label", "Filter by asset category");
    CATEGORY_TABS.forEach(function (tab) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "crypto-cat-tab" + (state.category === tab.id ? " is-active" : "");
      btn.setAttribute("role", "tab");
      btn.setAttribute("aria-selected", state.category === tab.id ? "true" : "false");
      btn.setAttribute("data-category", tab.id);
      btn.textContent = tab.label;
      btn.addEventListener("click", function () {
        state.category = tab.id;
        els.tabs.querySelectorAll(".crypto-cat-tab").forEach(function (b) {
          var on = b.getAttribute("data-category") === state.category;
          b.classList.toggle("is-active", on);
          b.setAttribute("aria-selected", on ? "true" : "false");
        });
        applyFilter();
      });
      els.tabs.appendChild(btn);
    });
  }

  function wireTableFullscreen() {
    var fs = window.__TABLE_FULLSCREEN;
    if (!fs || !fs.attachTableFullscreenButton || !els.tbody) return;
    var wrap = els.tbody.closest ? els.tbody.closest(".table-wrap") : null;
    var table = wrap ? wrap.querySelector("table") : null;
    if (!wrap || !table) return;
    fs.attachTableFullscreenButton(wrap, table, {
      title: "Crypto prices table",
      filename: "crypto-prices",
    });
  }

  function renderTable() {
    if (!els.tbody) return;
    els.tbody.innerHTML = "";
    if (!state.filtered.length) {
      els.tbody.innerHTML = '<tr><td colspan="8">No coins matched the current filter.</td></tr>';
    } else {
      sortRows(state.filtered).forEach(function (row) {
        var tr = document.createElement("tr");
        var w = typeof window !== "undefined" ? window : {};
        var blurb = (row.about_blurb || "").trim();
        var wrap =
          typeof w.wrapCryptoHint === "function"
            ? w.wrapCryptoHint
            : function (txt, b, cls) {
                return w.escapeHtml(String(txt || ""));
              };
        var detailCell = row.detail_url
          ? '<td><a href="' +
            escapeHtml(row.detail_url) +
            '" target="_blank" rel="noopener noreferrer">Open</a></td>'
          : "<td>—</td>";
        tr.innerHTML =
          '<td class="num">' +
          escapeHtml(String(row.rank != null ? row.rank : "—")) +
          "</td>" +
          '<td><span class="sym">' +
          wrap(row.symbol || "", blurb, "") +
          "</span></td>" +
          "<td>" +
          escapeHtml(row.name || "") +
          "</td>" +
          '<td><span class="' +
          escapeHtml(categoryClass(row)) +
          '">' +
          escapeHtml(categoryLabel(row)) +
          "</span></td>" +
          '<td class="num">' +
          escapeHtml(fmtPrice(row.price_usd)) +
          "</td>" +
          fmtPctCell(row.pct_30d) +
          '<td class="num">' +
          escapeHtml(fmtCap(row.market_cap_usd)) +
          "</td>" +
          detailCell;
        els.tbody.appendChild(tr);
      });
    }
    if (typeof window !== "undefined" && typeof window.bindCryptoHints === "function") {
      window.bindCryptoHints(els.tbody);
    }
    if (els.toolbar) {
      var catNote = state.category === "all" ? "" : " in <strong>" + escapeHtml(categoryLabel({ category: state.category })) + "</strong>";
      els.toolbar.innerHTML =
        "Showing <strong>" +
        state.filtered.length +
        "</strong> of <strong>" +
        state.rows.length +
        "</strong> coins" +
        catNote +
        ".";
    }
  }

  function applyFilter() {
    var q = (els.search && els.search.value ? els.search.value : "").trim().toLowerCase();
    state.filtered = state.rows.filter(function (row) {
      if (state.category !== "all" && (row.category || "other") !== state.category) {
        return false;
      }
      if (!q) return true;
      return (
        (row.symbol && row.symbol.toLowerCase().indexOf(q) >= 0) ||
        (row.name && row.name.toLowerCase().indexOf(q) >= 0)
      );
    });
    renderTable();
  }

  function updateSortClass() {
    if (!els.thead) return;
    els.thead.querySelectorAll("th[data-sort]").forEach(function (th) {
      th.classList.remove("is-sorted", "is-sorted-asc", "is-sorted-desc");
      th.removeAttribute("aria-sort");
    });
    var active = els.thead.querySelector('th[data-sort="' + state.sortKey + '"]');
    if (active) {
      active.classList.add("is-sorted", state.sortDir > 0 ? "is-sorted-asc" : "is-sorted-desc");
      active.setAttribute("aria-sort", state.sortDir > 0 ? "ascending" : "descending");
    }
  }

  function wireSort() {
    if (!els.thead || els.thead._cryptoSortBound) return;
    els.thead._cryptoSortBound = true;
    els.thead.addEventListener("click", function (ev) {
      var th = ev.target.closest("th[data-sort]");
      if (!th) return;
      var key = th.getAttribute("data-sort");
      if (!key) return;
      if (state.sortKey === key) state.sortDir *= -1;
      else {
        state.sortKey = key;
        state.sortDir = key === "symbol" || key === "name" || key === "category" ? 1 : -1;
      }
      updateSortClass();
      renderTable();
    });
  }

  function renderTimestamp(payload) {
    if (!els.ts || !payload || !payload.generated_at) return;
    var dt = new Date(payload.generated_at);
    els.ts.textContent = isNaN(dt.getTime()) ? "—" : "Last updated: " + dt.toLocaleString();
  }

  renderCategoryTabs();

  var freshApi = window.__DATA_FRESHNESS || {};
  var loadTimed =
    typeof freshApi.loadJsonWithTimeout === "function"
      ? freshApi.loadJsonWithTimeout
      : typeof window.loadJson === "function"
        ? window.loadJson
        : null;

  function applyChartMeta(meta) {
    meta = meta || DEFAULT_CHART_META;
    if (els.chartHeading && meta.title) {
      els.chartHeading.textContent = meta.title;
    }
    if (els.caption && meta.caption) {
      els.caption.textContent = meta.caption;
    }
    if (els.method && meta.method_note) {
      els.method.textContent = meta.method_note;
    }
    if (els.chartLink && meta.provider_url) {
      els.chartLink.href = meta.provider_url;
    }
  }

  function mountChartEarly() {
    if (!els.chart || els.chart._tvMounted) return;
    els.chart._tvMounted = true;
    renderChart(DEFAULT_CHART_META);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountChartEarly);
  } else {
    mountChartEarly();
  }

  function renderSnapshotFreshness(kpis, prices) {
    if (!freshApi.renderFreshness) return;
    freshApi.renderFreshness(document.getElementById("js-crypto-snapshot-as-of"), {
      at: (kpis && kpis.generated_at) || (prices && prices.generated_at),
      source: (kpis && kpis.source) || "CoinPaprika + CoinGecko",
      mode: "snapshot",
    });
  }

  if (!loadTimed) {
    showErr(
      "Page loader failed (static-base.js). Hard refresh (Ctrl+Shift+R) or check that js/static-base.js deployed."
    );
  } else {
    wireSort();
    wireTableFullscreen();

    var kpisPromise = loadTimed("crypto_kpis.json", 14000).catch(function () {
      return null;
    });
    var pricesPromise = loadTimed("crypto_prices.json", 14000).catch(function () {
      return { rows: [] };
    });
    var chartPromise = loadTimed("crypto_market_cap_series.json", 10000).catch(function () {
      return DEFAULT_CHART_META;
    });

    kpisPromise.then(function (kpis) {
      renderKpi(kpis || {}, state.rows);
      if (kpis && kpis.error) showErr(kpis.error);
    });

    pricesPromise.then(function (prices) {
      prices = prices || { rows: [] };
      state.rows = (prices.rows || []).slice();
      updateSortClass();
      applyFilter();
      renderKeyObservationsBlock(lastKpisPayload);
      if (prices.error) showErr(prices.error);
    });

    chartPromise.then(function (chart) {
      chart = chart || DEFAULT_CHART_META;
      if (chart.series && chart.series.length) {
        renderChartLegacy(chart);
      } else {
        applyChartMeta(chart);
      }
      if (chart.error) showErr(chart.error);
    });

    Promise.all([kpisPromise, pricesPromise, chartPromise])
      .then(function (results) {
        var kpis = results[0];
        var prices = results[1];
        renderSnapshotFreshness(kpis, prices);
        renderTimestamp(kpis && kpis.generated_at ? kpis : prices);
      })
      .catch(function (err) {
        showErr(
          "Could not load the crypto data page. " + (err && err.message ? err.message : "")
        );
        state.rows = [];
        applyFilter();
      });
  }

  if (els.search) {
    els.search.addEventListener("input", applyFilter);
  }
})();
