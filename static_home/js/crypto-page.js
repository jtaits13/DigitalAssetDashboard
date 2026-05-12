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
  var TV_TIME_FRAMES = {
    "1M": { timeframe: "1M", resolution: "1D" },
    "6M": { timeframe: "6M", resolution: "1D" },
    "1Y": { timeframe: "12M", resolution: "1W" },
    "5Y": { timeframe: "60M", resolution: "1W" },
  };
  var state = {
    rows: [],
    filtered: [],
    sortKey: "market_cap_usd",
    sortDir: -1,
    timeframe: "1M",
  };

  var els = {
    banner: document.getElementById("js-data-banner"),
    kpi: document.getElementById("js-crypto-kpi"),
    chart: document.getElementById("crypto-market-cap-chart"),
    search: document.getElementById("js-crypto-search"),
    toolbar: document.getElementById("js-crypto-toolbar"),
    tbody: document.getElementById("js-crypto-tbody"),
    thead: document.getElementById("js-crypto-thead"),
    ts: document.getElementById("js-crypto-generated"),
    caption: document.getElementById("js-crypto-chart-caption"),
    method: document.getElementById("js-crypto-chart-method"),
    chartHeading: document.getElementById("js-crypto-chart-heading"),
    chartLink: document.getElementById("js-crypto-chart-link"),
  };

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

  function renderKpi(payload) {
    if (!els.kpi || !payload) return;
    var K = window.__ETP_KPI || {};
    var fmtDelta =
      typeof K.fmtPctDelta === "function"
        ? K.fmtPctDelta
        : function (p) {
            if (p == null || p === "") return '<span class="kpi-delta neutral">—</span>';
            var n = Number(p);
            var cls = n > 0 ? "up" : n < 0 ? "down" : "neutral";
            return '<span class="kpi-delta ' + cls + '">' + (n > 0 ? "+" : "") + n.toFixed(2) + "%</span>";
          };
    var primary = payload.primary || {};
    var btc = payload.btc || {};
    var eth = payload.eth || {};
    els.kpi.innerHTML =
      '<div class="kpi-cell">' +
      '<span class="kpi-label">' +
      escapeHtml(primary.label || "Total market cap") +
      "</span>" +
      '<span class="kpi-val">' +
      escapeHtml(primary.value_display || "—") +
      "</span>" +
      fmtDelta(primary.delta && primary.delta.pct, primary.delta && primary.delta.window) +
      "</div>" +
      '<div class="kpi-cell">' +
      '<span class="kpi-label">' +
      escapeHtml(btc.label || "BTC price") +
      "</span>" +
      '<span class="kpi-val">' +
      escapeHtml(btc.value_display || "—") +
      "</span>" +
      fmtDelta(btc.delta && btc.delta.pct, btc.delta && btc.delta.window) +
      "</div>" +
      '<div class="kpi-cell">' +
      '<span class="kpi-label">' +
      escapeHtml(eth.label || "ETH price") +
      "</span>" +
      '<span class="kpi-val">' +
      escapeHtml(eth.value_display || "—") +
      "</span>" +
      fmtDelta(eth.delta && eth.delta.pct, eth.delta && eth.delta.window) +
      "</div>";
  }

  function chartWidgetConfig(meta) {
    var tf = TV_TIME_FRAMES[state.timeframe] || TV_TIME_FRAMES["1M"];
    return {
      autosize: true,
      symbol: meta.symbol || DEFAULT_CHART_META.symbol,
      interval: tf.resolution,
      timeframe: tf.timeframe,
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
      time_frames: [
        { text: "1m", resolution: "1D", description: "1 Month", title: "1M" },
        { text: "6m", resolution: "1D", description: "6 Months", title: "6M" },
        { text: "1y", resolution: "1W", description: "1 Year", title: "1Y" },
        { text: "5y", resolution: "1W", description: "5 Years", title: "5Y" },
      ],
    };
  }

  function updateTimeframeButtons() {
    document.querySelectorAll(".crypto-chart-range[data-timeframe]").forEach(function (btn) {
      var active = btn.getAttribute("data-timeframe") === state.timeframe;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
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
    updateTimeframeButtons();
  }

  function wireTimeframeButtons(chartMeta) {
    var buttons = document.querySelectorAll(".crypto-chart-range[data-timeframe]");
    if (!buttons.length) return;
    buttons.forEach(function (btn) {
      if (btn._cryptoRangeBound) return;
      btn._cryptoRangeBound = true;
      btn.addEventListener("click", function () {
        var next = btn.getAttribute("data-timeframe") || "1M";
        if (next === state.timeframe) return;
        state.timeframe = next;
        renderChart(chartMeta || DEFAULT_CHART_META);
      });
    });
  }

  function renderChartFallback(msg) {
    if (!els.chart) return;
    els.chart.innerHTML = '<p class="chart-fallback">' + escapeHtml(msg) + "</p>";
    updateTimeframeButtons();
  }

  function renderChartLegacy(payload) {
    if (!payload || !payload.series || !payload.series.length) {
      renderChartFallback("Chart data is unavailable right now.");
      return;
    }
    renderChartFallback("A legacy chart payload was loaded unexpectedly.");
  }

  function renderTable() {
    if (!els.tbody) return;
    els.tbody.innerHTML = "";
    if (!state.filtered.length) {
      els.tbody.innerHTML = '<tr><td colspan="7">No coins matched the current filter.</td></tr>';
    } else {
      sortRows(state.filtered).forEach(function (row) {
        var tr = document.createElement("tr");
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
          escapeHtml(row.symbol || "") +
          "</span></td>" +
          "<td>" +
          escapeHtml(row.name || "") +
          "</td>" +
          '<td class="num">' +
          escapeHtml(fmtPrice(row.price_usd)) +
          "</td>" +
          fmtPctCell(row.pct_24h) +
          '<td class="num">' +
          escapeHtml(fmtCap(row.market_cap_usd)) +
          "</td>" +
          detailCell;
        els.tbody.appendChild(tr);
      });
    }
    if (els.toolbar) {
      els.toolbar.innerHTML =
        "Showing <strong>" +
        state.filtered.length +
        "</strong> of <strong>" +
        state.rows.length +
        "</strong> coins.";
    }
  }

  function applyFilter() {
    var q = (els.search && els.search.value ? els.search.value : "").trim().toLowerCase();
    if (!q) {
      state.filtered = state.rows.slice();
    } else {
      state.filtered = state.rows.filter(function (row) {
        return (
          (row.symbol && row.symbol.toLowerCase().indexOf(q) >= 0) ||
          (row.name && row.name.toLowerCase().indexOf(q) >= 0)
        );
      });
    }
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
        state.sortDir = key === "symbol" || key === "name" ? 1 : -1;
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

  Promise.all([
    loadJson("crypto_kpis.json").catch(function () {
      return null;
    }),
    loadJson("crypto_prices.json").catch(function () {
      return { rows: [] };
    }),
    loadJson("crypto_market_cap_series.json").catch(function () {
      return DEFAULT_CHART_META;
    }),
  ])
    .then(function (results) {
      var kpis = results[0] || {};
      var prices = results[1] || { rows: [] };
      var chart = results[2] || DEFAULT_CHART_META;
      renderKpi(kpis);
      if (chart && chart.series) renderChartLegacy(chart);
      else renderChart(chart);
      wireTimeframeButtons(chart);
      state.rows = (prices.rows || []).slice();
      updateSortClass();
      applyFilter();
      wireSort();
      renderTimestamp(kpis.generated_at ? kpis : prices);
      if ((kpis && kpis.error) || (prices && prices.error) || (chart && chart.error)) {
        showErr(kpis.error || prices.error || chart.error);
      }
    })
    .catch(function (err) {
      showErr("Could not load the crypto data page. " + (err && err.message ? err.message : ""));
      renderChart(DEFAULT_CHART_META);
      state.rows = [];
      applyFilter();
    });

  if (els.search) {
    els.search.addEventListener("input", applyFilter);
  }
})();
