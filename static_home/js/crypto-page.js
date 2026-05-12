(function () {
  var state = {
    rows: [],
    filtered: [],
    sortKey: "market_cap_usd",
    sortDir: -1,
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

  function renderChart(payload) {
    if (els.chartHeading && payload && payload.title) {
      els.chartHeading.textContent = payload.title;
    }
    if (els.caption) {
      els.caption.textContent = payload && payload.caption ? payload.caption : "";
    }
    if (els.method) {
      els.method.textContent = payload && payload.method_note ? payload.method_note : "";
    }
    if (!els.chart) return;
    if (!payload || !payload.series || !payload.series.length || typeof Plotly === "undefined") {
      els.chart.innerHTML = '<p class="chart-fallback">Chart data is unavailable right now.</p>';
      return;
    }
    var x = payload.series.map(function (point) {
      return point.date;
    });
    var y = payload.series.map(function (point) {
      return Number(point.market_cap_usd || 0) / 1e12;
    });
    Plotly.newPlot(
      els.chart,
      [
        {
          x: x,
          y: y,
          type: "scatter",
          mode: "lines",
          fill: "tozeroy",
          fillcolor: "rgba(37,128,156,0.15)",
          line: { color: "#25809c", width: 2 },
          hovertemplate: "%{x}<br>$%{y:.2f}T<extra></extra>",
        },
      ],
      {
        margin: { t: 28, r: 16, b: 64, l: 56 },
        paper_bgcolor: "#fafcfd",
        plot_bgcolor: "#f8fafc",
        font: { family: "Outfit, sans-serif", size: 12, color: "#1f4c67" },
        xaxis: { title: { text: "Date", standoff: 16 }, automargin: true, tickangle: -30 },
        yaxis: { title: { text: payload.axis_label || "Estimated market cap ($T)", standoff: 8 }, automargin: true },
        showlegend: false,
      },
      { responsive: true, displayModeBar: true, scrollZoom: true }
    );
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
      return { series: [] };
    }),
  ])
    .then(function (results) {
      var kpis = results[0] || {};
      var prices = results[1] || { rows: [] };
      var chart = results[2] || { series: [] };
      renderKpi(kpis);
      renderChart(chart);
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
      renderChart({ series: [] });
      state.rows = [];
      applyFilter();
    });

  if (els.search) {
    els.search.addEventListener("input", applyFilter);
  }
})();
