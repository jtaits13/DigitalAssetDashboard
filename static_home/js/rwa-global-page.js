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

  function isMockParityLayout() {
    return document.body.classList.contains("mock-rwa-global-inner");
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

    var marginRight = Math.min(210, Math.max(118, Math.round(maxPct * 6 + 84)));

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

  function buildCurrencyAxisProps(values, plotWidth, theme) {
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
    var ink = theme && theme.ink ? theme.ink : "#1a3d5c";
    return {
      tickangle: -30,
      tickvals: vals,
      ticktext: vals.map(formatUsdAxisTick),
      tickfont: { size: width < 220 ? 10 : 11, color: ink, family: "Outfit, system-ui, sans-serif" },
    };
  }

  function renderPrimaryCta(host, data, mockLayout) {
    if (!host) return;
    var L = data.links || {};
    var label = L.global_market_link_label || "Open RWA.xyz Global Market";
    var href = L.global_market_on_rwa_xyz || "https://app.rwa.xyz/networks";
    host.hidden = false;
    if (mockLayout) {
      host.className = "cta-row etp-mock-bottom-cta rwa-deep-page-cta";
      host.innerHTML =
        '<a class="btn btn-primary" href="' +
        esc(href) +
        '" target="_blank" rel="noopener noreferrer">' +
        esc(label) +
        "</a>";
    } else {
      host.className = "cta-row rwa-deep-page-cta";
      host.innerHTML =
        '<p><a class="btn btn-primary" href="' +
        esc(href) +
        '" target="_blank" rel="noopener noreferrer">' +
        esc(label) +
        "</a></p>";
    }
  }

  function renderConcBarRows(items) {
    if (!items || !items.length) return "";
    var maxPct = items.reduce(function (m, d) {
      return d.pct > m ? d.pct : m;
    }, 0);
    return items
      .map(function (d) {
        var barWidth = maxPct > 0 ? (d.pct / maxPct) * 100 : 0;
        return (
          '<div class="etp-mock-conc__row">' +
          '<span class="etp-mock-conc__sym">' +
          esc(d.label) +
          "</span>" +
          '<span class="etp-mock-conc__track"><span class="etp-mock-conc__fill" style="width:' +
          barWidth.toFixed(1) +
          '%"></span></span>' +
          '<span class="etp-mock-conc__pct">' +
          d.pct.toFixed(1) +
          "%</span></div>"
        );
      })
      .join("");
  }

  function renderGlobalInsights(rows) {
    var host = $("js-rwa-global-insights");
    if (!host || !isMockParityLayout() || !rows || !rows.length) {
      if (host) host.hidden = true;
      return;
    }
    var sorted = rows.slice().sort(function (a, b) {
      return (Number(b["Market Share"]) || 0) - (Number(a["Market Share"]) || 0);
    });
    var topFive = sorted.slice(0, 5);
    var topFiveSum = topFive.reduce(function (s, r) {
      return s + (Number(r["Market Share"]) || 0);
    }, 0);
    var items = topFive.map(function (r) {
      return { label: String(r.Network || "—"), pct: Number(r["Market Share"]) || 0 };
    });
    var otherPct = Math.max(0, 100 - topFiveSum);
    if (otherPct > 0.15) items.push({ label: "Other", pct: otherPct });
    host.hidden = false;
    host.innerHTML =
      '<div class="etp-mock-insights__panel etp-mock-insights__panel--conc">' +
      '<h3 class="etp-mock-insights__head">Network share (top 5)</h3>' +
      '<p class="etp-mock-conc__dek">Share of aggregate total value by chain (RWA.xyz snapshot).</p>' +
      '<div class="etp-mock-conc__rows etp-mock-conc__rows--grid" role="img" aria-label="Top five networks by total value share">' +
      renderConcBarRows(items) +
      "</div></div>";
  }

  function renderGlobalShareMovers(rows) {
    var moversEl = $("js-rwa-global-share-movers");
    if (!moversEl || !isMockParityLayout() || !rows || !rows.length) return;
    var topNetworks = rows
      .slice()
      .sort(function (a, b) {
        return (Number(b["Total Value"]) || 0) - (Number(a["Total Value"]) || 0);
      })
      .slice(0, 15);
    var moverRows = topNetworks
      .filter(function (r) {
        return r["30D Δ share"] != null && isFinite(Number(r["30D Δ share"]));
      })
      .sort(function (a, b) {
        return Math.abs(Number(b["30D Δ share"])) - Math.abs(Number(a["30D Δ share"]));
      })
      .slice(0, 4);
    var items = moverRows
      .map(function (r) {
        var n = Number(r["30D Δ share"]);
        var cls = n >= 0 ? "up" : "down";
        var d7 = r["7D Δ value"];
        var ctx =
          d7 != null && isFinite(Number(d7))
            ? "7D value " +
              (Number(d7) >= 0 ? "+" : "") +
              Number(d7).toFixed(2) +
              "% · " +
              (Number(r["Market Share"]) || 0).toFixed(1) +
              "% market share"
            : (Number(r["Market Share"]) || 0).toFixed(1) + "% market share";
        return (
          '<li class="crypto-top-mover"><div class="crypto-top-mover__row">' +
          '<span class="crypto-top-mover__label"><strong>' +
          esc(r.Network || "—") +
          "</strong></span>" +
          '<span class="crypto-top-mover__pct pct ' +
          cls +
          '">' +
          (n >= 0 ? "+" : "") +
          n.toFixed(2) +
          "%</span></div>" +
          '<p class="crypto-top-mover__ctx">' +
          esc(ctx) +
          "</p></li>"
        );
      })
      .join("");
    moversEl.innerHTML =
      '<ul class="crypto-top-movers__list">' +
      items +
      '</ul><p class="crypto-story-callout__note"><strong>30D Δ share</strong> is 30-day change in market share (%). Top 15 networks by total value.</p>';
  }

  function drawChart(rows, chartMax, heightPx, chartElId, emptyElId, options) {
    options = options || {};
    var includeOther = options.includeOther === true;
    var el = $(chartElId || "js-rwa-gmo-chart");
    var emptyEl = emptyElId ? $(emptyElId) : $("js-rwa-gmo-chart-empty");
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

    var y;
    var x;
    var text;
    var hasOther = false;
    var barCount;

    if (includeOther && typeof global.buildTopNPlusOtherChartRows === "function") {
      var built = global.buildTopNPlusOtherChartRows(rows, {
        nameCol: "Network",
        valCol: "Total Value",
        topN: chartMax,
        includeOther: true,
      });
      y = built.y;
      x = built.x;
      text = built.text;
      hasOther = built.hasOther;
      barCount = built.barCount;
    } else {
      var sorted = rows.slice().sort(function (a, b) {
        return (Number(b["Total Value"]) || 0) - (Number(a["Total Value"]) || 0);
      });
      var top = sorted.slice(0, chartMax);
      var asc = top.slice().sort(function (a, b) {
        return (Number(a["Total Value"]) || 0) - (Number(b["Total Value"]) || 0);
      });
      y = asc.map(function (r) {
        return String(r.Network != null ? r.Network : "—").trim() || "—";
      });
      x = asc.map(function (r) {
        return Number(r["Total Value"]) || 0;
      });
      text = asc.map(function (r) {
        var s = r["Market Share"];
        if (s == null || !isFinite(Number(s))) return "—% share";
        return Number(s).toFixed(2) + "% share";
      });
      barCount = y.length;
    }

    var theme = typeof global.getZoneChartTheme === "function" ? global.getZoneChartTheme(el) : null;
    var barColor = theme ? theme.bar : "#2a5f82";
    var barOtherColor = theme ? theme.barOther || "#4a7a96" : "#4a7a96";
    var barLine = theme ? theme.barLine : "#1a3d5c";
    var ink = theme ? theme.ink : "#1a3d5c";
    var inkMuted = theme ? theme.inkMuted : "#2a5f82";
    var barColors = y.map(function (label) {
      return label === "Other" ? barOtherColor : barColor;
    });

    var shell =
      el.closest && el.closest(".stable-dash-chart-body")
        ? el.closest(".stable-dash-chart-body")
        : el.closest
          ? el.closest(".rwa-split-chart-shell")
          : el.parentElement;
    var shellW = shell && shell.clientWidth ? shell.clientWidth : el.offsetParent ? el.offsetWidth : 0;
    var m = estimateChartMargins(y, text, shellW);
    var axisProps = buildCurrencyAxisProps(x, Math.max(120, (shellW || 560) - m.l - m.r), theme);

    var trace = {
      type: "bar",
      x: x,
      y: y,
      orientation: "h",
      width: Math.min(0.9, Math.max(0.52, 0.86 - barCount * 0.028)),
      marker: {
        color: hasOther ? barColors : barColor,
        line: { color: barLine, width: 0.5 },
      },
      showlegend: false,
      text: text,
      textposition: "outside",
      textfont: { size: 11, color: inkMuted, family: "Outfit, system-ui, sans-serif" },
      cliponaxis: false,
      hovertemplate: "<b>%{y}</b><br>Total value: %{x:$,.0f}<br>Market share: %{text}<extra></extra>",
    };

    var layout = {
      height: heightPx,
      autosize: true,
      margin: { l: m.l, r: m.r, t: 14, b: 60, pad: 4 },
      bargap: barCount >= 6 ? 0.11 : 0.14,
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "#f8fafc",
      font: { size: 12, color: ink, family: "Outfit, system-ui, sans-serif" },
      showlegend: false,
      xaxis: {
        title: { text: "Total value (USD)", font: { size: 12, color: ink }, standoff: 18 },
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
        tickfont: { family: "Outfit, system-ui, sans-serif", size: 11, color: ink },
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
        var axisProps2 = buildCurrencyAxisProps(x, Math.max(120, wLate - m2.l - m2.r), theme);
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

  function renderGlobalDashboard(rows) {
    var dash = $("js-rwa-global-dashboard");
    if (!dash || !isMockParityLayout() || !rows || !rows.length) {
      if (dash) dash.hidden = true;
      return;
    }
    dash.hidden = false;
    drawChart(rows, 5, 286, "js-rwa-global-dashboard-chart", null, { includeOther: true });
    renderGlobalShareMovers(rows);
  }

  function wireLegacySplitHost(data) {
    var host = $("js-rwa-global-split");
    if (!host) return null;
    host.className = "split-two rwa-split";
    host.style.setProperty("--rwa-split-body-height", String(data.chartHeight || 420) + "px");
    host.innerHTML =
      '<div class="rwa-split-pane">' +
      '<div class="rwa-split-table-head">' +
      '<h3 class="subsection-head rwa-deep-table-h rwa-split-table-head__title">Networks table</h3>' +
      '<div class="rwa-split-table-head__actions" id="js-rwa-global-table-actions"></div></div>' +
      '<div class="rwa-split-table-scroll">' +
      '<table class="data-table data-table--dense rwa-split-data-table"><thead><tr id="js-rwa-gmo-thead-row"></tr></thead>' +
      '<tbody id="js-rwa-gmo-tbody"><tr><td>Loading…</td></tr></tbody></table></div></div>' +
      '<div class="rwa-split-pane rwa-split-pane--chart">' +
      '<h2 class="subsection-head rwa-split-heading">Top networks by value</h2>' +
      '<div class="rwa-split-chart-shell"><div id="js-rwa-gmo-chart" class="aum-chart-host rwa-split-chart-host"></div>' +
      '<p class="muted rwa-split-chart-empty" id="js-rwa-gmo-chart-empty" hidden>No networks match this filter; there is nothing to chart.</p></div>' +
      '<p class="jd-hub-cta-note jd-rwa-gmo-split-note" id="js-rwa-global-chart-note"></p></div>';

    var searchBlock = $("js-rwa-global-search-block");
    if (!searchBlock) {
      var detailStack = $("js-rwa-global-detail-stack");
      if (detailStack) {
        searchBlock = document.createElement("div");
        searchBlock.id = "js-rwa-global-search-block";
        searchBlock.innerHTML =
          '<div class="inline-search rwa-global-search" role="search">' +
          '<label for="rwa-global-q">Search network table</label>' +
          '<input id="rwa-global-q" type="search" name="q" autocomplete="off" placeholder="Filter by network name…" />' +
          '<button type="button" class="btn btn-secondary" id="rwa-global-clear">Clear</button></div>' +
          '<p class="toolbar-note" id="rwa-global-toolbar-note"></p>';
        detailStack.insertBefore(searchBlock, host);
      }
    }
    return host;
  }

  function wireMockTableHost(data) {
    var host = $("js-rwa-global-split");
    if (!host) return null;
    var intro =
      data.section_intro_html ||
      "<strong>Networks</strong> — total value by chain (RWA.xyz Distributed league). Filter by name below.";
    var caption = data.caption_html || "";
    host.className = "etp-mock-table-block rwa-global-mock-league-block";
    host.innerHTML =
      '<div class="rwa-split-table-head inner-table-head">' +
      '<h2 class="subsection-head rwa-split-table-head__title">Networks table</h2>' +
      '<div class="rwa-split-table-head__actions" id="js-rwa-global-table-actions"></div></div>' +
      '<p class="rwa-global-mock-league-intro">' +
      intro +
      "</p>" +
      '<label class="search-field etp-mock-table-search">' +
      '<span class="search-field__label">Search network table</span>' +
      '<input id="rwa-global-q" type="search" class="search-field__input" autocomplete="off" placeholder="Filter by network name…" /></label>' +
      '<div class="etp-mock-table-meta" aria-live="polite">' +
      '<p class="etp-mock-table-meta__count toolbar-note" id="rwa-global-toolbar-note"></p>' +
      '<div class="rwa-table-actions" id="js-rwa-global-meta-actions"></div></div>' +
      '<div class="table-wrap table-wrap--scroll rwa-split-table-scroll">' +
      '<table class="data-table data-table--dense data-table--sortable"><thead><tr id="js-rwa-gmo-thead-row"></tr></thead>' +
      '<tbody id="js-rwa-gmo-tbody"><tr><td>Loading…</td></tr></tbody></table></div>' +
      (caption
        ? '<div class="rwa-table-footnote-row"><p class="source-cap rwa-table-footnote-row__cap">' + caption + "</p></div>"
        : "");
    return host;
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
        note.textContent = "Showing " + rows.length + " of " + total + ' networks matching "' + esc(q) + '".';
      } else if (isMockParityLayout()) {
        note.textContent = "Showing all " + rows.length + " networks.";
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

    if (!isMockParityLayout()) {
      drawChart(rows, state.chartMax, state.chartHeight);
    }
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
    var mockLayout = isMockParityLayout();

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
      renderKpis($("js-rwa-global-kpis"), data.kpis || [], "");
      hide(errCta, false);
      renderPrimaryCta(errCta, data, mockLayout);
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

    renderKpis($("js-rwa-global-kpis"), data.kpis || [], "");

    var koSection = $("js-rwa-global-ko-section");
    var macroHost = $("js-rwa-global-macro");
    var hasKo = !!(data.macro_observations_html && String(data.macro_observations_html).trim());
    hide(koSection, !hasKo);
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
      if (H.exploreCompactHtml) {
        exploreHost.innerHTML = H.exploreCompactHtml(data.links || {});
      } else {
        exploreHost.innerHTML = data.explore_gateways_html || "";
      }
      if (typeof global.finalizeHubAnchors === "function") {
        global.finalizeHubAnchors(exploreHost);
      }
    }

    if (mockLayout) {
      renderGlobalInsights(rows);
      renderGlobalDashboard(rows);
    }

    var chartMax = data.chart_max_bars != null ? Number(data.chart_max_bars) : 12;
    var chartHeight = data.chart_height_px != null ? Number(data.chart_height_px) : 420;

    if (mockLayout) {
      wireMockTableHost(data);
    } else {
      wireLegacySplitHost({ chartHeight: chartHeight });
      var chartNote = $("js-rwa-global-chart-note");
      if (chartNote) chartNote.innerHTML = data.chart_note_html || "";
      var captionHost = $("js-rwa-global-caption");
      if (captionHost) captionHost.innerHTML = data.caption_html || "";
    }

    var splitRoot = $("js-rwa-global-split");
    var tableWrap = splitRoot ? splitRoot.querySelector(".table-wrap, .rwa-split-table-scroll") : null;
    var tableEl = tableWrap ? tableWrap.querySelector("table") : splitRoot ? splitRoot.querySelector("table") : null;
    var titleActions = $("js-rwa-global-table-actions");
    var metaActions = $("js-rwa-global-meta-actions");
    var actionRow = null;

    if (attachTableFullscreenButton && tableWrap && tableEl) {
      actionRow = attachTableFullscreenButton(tableWrap, tableEl, {
        title: "RWA Global Market Overview networks table",
        downloadPlacement: "title-row",
        downloadAnchor: titleActions,
        actionRow: mockLayout && metaActions ? metaActions : undefined,
      });
    }

    if (appendRwaActionLink && actionRow && !mockLayout) {
      appendRwaActionLink(actionRow, {
        href: (data.links && data.links.global_market_on_rwa_xyz) || "https://app.rwa.xyz/networks",
        label: (data.links && data.links.global_market_link_label) || "Open RWA.xyz Global Market",
        className: "btn btn-primary",
      });
      hide(bottomCta, true);
    } else {
      hide(bottomCta, false);
      renderPrimaryCta(bottomCta, data, mockLayout);
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

    if (typeof global.finalizeHubAnchors === "function") {
      global.finalizeHubAnchors(document.body);
    }
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
            (e && e.message) || "Could not load rwa_global_market.json.";
        }
      });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})(typeof window !== "undefined" ? window : this);
