/**
 * Full static RWA Global Market Overview — data from ``static_home/data/rwa_global_market.json``.
 */
(function (global) {
  function esc(s) {
    var fn = global.escapeHtml;
    return typeof fn === "function" ? fn(String(s == null ? "" : s)) : String(s == null ? "" : s);
  }

  function $(id) {
    return document.getElementById(id);
  }

  function renderPrimaryCta(host, data) {
    if (!host) return;
    var L = data.links || {};
    var label = L.global_market_link_label || "Open RWA.xyz Global Market";
    var href = L.global_market_on_rwa_xyz || "https://app.rwa.xyz/networks";
    host.hidden = false;
    host.innerHTML =
      '<p><a class="btn btn-primary" href="' +
      esc(href) +
      '" target="_blank" rel="noopener noreferrer">' +
      esc(label) +
      "</a></p>";
  }

  function drawChart(rows, chartMax, heightPx) {
    var el = $("js-rwa-gmo-chart");
    var emptyEl = $("js-rwa-gmo-chart-empty");
    if (!el || typeof Plotly === "undefined") return;

    if (!rows || !rows.length) {
      try {
        Plotly.purge(el);
      } catch (e) {}
      el.innerHTML = "";
      if (emptyEl) emptyEl.hidden = false;
      return;
    }

    if (emptyEl) emptyEl.hidden = true;

    var sorted = rows.slice().sort(function (a, b) {
      return (Number(b["Total Value"]) || 0) - (Number(a["Total Value"]) || 0);
    });
    var top = sorted.slice(0, chartMax);
    var asc = top.slice().sort(function (a, b) {
      return (Number(a["Total Value"]) || 0) - (Number(b["Total Value"]) || 0);
    });

    var y = asc.map(function (r) {
      return String(r.Network != null ? r.Network : "—").trim() || "—";
    });
    var x = asc.map(function (r) {
      return Number(r["Total Value"]) || 0;
    });
    var text = asc.map(function (r) {
      var s = r["Market Share"];
      if (s == null || !isFinite(Number(s))) return "—% share";
      return Number(s).toFixed(2) + "% share";
    });

    var trace = {
      type: "bar",
      x: x,
      y: y,
      orientation: "h",
      marker: {
        color: "#25809C",
        line: { color: "#1F4C67", width: 0.5 },
      },
      showlegend: false,
      text: text,
      textposition: "outside",
      textfont: { size: 11, color: "#3E6A7A" },
      cliponaxis: false,
      hovertemplate: "<b>%{y}</b><br>Total value: %{x:$,.0f}<br>Market share: %{text}<extra></extra>",
    };

    var layout = {
      height: heightPx,
      margin: { l: 8, r: 100, t: 14, b: 36 },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "#f8fafc",
      font: { size: 12, color: "#1F4C67" },
      showlegend: false,
      xaxis: {
        title: { text: "Total value (USD)", font: { size: 12, color: "#1F4C67" } },
        tickprefix: "$",
        separatethousands: true,
      },
      yaxis: {
        type: "category",
        categoryorder: "array",
        categoryarray: y,
        showticklabels: true,
      },
    };

    var config = { displayModeBar: false, responsive: true };
    Plotly.react(el, [trace], layout, config);
  }

  function applyFilter(state, renderTable) {
    var q = state.filter.trim().toLowerCase();
    var rows = state.allRows.filter(function (r) {
      var n = String(r.Network != null ? r.Network : "").toLowerCase();
      return !q || n.indexOf(q) >= 0;
    });

    var note = $("rwa-global-toolbar-note");
    if (note) {
      var total = state.allRows.length;
      if (total === 0) {
        note.textContent = "";
      } else if (q) {
        note.textContent =
          "Showing " + rows.length + " of " + total + ' networks matching "' + q + '".';
      } else {
        note.textContent =
          "Showing all " + rows.length + " networks from the homepage Global Market table.";
      }
    }

    var thead = $("js-rwa-gmo-thead-row");
    var tbody = $("js-rwa-gmo-tbody");
    renderTable(thead, tbody, state.columns, rows);

    if (rows.length === 0 && state.allRows.length > 0 && tbody) {
      var colspan = state.columns && state.columns.length ? state.columns.length : 1;
      tbody.innerHTML =
        '<tr><td colspan="' + colspan + '">No networks match this filter.</td></tr>';
    }

    drawChart(rows, state.chartMax, state.chartHeight);
  }

  function wireSearch(state, renderTable) {
    var input = $("rwa-global-q");
    var clearBtn = $("rwa-global-clear");
    if (input) {
      input.addEventListener("input", function () {
        state.filter = input.value || "";
        applyFilter(state, renderTable);
      });
    }
    if (clearBtn && input) {
      clearBtn.addEventListener("click", function () {
        input.value = "";
        state.filter = "";
        applyFilter(state, renderTable);
        input.focus();
      });
    }
  }

  function hide(el, hidden) {
    if (!el) return;
    el.hidden = !!hidden;
  }

  function renderFull(data) {
    var H = global.__RWA_STATIC_HELPERS || {};
    var renderKpis = H.renderKpis;
    var renderTable = H.renderTable;

    var banner = $("js-rwa-global-banner");
    if (banner) {
      if (data.error && String(data.error).trim()) {
        banner.hidden = false;
        banner.textContent = data.error;
      } else {
        banner.hidden = true;
        banner.textContent = "";
      }
    }

    var dek = $("js-rwa-global-dek");
    if (dek && data.page_subtitle_html) dek.innerHTML = data.page_subtitle_html;

    var rows = data.rows || [];
    var errNoRows = !!(data.error && String(data.error).trim()) && (!rows || !rows.length);
    var emptyNoErr = !(data.error && String(data.error).trim()) && (!rows || !rows.length);

    var snapshot = $("js-rwa-global-snapshot");
    var detailStack = $("js-rwa-global-detail-stack");
    var emptyMsg = $("js-rwa-global-empty");
    var errCta = $("js-rwa-global-error-cta");
    var bottomCta = $("js-rwa-global-bottom-cta");

    hide(emptyMsg, true);
    hide(errCta, true);
    hide(bottomCta, true);
    if (errCta) errCta.innerHTML = "";
    if (bottomCta) bottomCta.innerHTML = "";

    var footerNote = $("js-rwa-global-footer-note");
    if (footerNote) footerNote.textContent = data.footer_note || "";

    if (errNoRows) {
      hide(snapshot, false);
      hide(detailStack, true);
      renderKpis($("js-rwa-global-kpis"), data.kpis || [], data.kpi_window_note || "");
      hide(errCta, false);
      renderPrimaryCta(errCta, data);
      return;
    }

    if (emptyNoErr) {
      hide(snapshot, true);
      hide(detailStack, true);
      hide(emptyMsg, false);
      emptyMsg.textContent = data.empty_message || "No network rows returned.";
      return;
    }

    hide(snapshot, false);
    hide(detailStack, false);

    renderKpis($("js-rwa-global-kpis"), data.kpis || [], data.kpi_window_note || "");

    var macroHost = $("js-rwa-global-macro");
    if (macroHost) macroHost.innerHTML = data.macro_observations_html || "";

    var exploreHost = $("js-rwa-global-explore");
    if (exploreHost) exploreHost.innerHTML = data.explore_gateways_html || "";

    var captionHost = $("js-rwa-global-caption");
    if (captionHost) captionHost.innerHTML = data.caption_html || "";

    var chartNote = $("js-rwa-global-chart-note");
    if (chartNote) chartNote.innerHTML = data.chart_note_html || "";

    hide(bottomCta, false);
    renderPrimaryCta(bottomCta, data);

    var chartMax = data.chart_max_bars != null ? Number(data.chart_max_bars) : 12;
    var chartHeight = data.chart_height_px != null ? Number(data.chart_height_px) : 420;

    var state = {
      allRows: rows,
      columns: data.columns || [],
      filter: "",
      chartMax: chartMax,
      chartHeight: chartHeight,
    };

    var qInput = $("rwa-global-q");
    if (qInput) qInput.value = "";

    wireSearch(state, renderTable);
    applyFilter(state, renderTable);
  }

  function boot() {
    var H = global.__RWA_STATIC_HELPERS || {};
    if (!H.renderKpis || !H.renderTable) {
      console.error("rwa-global-page: load rwa-onchain-home.js before rwa-global-page.js.");
      return;
    }

    loadJson("rwa_global_market.json")
      .then(renderFull)
      .catch(function (e) {
        var banner = $("js-rwa-global-banner");
        if (banner) {
          banner.hidden = false;
          banner.textContent =
            (e && e.message) ||
            "Could not load rwa_global_market.json. Run python scripts/export_static_site_data.py.";
        }
      });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})(typeof window !== "undefined" ? window : this);
