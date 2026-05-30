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
    snapshotAsOf: document.getElementById("js-etp-snapshot-as-of"),
    keyObs: document.getElementById("js-etp-key-obs"),
    concentration: document.getElementById("etp-concentration-chart"),
    chart: document.getElementById("aum-chart"),
    pulse: document.getElementById("js-etf-pulse"),
    search: document.getElementById("js-etp-search"),
    toolbar: document.getElementById("js-etp-toolbar"),
    tbody: document.getElementById("js-etp-tbody"),
    thead: document.getElementById("js-etp-thead"),
    ts: document.getElementById("js-etp-generated"),
  };

  var freshApi = window.__DATA_FRESHNESS || {};
  var loadTimed =
    typeof freshApi.loadJsonWithTimeout === "function"
      ? freshApi.loadJsonWithTimeout
      : function (name) {
          return loadJson(name);
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

  function wireTableFullscreen() {
    var fs = window.__TABLE_FULLSCREEN;
    if (!fs || !fs.attachTableFullscreenButton) return;
    var wrap = document.querySelector(".table-wrap--scroll");
    var table = wrap ? wrap.querySelector("table") : null;
    if (!wrap || !table) return;
    fs.attachTableFullscreenButton(wrap, table, { title: "U.S. ETP fund table", filename: "us-etp-funds" });
  }

  function renderKpi(k) {
    if (!els.kpi || !k) return;
    var snap = window.__SNAPSHOT_KPI;
    if (snap && typeof snap.renderEtpSnapshot === "function") {
      snap.renderEtpSnapshot(els.kpi, k);
    }
  }

  function renderChart(series) {
    if (!els.chart || !series || !series.length || typeof Plotly === "undefined") {
      if (els.chart && (!series || !series.length)) {
        els.chart.innerHTML =
          '<p class="chart-fallback">Chart data is unavailable right now.</p>';
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
        margin: { t: 28, r: 16, b: 64, l: 56 },
        paper_bgcolor: "#fafcfd",
        plot_bgcolor: "#f8fafc",
        font: { family: "Outfit, sans-serif", size: 12, color: "#1f4c67" },
        xaxis: { title: { text: "Week", standoff: 16 }, automargin: true, tickangle: -30 },
        yaxis: { title: { text: "Est. aggregate AUM ($B)", standoff: 8 }, automargin: true },
        showlegend: false,
      },
      { responsive: true, displayModeBar: true, scrollZoom: true }
    );
  }

  function concentrationFundLabel(row) {
    var ticker = String(row.symbol || "").trim();
    var company = String(row.issuer || row.name || "").trim();
    if (ticker && company) return ticker + " (" + company + ")";
    if (ticker) return ticker;
    if (company) return company;
    return "—";
  }

  /** Top funds by share of listed AUM (descending %). */
  function buildConcentrationSeries(rows) {
    var withAum = (rows || []).filter(function (r) {
      var n = Number(r.assets_usd);
      return isFinite(n) && n > 0;
    });
    if (!withAum.length) return null;
    var total = withAum.reduce(function (sum, r) {
      return sum + Number(r.assets_usd);
    }, 0);
    if (!isFinite(total) || total <= 0) return null;

    var top = withAum
      .slice()
      .sort(function (a, b) {
        return Number(b.assets_usd) - Number(a.assets_usd);
      })
      .slice(0, 5);
    var series = top.map(function (r) {
      return {
        label: concentrationFundLabel(r),
        pct: (100 * Number(r.assets_usd)) / total,
      };
    });
    var topSum = series.reduce(function (s, d) {
      return s + d.pct;
    }, 0);
    var restPct = 100 - topSum;
    if (restPct > 0.15) {
      series.push({ label: "All other listed", pct: restPct });
    }
    return series;
  }

  function renderConcentration(rows) {
    if (!els.concentration) return;
    var series = buildConcentrationSeries(rows);
    if (!series || !series.length) {
      els.concentration.innerHTML =
        '<p class="chart-fallback">Concentration data is unavailable right now.</p>';
      return;
    }

    var xMax = Math.min(
      100,
      series.reduce(function (m, d) {
        return d.pct > m ? d.pct : m;
      }, 0) + 8
    );
    var parts = [
      '<figure class="etp-conc-chart" role="img" aria-labelledby="etp-conc-chart-title">',
      '<p class="u-vh" id="etp-conc-chart-title">AUM concentration: largest funds as a percent of listed AUM</p>',
      '<div class="etp-conc-chart__grid">',
      '<div class="etp-conc-chart__head">',
      '<span class="etp-conc-chart__y-head">Ticker (company)</span>',
      '<span class="etp-conc-chart__bar-head" aria-hidden="true"></span>',
      '<span class="etp-conc-chart__pct-head" aria-hidden="true"></span>',
      "</div>",
    ];

    series.forEach(function (d) {
      var barWidth = xMax > 0 ? (d.pct / xMax) * 100 : 0;
      var tip = d.label + ": " + d.pct.toFixed(1) + "% of listed AUM";
      parts.push(
        '<div class="etp-conc-chart__row">',
        '<span class="etp-conc-chart__label" title="' +
          escapeHtml(tip) +
          '">' +
          escapeHtml(d.label) +
          "</span>",
        '<div class="etp-conc-chart__track" aria-hidden="true">',
        '<span class="etp-conc-chart__bar" style="width:' +
          barWidth.toFixed(2) +
          '%"></span>',
        "</div>",
        '<span class="etp-conc-chart__pct">' + d.pct.toFixed(1) + "%</span>",
        "</div>"
      );
    });

    parts.push(
      "</div>",
      '<p class="etp-conc-chart__x-label">% of listed AUM</p>',
      "</figure>"
    );

    els.concentration.innerHTML = parts.join("");
  }

  function renderPulse(items) {
    if (!els.pulse) return;
    els.pulse.innerHTML = "";
    if (!items || !items.length) {
      els.pulse.innerHTML =
        '<li class="pulse-list__empty">No ETF/ETP headlines matched the current filters.</li>';
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
        (window.__ETP_KPI && typeof window.__ETP_KPI.renderSymbolTd === "function"
          ? window.__ETP_KPI.renderSymbolTd(r.symbol)
          : '<td><span class="sym">' + escapeHtml(r.symbol) + "</span></td>") +
        '<td class="data-table__name">' +
        escapeHtml(r.name) +
        "</td>" +
        '<td class="num">' +
        escapeHtml(String(r.price != null ? r.price : "—")) +
        "</td>" +
        fmt52wTd(r.pct_52w) +
        (window.__ETP_KPI && typeof window.__ETP_KPI.fmtFlowCell === "function"
          ? window.__ETP_KPI.fmtFlowCell(r.flow_1y_usd)
          : '<td class="num">—</td>') +
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
    wireTableFullscreen();
    if (els.search) {
      els.search.disabled = false;
      els.search.addEventListener("input", function () {
        applyFilter();
      });
    }
    wireSort();

    Promise.all([
      loadTimed("manifest.json", 12000).catch(function () {
        return {};
      }),
      loadTimed("etp_kpis.json", 14000).catch(function () {
        return null;
      }),
      loadTimed("aum_series.json", 14000).catch(function () {
        return { series: [] };
      }),
      loadTimed("etps.json", 14000).catch(function () {
        return { rows: [] };
      }),
      loadTimed("etf_pulse.json", 12000).catch(function () {
        return { items: [] };
      }),
    ]).then(function (out) {
      var manifest = out[0];
      var kpis = out[1];
      var aum = out[2];
      var etps = out[3];
      var pulse = out[4];
      if (manifest.errors && manifest.errors.length && els.banner) {
        els.banner.hidden = false;
        els.banner.textContent =
          "Partial feed warnings: " + manifest.errors.slice(0, 4).join("; ");
      }
      var tsIso =
        (kpis && kpis.generated_at) ||
        etps.generated_at ||
        manifest.etp_refreshed_at ||
        manifest.generated_at;
      if (freshApi.renderFreshness) {
        freshApi.renderFreshness(els.snapshotAsOf, {
          at: tsIso,
          source: "StockAnalysis · Yahoo · Farside",
          mode: "snapshot",
        });
      }
      if (tsIso && els.ts) {
        els.ts.textContent = String(tsIso).replace("T", " ").replace(/\.\d+Z$/, " UTC");
      }
      renderKpi(kpis);
      var koApi = window.__CRYPTO_KPI || {};
      if (typeof koApi.renderKeyObservationsCallout === "function") {
        koApi.renderKeyObservationsCallout(
          els.keyObs,
          (kpis && kpis.key_observations_html) || "",
          { title: "Key observations" }
        );
      } else if (els.keyObs && kpis && kpis.key_observations_html) {
        els.keyObs.hidden = false;
        els.keyObs.innerHTML = kpis.key_observations_html;
      } else if (els.keyObs) {
        els.keyObs.hidden = true;
        els.keyObs.innerHTML = "";
      }
      renderChart((aum && aum.series) || []);
      state.rows = (etps.rows || []).map(prepareRow);
      state.filtered = state.rows.slice();
      renderConcentration(state.rows);
      renderPulse((pulse && pulse.items) || []);
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
