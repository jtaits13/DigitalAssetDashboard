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

  function estimateChartMargins(yLabels, textLabels, shellWidth) {
    var i;
    var maxLab = 4;
    for (i = 0; i < yLabels.length; i++) {
      maxLab = Math.max(maxLab, String(yLabels[i] || "").length);
    }
    var maxPct = 6;
    for (i = 0; i < textLabels.length; i++) {
      maxPct = Math.max(maxPct, String(textLabels[i] || "").length);
    }

    var sw = typeof shellWidth === "number" && shellWidth > 0 ? shellWidth : 560;

    var perCharLeft = 7.5;
    var basePad = 76;
    var fromText = Math.round(maxLab * perCharLeft + basePad);
    var minByWidth = Math.round(sw * 0.44);
    var marginLeft = Math.min(440, Math.max(176, Math.max(fromText, minByWidth)));

    var marginRight = Math.min(
      210,
      Math.max(118, Math.round(maxPct * 6 + 84))
    );

    return { l: marginLeft, r: marginRight };
  }

  function formatUsdAxisTick(v) {
    var n = Number(v) || 0;
    var abs = Math.abs(n);
    if (abs >= 1e9) return "$" + (n / 1e9).toFixed(abs >= 10e9 ? 0 : 1).replace(/\.0$/, "") + "B";
    if (abs >= 1e6) return "$" + (n / 1e6).toFixed(abs >= 10e6 ? 0 : 1).replace(/\.0$/, "") + "M";
    if (abs >= 1e3) return "$" + (n / 1e3).toFixed(abs >= 10e3 ? 0 : 1).replace(/\.0$/, "") + "K";
    return "$" + Math.round(n).toLocaleString();
  }

  function niceTickStep(rawStep) {
    if (!(rawStep > 0)) return 1;
    var pow = Math.pow(10, Math.floor(Math.log(rawStep) / Math.LN10));
    var base = rawStep / pow;
    var mult = base <= 1 ? 1 : base <= 2 ? 2 : base <= 5 ? 5 : 10;
    return mult * pow;
  }

  function buildCurrencyAxisProps(values, plotWidth) {
    var maxVal = 0;
    var i;
    for (i = 0; i < values.length; i++) {
      maxVal = Math.max(maxVal, Number(values[i]) || 0);
    }
    var width = typeof plotWidth === "number" && plotWidth > 0 ? plotWidth : 260;
    var tickCount = width < 150 ? 2 : width < 240 ? 3 : width < 360 ? 4 : 5;
    var step = niceTickStep(maxVal / Math.max(1, tickCount - 1));
    var maxTick = step * Math.max(1, Math.ceil(maxVal / step));
    var vals = [];
    for (i = 0; i <= maxTick + step * 0.2; i += step) {
      vals.push(i);
      if (vals.length > 8) break;
    }
    return {
      tickangle: -30,
      tickvals: vals,
      ticktext: vals.map(formatUsdAxisTick),
      tickfont: { size: width < 220 ? 10 : 11 },
    };
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
      if (el._rwaResizeMarginTimer) {
        clearTimeout(el._rwaResizeMarginTimer);
        el._rwaResizeMarginTimer = null;
      }
      if (el._rwaResizeObs) {
        try {
          el._rwaResizeObs.disconnect();
        } catch (eD) {}
        el._rwaResizeObs = null;
      }
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

    var shell = el.closest ? el.closest(".rwa-split-chart-shell") : el.parentElement;
    var shellW = shell && shell.clientWidth ? shell.clientWidth : el.offsetParent ? el.offsetWidth : 0;
    var m = estimateChartMargins(y, text, shellW);
    var axisProps = buildCurrencyAxisProps(x, Math.max(120, (shellW || 560) - m.l - m.r));

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
      autosize: true,
      margin: { l: m.l, r: m.r, t: 14, b: 60, pad: 4 },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "#f8fafc",
      font: { size: 12, color: "#1F4C67" },
      showlegend: false,
      xaxis: {
        title: { text: "Total value (USD)", font: { size: 12, color: "#1F4C67" }, standoff: 18 },
        automargin: true,
        tickprefix: "$",
        separatethousands: true,
        tickangle: axisProps.tickangle,
        tickvals: axisProps.tickvals,
        ticktext: axisProps.ticktext,
        tickfont: axisProps.tickfont,
      },
      yaxis: {
        type: "category",
        categoryorder: "array",
        categoryarray: y,
        showticklabels: true,
      },
    };

    var config = { displayModeBar: false, responsive: true, scrollZoom: false };
    Plotly.react(el, [trace], layout, config);
    function relayoutMargins() {
      try {
        var wLate =
          shell && shell.clientWidth
            ? shell.clientWidth
            : el.offsetWidth > 0
              ? el.offsetWidth
              : shellW || 560;
        var m2 = estimateChartMargins(y, text, wLate);
        var axisProps2 = buildCurrencyAxisProps(x, Math.max(120, wLate - m2.l - m2.r));
        Plotly.relayout(el, {
          margin: { l: m2.l, r: m2.r, t: 14, b: 60, pad: 4 },
          "xaxis.tickangle": axisProps2.tickangle,
          "xaxis.tickvals": axisProps2.tickvals,
          "xaxis.ticktext": axisProps2.ticktext,
          "xaxis.tickfont.size": axisProps2.tickfont.size,
        });
      } catch (e3) {}
      try {
        Plotly.Plots.resize(el);
      } catch (e2) {}
    }

    setTimeout(function () {
      requestAnimationFrame(function () {
        relayoutMargins();
      });
    }, 0);

    if (shell && typeof ResizeObserver !== "undefined") {
      if (el._rwaResizeMarginTimer) {
        clearTimeout(el._rwaResizeMarginTimer);
        el._rwaResizeMarginTimer = null;
      }
      if (el._rwaResizeObs) {
        try {
          el._rwaResizeObs.disconnect();
        } catch (eDC) {}
        el._rwaResizeObs = null;
      }
      try {
        el._rwaResizeObs = new ResizeObserver(function () {
          if (el._rwaResizeMarginTimer) {
            clearTimeout(el._rwaResizeMarginTimer);
          }
          el._rwaResizeMarginTimer = setTimeout(function () {
            el._rwaResizeMarginTimer = null;
            relayoutMargins();
          }, 64);
        });
        el._rwaResizeObs.observe(shell);
      } catch (eOb) {}
    }
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
    var attachTableFullscreenButton = H.attachRwaTableFullscreenButton;
    var appendRwaActionLink = H.appendRwaActionLink;

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
    if (macroHost) {
      if (H.renderKeyObservationsCallout) {
        H.renderKeyObservationsCallout(macroHost, data.macro_observations_html || "", {
          title: "Key observations",
        });
      } else {
        macroHost.innerHTML = data.macro_observations_html || "";
      }
    }

    var exploreHost = $("js-rwa-global-explore");
    if (exploreHost) {
      exploreHost.innerHTML = data.explore_gateways_html || "";
      if (typeof global.finalizeHubAnchors === "function") {
        global.finalizeHubAnchors(exploreHost);
      }
    }

    var captionHost = $("js-rwa-global-caption");
    if (captionHost) captionHost.innerHTML = data.caption_html || "";

    var chartNote = $("js-rwa-global-chart-note");
    if (chartNote) chartNote.innerHTML = data.chart_note_html || "";

    var chartMax = data.chart_max_bars != null ? Number(data.chart_max_bars) : 12;
    var chartHeight = data.chart_height_px != null ? Number(data.chart_height_px) : 420;

    var splitRoot = $("js-rwa-global-split");
    if (splitRoot) splitRoot.style.setProperty("--rwa-split-body-height", String(chartHeight) + "px");
    if (attachTableFullscreenButton && splitRoot) {
      var actionRow = attachTableFullscreenButton(
        splitRoot.querySelector(".rwa-split-table-scroll"),
        splitRoot.querySelector("table"),
        {
          title: "RWA Global Market Overview networks table",
          downloadPlacement: "title-row",
          downloadAnchor: $("js-rwa-global-table-actions"),
        }
      );
      if (appendRwaActionLink && actionRow) {
        appendRwaActionLink(actionRow, {
          href: (data.links && data.links.global_market_on_rwa_xyz) || "https://app.rwa.xyz/networks",
          label: (data.links && data.links.global_market_link_label) || "Open RWA.xyz Global Market",
          className: "btn btn-primary",
        });
        hide(bottomCta, true);
      } else {
        hide(bottomCta, false);
        renderPrimaryCta(bottomCta, data);
      }
    } else {
      hide(bottomCta, false);
      renderPrimaryCta(bottomCta, data);
    }

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
            "Could not load rwa_global_market.json.";
        }
      });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})(typeof window !== "undefined" ? window : this);
