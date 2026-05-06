(function () {
  var state = {
    rows: [],
    filtered: [],
    sortKey: "assets_usd",
    sortDir: -1,
  };

  var els = {
    banner: document.getElementById("js-data-banner"),
    kpi: document.getElementById("js-etp-kpi"),
    chart: document.getElementById("aum-chart"),
    pulse: document.getElementById("js-etf-pulse"),
    search: document.getElementById("js-etp-search"),
    toolbar: document.getElementById("js-etp-toolbar"),
    tbody: document.getElementById("js-etp-tbody"),
    thead: document.getElementById("js-etp-thead"),
    ts: document.getElementById("js-etp-generated"),
  };

  function parsePrice(s) {
    if (s == null || s === "") return NaN;
    var x = String(s).replace(/,/g, "").replace(/^\$/, "");
    return parseFloat(x);
  }

  function prepareRow(r) {
    var o = Object.assign({}, r);
    o.price_num = parsePrice(r.price);
    return o;
  }

  function fmt52wTd(n) {
    if (n == null || isNaN(n)) return '<td class="num">—</td>';
    var v = Number(n);
    var cls = v >= 0 ? "pct up" : "pct down";
    return (
      '<td class="num ' + cls + '">' + (v >= 0 ? "+" : "") + v.toFixed(1) + "%</td>"
    );
  }

  function fmtAssets(usd) {
    if (usd == null) return "—";
    var n = Number(usd);
    if (!isFinite(n)) return "—";
    return (n / 1e9).toFixed(2);
  }

  function filingCell(url) {
    if (!url)
      return "<td>—</td>";
    return (
      '<td><a href="' +
      escapeHtml(url) +
      "\" target=\"_blank\" rel=\"noopener noreferrer\">Filing</a></td>"
    );
  }

  function cmp(a, b, key) {
    var va = a[key];
    var vb = b[key];
    if (key === "price_num") {
      va = a.price_num;
      vb = b.price_num;
    }
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    if (typeof va === "number" && typeof vb === "number") {
      if (isNaN(va) && isNaN(vb)) return 0;
      if (isNaN(va)) return 1;
      if (isNaN(vb)) return -1;
      return va - vb;
    }
    return String(va).localeCompare(String(vb));
  }

  function sortRows(arr) {
    var k = state.sortKey;
    if (k === "price") k = "price_num";
    var d = state.sortDir;
    // Descending numeric sorts used to multiply cmp() by d, which inverted "nulls last"
    // and put missing AUM/price at the top. Always park missing/non-finite values last,
    // then apply asc/desc only to comparable numbers.
    if (k === "assets_usd" || k === "price_num") {
      return arr.slice().sort(function (a, b) {
        var va = k === "assets_usd" ? a.assets_usd : a.price_num;
        var vb = k === "assets_usd" ? b.assets_usd : b.price_num;
        var aBad = va == null || (typeof va === "number" && !isFinite(va));
        var bBad = vb == null || (typeof vb === "number" && !isFinite(vb));
        if (aBad && bBad) {
          return String(a.symbol || "").localeCompare(String(b.symbol || ""));
        }
        if (aBad) return 1;
        if (bBad) return -1;
        var na = Number(va);
        var nb = Number(vb);
        if (d < 0) return nb - na;
        return na - nb;
      });
    }
    return arr.slice().sort(function (a2, b2) {
      return d * cmp(a2, b2, k);
    });
  }

  function applyFilter() {
    var q = (els.search && els.search.value ? els.search.value : "").trim().toLowerCase();
    if (!q) {
      state.filtered = state.rows.slice();
    } else {
      state.filtered = state.rows.filter(function (r) {
        return (
          (r.symbol && r.symbol.toLowerCase().indexOf(q) >= 0) ||
          (r.name && r.name.toLowerCase().indexOf(q) >= 0)
        );
      });
    }
    render();
  }

  function renderKpi(k) {
    if (!els.kpi || !k) return;
    var K = window.__ETP_KPI || {};
    var fmtDelta =
      typeof K.fmtPctDelta === "function"
        ? K.fmtPctDelta
        : function (p, w) {
            if (p == null || p === "") return '<span class="kpi-delta neutral">—</span>';
            var n = Number(p);
            var cls = n > 0 ? "up" : n < 0 ? "down" : "neutral";
            return '<span class="kpi-delta ' + cls + '">' + (n > 0 ? "+" : "") + n.toFixed(2) + "%</span>";
          };
    els.kpi.innerHTML =
      '<div class="kpi-cell">' +
      '<span class="kpi-label">Total AUM (listed)</span>' +
      '<span class="kpi-val">' +
      escapeHtml(k.total_aum_display || "—") +
      "</span>" +
      fmtDelta(k.aggregate_pct, k.aggregate_window) +
      "</div>" +
      '<div class="kpi-cell">' +
      '<span class="kpi-label">IBIT · AUM</span>' +
      '<span class="kpi-val">' +
      escapeHtml(k.ibit && k.ibit.aum_display) +
      "</span>" +
      (k.ibit && k.ibit.delta ? fmtDelta(k.ibit.delta.pct, k.ibit.delta.window) : "") +
      "</div>" +
      '<div class="kpi-cell">' +
      '<span class="kpi-label">ETHA · AUM</span>' +
      '<span class="kpi-val">' +
      escapeHtml(k.etha && k.etha.aum_display) +
      "</span>" +
      (k.etha && k.etha.delta ? fmtDelta(k.etha.delta.pct, k.etha.delta.window) : "") +
      "</div>";
  }

  function renderChart(series) {
    if (!els.chart || !series || !series.length || typeof Plotly === "undefined") {
      if (els.chart && (!series || !series.length)) {
        els.chart.innerHTML =
          '<p class="chart-fallback">Chart data unavailable (check export logs).</p>';
      }
      return;
    }
    var x = series.map(function (p) {
      return p.date;
    });
    var y = series.map(function (p) {
      return p.aum_billions;
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
        },
      ],
      {
        margin: { t: 28, r: 16, b: 48, l: 56 },
        paper_bgcolor: "#fafcfd",
        plot_bgcolor: "#f8fafc",
        font: { family: "Outfit, sans-serif", size: 12, color: "#1f4c67" },
        xaxis: { title: "Week" },
        yaxis: { title: "Est. aggregate AUM ($B)" },
        showlegend: false,
      },
      { responsive: true, displayModeBar: true, scrollZoom: true }
    );
  }

  function renderPulse(items) {
    if (!els.pulse) return;
    els.pulse.innerHTML = "";
    if (!items || !items.length) {
      els.pulse.innerHTML =
        '<li class="pulse-list__empty">No ETF headlines matched filters. Try refreshing data export.</li>';
      return;
    }
    items.forEach(function (a) {
      var li = document.createElement("li");
      var href = a.link ? escapeHtml(a.link) : "#";
      var title = escapeHtml(a.title || "");
      var src =
        escapeHtml(a.source || "") + " · " + escapeHtml(fmtDate(a.published) || "");
      li.innerHTML =
        '<a class="pulse-list__a" href="' +
        href +
        '" target="_blank" rel="noopener noreferrer">' +
        title +
        "</a>" +
        '<span class="pulse-list__src">' +
        src +
        "</span>";
      els.pulse.appendChild(li);
    });
  }

  function renderTable() {
    if (!els.tbody) return;
    var sorted = sortRows(state.filtered);
    els.tbody.innerHTML = "";
    sorted.forEach(function (r) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        '<td><span class="sym">' +
        escapeHtml(r.symbol) +
        "</span></td>" +
        "<td>" +
        escapeHtml(r.name) +
        "</td>" +
        '<td class="num">' +
        escapeHtml(String(r.price != null ? r.price : "—")) +
        "</td>" +
        fmt52wTd(r.pct_52w) +
        '<td class="num">' +
        fmtAssets(r.assets_usd) +
        "</td>" +
        "<td>" +
        escapeHtml(r.issuer || "") +
        "</td>" +
        "<td>" +
        escapeHtml(r.custodian || "") +
        "</td>" +
        "<td>" +
        escapeHtml(r.inception || "") +
        "</td>" +
        filingCell(r.fund_filing_url);
      els.tbody.appendChild(tr);
    });
    if (els.toolbar) {
      els.toolbar.innerHTML =
        "Showing <strong>" +
        state.filtered.length +
        "</strong> of <strong>" +
        state.rows.length +
        "</strong> funds.";
    }
  }

  function render() {
    renderTable();
  }

  function wireSort() {
    if (!els.thead) return;
    els.thead.addEventListener("click", function (ev) {
      var th = ev.target.closest("th[data-sort]");
      if (!th) return;
      var key = th.getAttribute("data-sort");
      if (state.sortKey === key) state.sortDir *= -1;
      else {
        state.sortKey = key;
        state.sortDir = key === "name" || key === "symbol" || key === "issuer" ? 1 : -1;
      }
      document.querySelectorAll("#js-etp-thead th").forEach(function (h) {
        h.classList.remove("is-sorted", "is-sorted-asc", "is-sorted-desc");
      });
      th.classList.add("is-sorted", state.sortDir > 0 ? "is-sorted-asc" : "is-sorted-desc");
      render();
    });
  }

  function init() {
    if (els.search) {
      els.search.disabled = false;
      els.search.addEventListener("input", function () {
        applyFilter();
      });
    }
    wireSort();

    Promise.all([
      loadJson("manifest.json").catch(function () {
        return {};
      }),
      loadJson("etp_kpis.json").catch(function () {
        return null;
      }),
      loadJson("aum_series.json").catch(function () {
        return { series: [] };
      }),
      loadJson("etps.json").catch(function () {
        return { rows: [] };
      }),
      loadJson("etf_pulse.json").catch(function () {
        return { items: [] };
      }),
    ]).then(function (out) {
      var manifest = out[0];
      if (manifest.errors && manifest.errors.length && els.banner) {
        els.banner.hidden = false;
        els.banner.textContent =
          "Partial feed warnings: " + manifest.errors.slice(0, 4).join("; ");
      }
      if (manifest.generated_at && els.ts) {
        els.ts.textContent = manifest.generated_at.replace("T", " ").replace(/\.\d+Z$/, " UTC");
      }
      renderKpi(out[1]);
      renderChart((out[2] && out[2].series) || []);
      state.rows = (out[3].rows || []).map(prepareRow);
      state.filtered = state.rows.slice();
      renderPulse((out[4] && out[4].items) || []);
      state.sortKey = "assets_usd";
      state.sortDir = -1;
      render();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
