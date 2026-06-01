/**
 * Full-depth RWA asset pages (Stablecoins, US Treasuries, Tokenized Stocks).
 * Loads JSON named by ``data-rwa-deep-json`` on ``<body>`` for the RWA deep-dive pages.
 */
(function (global) {
  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    var fn = global.escapeHtml;
    return typeof fn === "function" ? fn(String(s == null ? "" : s)) : String(s == null ? "" : s);
  }

  function assetPath(rel) {
    var S = global.__STATIC;
    return S && typeof S.assetUrl === "function" ? S.assetUrl(rel) : rel;
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
    var fromText = Math.round(maxLab * 6.25 + 48);
    var minByWidth = Math.round(sw * 0.24);
    var marginLeft = Math.min(312, Math.max(140, Math.max(fromText, minByWidth) + 12));
    var marginRight = Math.min(
      188,
      Math.max(96, Math.round(maxPct * 5.5 + 64))
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

  function filterRows(rows, nameCol, q) {
    var qq = String(q || "")
      .trim()
      .toLowerCase();
    if (!qq) return (rows || []).slice();
    return (rows || []).filter(function (r) {
      return String(r[nameCol] != null ? r[nameCol] : "")
        .toLowerCase()
        .indexOf(qq) >= 0;
    });
  }

  function drawHorizontalBar(chartEl, rowsFiltered, league, payload) {
    if (!chartEl || typeof Plotly === "undefined") return;
    var cfg = league;
    var nameCol = cfg.name_column;
    var valCol = cfg.value_column;
    var maxBars = payload.chart_max_bars != null ? Number(payload.chart_max_bars) : 12;

    try {
      Plotly.purge(chartEl);
    } catch (e) {}

    if (!rowsFiltered || !rowsFiltered.length) {
      chartEl.innerHTML = "";
      return;
    }

    var sortedDesc = rowsFiltered.slice().sort(function (a, b) {
      return (Number(b[valCol]) || 0) - (Number(a[valCol]) || 0);
    });
    var top = sortedDesc.slice(0, maxBars);
    var asc = top.slice().sort(function (a, b) {
      return (Number(a[valCol]) || 0) - (Number(b[valCol]) || 0);
    });

    var y = asc.map(function (r) {
      return String(r[nameCol] != null ? r[nameCol] : "—").trim() || "—";
    });
    var x = asc.map(function (r) {
      return Number(r[valCol]) || 0;
    });
    var text = asc.map(function (r) {
      var ms = r["Market Share"];
      if (ms == null || !isFinite(Number(ms))) return "—% share";
      return Number(ms).toFixed(2) + "% share";
    });

    var shell =
      chartEl.closest && chartEl.closest(".rwa-split-chart-shell")
        ? chartEl.closest(".rwa-split-chart-shell")
        : chartEl.parentElement;
    var shellW = shell && shell.clientWidth ? shell.clientWidth : chartEl.offsetWidth || 560;
    var m = estimateChartMargins(y, text, shellW);
    var axisProps = buildCurrencyAxisProps(x, Math.max(120, shellW - m.l - m.r));

    var barThickness = Math.min(0.9, Math.max(0.58, 0.86 - y.length * 0.028));

    var trace = {
      type: "bar",
      x: x,
      y: y,
      orientation: "h",
      width: barThickness,
      marker: {
        color: "#25809C",
        line: { color: "#1F4C67", width: 0.5 },
      },
      showlegend: false,
      text: text,
      textposition: "outside",
      textfont: { size: 11, color: "#3E6A7A" },
      cliponaxis: false,
      hovertemplate:
        "<b>%{y}</b><br>Value: %{x:$,.0f}<br>%{text}<extra></extra>",
    };

    var heightPx =
      league.split_body_height_px != null ? Number(league.split_body_height_px) : 420;
    if (shell) {
      var shellH = shell.clientHeight || shell.offsetHeight;
      if (shellH > 0) heightPx = Math.round(shellH);
    }

    var layout = {
      height: heightPx,
      autosize: true,
      margin: { l: m.l, r: m.r, t: 12, b: 56, pad: 2 },
      bargap: 0.14,
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "#f8fafc",
      font: { size: 12, color: "#1F4C67" },
      showlegend: false,
      xaxis: {
        title: {
          text: String(valCol) + " (USD)",
          font: { size: 12, color: "#1F4C67" },
          standoff: 18,
        },
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
        automargin: true,
        ticklabelstandoff: 8,
      },
    };

    Plotly.react(chartEl, [trace], layout, { displayModeBar: false, responsive: true, scrollZoom: false });
    setTimeout(function () {
      try {
        var wLate = shell && shell.clientWidth ? shell.clientWidth : chartEl.offsetWidth || shellW || 560;
        var m2 = estimateChartMargins(y, text, wLate);
        var axisProps2 = buildCurrencyAxisProps(x, Math.max(120, wLate - m2.l - m2.r));
        Plotly.relayout(chartEl, {
          margin: { l: m2.l, r: m2.r, t: 12, b: 56, pad: 2 },
          "xaxis.tickangle": axisProps2.tickangle,
          "xaxis.tickvals": axisProps2.tickvals,
          "xaxis.ticktext": axisProps2.ticktext,
          "xaxis.tickfont.size": axisProps2.tickfont.size,
        });
      } catch (e3) {}
      try {
        Plotly.Plots.resize(chartEl);
      } catch (e2) {}
    }, 0);
  }

  function renderDeepPage(payload) {
    var H = global.__RWA_STATIC_HELPERS || {};
    var renderKpis = H.renderKpis;
    var renderTable = H.renderTable;
    var attachTableFullscreenButton = H.attachRwaTableFullscreenButton;
    var appendRwaActionLink = H.appendRwaActionLink;
    if (!renderKpis || !renderTable) {
      var b0 = $("js-deep-banner");
      if (b0) {
        b0.hidden = false;
        b0.textContent =
          "Dashboard scripts did not initialize (missing table/KPI helpers). Check the browser Network tab that js/static-base.js and js/rwa-onchain-home.js return 200, then hard refresh.";
      }
      return;
    }

    if (!global.loadJson) {
      var bl = $("js-deep-banner");
      if (bl) {
        bl.hidden = false;
        bl.textContent = "Some page assets could not load. Hard refresh and try again.";
      }
      return;
    }

    if (payload.page_title) document.title = payload.page_title;

    var band = $("js-deep-band");
    if (band) band.textContent = payload.band_label || "";

    var titleEl = $("js-deep-title");
    if (titleEl) {
      var titleText = payload.page_title || "";
      titleText = titleText.replace(/\s*[—–-]\s*Digital Assets Dashboard\s*$/i, "").trim();
      titleEl.textContent = titleText || payload.band_label || "";
    }

    var sub = $("js-deep-subtitle");
    if (sub) sub.innerHTML = payload.page_subtitle_html || "";

    var banner = $("js-deep-banner");
    if (banner) {
      banner.hidden = true;
      banner.textContent = "";
      banner.innerHTML = "";
    }

    var snap = $("js-deep-snapshot");
    var kpis = $("js-deep-kpis");
    if (snap && kpis) {
      snap.hidden = false;
      renderKpis(kpis, payload.kpis || [], payload.kpi_window_note || "", { hideIfEmpty: true });
    }

    var ko = $("js-deep-ko");
    if (ko) {
      if (H.renderKeyObservationsCallout) {
        H.renderKeyObservationsCallout(ko, payload.key_observations_html || "", {
          title: "Key observations",
        });
      } else {
        ko.innerHTML = payload.key_observations_html || "";
      }
    }

    var mode = payload.error_mode || "";
    var errMsg = payload.error_detail || "";

    function setOptionalDeepHtml(idS, html) {
      var el = $(idS);
      if (!el) return;
      var raw = html == null ? "" : String(html);
      if (!raw.trim()) {
        el.innerHTML = "";
        el.hidden = true;
        return;
      }
      el.innerHTML = raw;
      el.hidden = false;
    }

    function wireLeague(league, prefix, data) {
      var host = $(prefix + "-wrap");
      if (!host || !league || !league.columns || !league.columns.length) {
        if (host) host.hidden = true;
        return null;
      }

      host.hidden = false;
      host.className = "rwa-deep-league-panel";

      var wideNote = league.wide_chart_note_html != null ? String(league.wide_chart_note_html) : "";
      var colNote =
        league.chart_note_html != null && String(league.chart_note_html).trim()
          ? '<p class="jd-hub-cta-note">' + league.chart_note_html + "</p>"
          : "";
      host.innerHTML =
        '<h2 class="subsection-head">' +
        esc(league.block_heading || "") +
        "</h2>" +
        (league.section_intro_html
          ? '<div class="muted rwa-deep-section-intro">' + league.section_intro_html + "</div>"
          : "") +
        '<div class="inline-search" role="search">' +
        '<label for="' +
        prefix +
        '-q">' +
        esc(league.search_label || "Search table") +
        "</label>" +
        '<input id="' +
        prefix +
        '-q" type="search" autocomplete="off" placeholder="' +
        esc(league.search_placeholder || "") +
        '" />' +
        '<button type="button" class="btn btn-secondary" id="' +
        prefix +
        '-clear">Clear</button>' +
        "</div>" +
        '<p class="toolbar-note" id="' +
        prefix +
        '-note"></p>' +
        '<div class="split-two rwa-split" id="' +
        prefix +
        '-split" style="--rwa-split-body-height:' +
        String(league.split_body_height_px || 420) +
        'px">' +
        '<div class="rwa-split-pane">' +
        '<h3 class="subsection-head rwa-deep-table-h">' +
        esc(league.table_heading || "Table") +
        "</h3>" +
        '<div class="rwa-split-table-scroll">' +
        "<table class=\"data-table data-table--dense\"><thead><tr id=\"" +
        prefix +
        '-thead"></tr></thead><tbody id="' +
        prefix +
        '-tbody"></tbody></table></div>' +
        (league.caption_html
          ? '<div class="rwa-caption-html rwa-deep-caption">' + league.caption_html + "</div>"
          : "") +
        "</div>" +
        '<div class="rwa-split-pane rwa-split-pane--chart">' +
        '<h3 class="subsection-head rwa-deep-table-h">' +
        esc(league.chart_heading || "Top by value") +
        "</h3>" +
        '<div class="rwa-split-chart-shell">' +
        '<p class="muted rwa-split-chart-empty" id="' +
        prefix +
        '-chart-empty" hidden></p>' +
        '<div id="' +
        prefix +
        '-chart" class="aum-chart-host rwa-split-chart-host"></div></div>' +
        colNote +
        "</div></div>" +
        (wideNote.trim()
          ? '<p class="jd-hub-cta-note jd-rwa-gmo-split-note rwa-deep-chart-wide-note">' +
            wideNote +
            "</p>"
          : "");

      var inp = $(prefix + "-q");
      var clr = $(prefix + "-clear");
      var tableWrap = host.querySelector(".rwa-split-table-scroll");
      var tableEl = tableWrap ? tableWrap.querySelector("table") : null;
      var actionRow = null;
      if (attachTableFullscreenButton) {
        actionRow = attachTableFullscreenButton(tableWrap, tableEl, {
          title: String(league.table_heading || league.block_heading || "RWA table"),
        });
      }

      function sync() {
        var q = inp && inp.value !== undefined ? String(inp.value) : "";

        var all = league.rows_full || [];
        var nameCol = league.name_column;
        var filt = filterRows(all, nameCol, q);

        var noteEl = $(prefix + "-note");
        if (noteEl) {
          var tot = all.length;
          var qp = league.filter_note_entity_plural || "";
          var qall = league.filter_note_suffix_all || "";
          if (tot <= 0) noteEl.textContent = "";
          else if (!String(q || "").trim()) {
            if (qp && qall) {
              noteEl.textContent = "Showing all " + filt.length + " " + qall;
            } else {
              noteEl.textContent = "Showing all " + filt.length + " rows.";
            }
          } else if (qp) {
            noteEl.textContent =
              "Showing " +
              filt.length +
              " of " +
              tot +
              " " +
              qp +
              ' matching "' +
              esc(String(q || "").trim()) +
              '".';
          } else {
            noteEl.textContent =
              "Showing " +
              filt.length +
              " of " +
              tot +
              ' rows matching "' +
              esc(String(q || "").trim()) +
              '".';
          }
        }

        var thead = $(prefix + "-thead");
        var tbody = $(prefix + "-tbody");
        renderTable(thead, tbody, league.columns, filt, {
          emptyMsg: "No rows match this filter.",
          linkAria: "Open RWA.xyz",
        });

        var cel = $(prefix + "-chart");
        var emptyEl = $(prefix + "-chart-empty");
        var qpEntity = league.chart_empty_filtered_entity_plural || "rows";

        var noRowsAtAll = all.length === 0;
        var filterExcludesAll =
          q.trim().length > 0 && filt.length === 0 && all.length > 0;

        if (emptyEl) {
          if (noRowsAtAll) {
            emptyEl.textContent = "No rows loaded for this chart.";
            emptyEl.hidden = false;
          } else if (filterExcludesAll) {
            emptyEl.textContent =
              "No " + qpEntity + " match this filter; there is nothing to chart.";
            emptyEl.hidden = false;
          } else {
            emptyEl.textContent = "";
            emptyEl.hidden = true;
          }
        }

        if (noRowsAtAll || filterExcludesAll) {
          if (cel) {
            try {
              Plotly.purge(cel);
            } catch (ePurge) {}
            cel.innerHTML = "";
          }
        } else {
          drawHorizontalBar(cel, filt, league, data);
        }
      }

      if (inp)
        inp.addEventListener("input", function () {
          sync();
        });
      if (clr && inp) {
        clr.addEventListener("click", function () {
          inp.value = "";
          inp.focus();
          sync();
        });
      }

      if (inp) inp.value = "";
      sync();

      /*
      resize observer per chart shell - abbreviated: rely Plotly resize on window optional
       */
      var cel = $(prefix + "-chart");
      var shl = cel && cel.closest ? cel.closest(".rwa-split-chart-shell") : null;
      if (cel && shl && typeof ResizeObserver !== "undefined") {
        cel._rwaRo = new ResizeObserver(function () {
          try {
            Plotly.Plots.resize(cel);
          } catch (eSz) {}
        });
        try {
          cel._rwaRo.observe(shl);
        } catch (eOb) {}
      }
      return { actionRow: actionRow, host: host };
    }

    function applyBottomCta() {
      var bottom = $("js-deep-bottom-cta");
      var bc = payload.bottom_cta || {};
      if (!bottom) return;
      if (bc.href) {
        bottom.hidden = false;
        bottom.innerHTML =
          '<p><a class="btn btn-primary" href="' +
          esc(bc.href) +
          '" target="_blank" rel="noopener noreferrer">' +
          esc(bc.label || "RWA.xyz") +
          "</a></p>";
      } else {
        bottom.innerHTML = "";
        bottom.hidden = true;
      }
    }

    var koSec = $("js-deep-ko-section");

    var ruleKo = $("js-deep-rule-after-ko");

    if (mode === "warn_total" && errMsg) {
      if (banner) {
        banner.hidden = false;
        banner.innerHTML = "";
        banner.textContent = errMsg;
      }
      if (koSec) koSec.hidden = true;
      if (ruleKo) ruleKo.hidden = true;
      setOptionalDeepHtml("js-deep-extra-before-leagues", "");
      setOptionalDeepHtml("js-deep-extra-after-network", "");
      $("deep-net-wrap").hidden = true;
      $("deep-plat-wrap").hidden = true;
      $("js-deep-rule-mid").hidden = true;
      applyBottomCta();
      if (typeof global.finalizeHubAnchors === "function") global.finalizeHubAnchors(document.body);
      return;
    }

    if (mode === "empty_total") {
      if (banner) {
        banner.hidden = false;
        banner.innerHTML =
          '<p class="alert info">' + esc(payload.empty_message || "") + "</p>";
      }
      if (koSec) koSec.hidden = true;
      if (ruleKo) ruleKo.hidden = true;
      setOptionalDeepHtml("js-deep-extra-before-leagues", "");
      setOptionalDeepHtml("js-deep-extra-after-network", "");
      $("deep-net-wrap").hidden = true;
      $("deep-plat-wrap").hidden = true;
      $("js-deep-rule-mid").hidden = true;
      applyBottomCta();
      if (typeof global.finalizeHubAnchors === "function") global.finalizeHubAnchors(document.body);
      return;
    }

    if (banner) {
      banner.hidden = true;
      banner.textContent = "";
      banner.innerHTML = "";
    }

    var hasKo = !!(payload.key_observations_html && String(payload.key_observations_html).trim());
    if (koSec) {
      koSec.hidden = !hasKo;
    }
    if (ruleKo) {
      ruleKo.hidden = !hasKo;
    }
    var koAsOf = $("js-deep-ko-as-of");
    var freshApi = global.__DATA_FRESHNESS;
    if (koAsOf) {
      if (
        hasKo &&
        payload.generated_at &&
        freshApi &&
        typeof freshApi.renderFreshness === "function"
      ) {
        freshApi.renderFreshness(koAsOf, {
          at: payload.generated_at,
          label: payload.key_observations_as_of_label || "Headline KPIs",
          source: "RWA.xyz",
          mode: "snapshot",
        });
      } else {
        koAsOf.hidden = true;
        koAsOf.textContent = "";
      }
    }

    setOptionalDeepHtml("js-deep-extra-before-leagues", payload.between_ko_and_leagues_html);
    var extraBefore = $("js-deep-extra-before-leagues");
    if (extraBefore) {
      var ft = payload.funds_table || null;
      if (ft && ft.columns && ft.columns.length) {
        extraBefore.innerHTML +=
          '<div class="inline-search" role="search">' +
          '<label for="tmmf-funds-q">' +
          esc(ft.search_label || "Search funds table") +
          '</label><input id="tmmf-funds-q" type="search" autocomplete="off" placeholder="' +
          esc(ft.search_placeholder || "Filter funds…") +
          '" /><button type="button" class="btn btn-secondary" id="tmmf-funds-clear">Clear</button></div>' +
          '<p class="toolbar-note" id="tmmf-funds-note"></p>' +
          '<div class="rwa-split-table-scroll"><table class="data-table data-table--dense"><thead><tr id="tmmf-funds-thead"></tr></thead><tbody id="tmmf-funds-tbody"></tbody></table></div>';
        var fInp = $("tmmf-funds-q");
        var fClr = $("tmmf-funds-clear");
        var fThead = $("tmmf-funds-thead");
        var fTbody = $("tmmf-funds-tbody");
        var fNote = $("tmmf-funds-note");
        var fWrap = extraBefore.querySelector(".rwa-split-table-scroll");
        var fTable = fWrap ? fWrap.querySelector("table") : null;
        var allRows = ft.rows_full || [];
        function syncFunds() {
          var q = String((fInp && fInp.value) || "").trim().toLowerCase();
          var filt = !q
            ? allRows.slice()
            : allRows.filter(function (r) {
                return Object.keys(r || {}).some(function (k) {
                  if (k === "Link") return false;
                  var v = r[k];
                  return v != null && String(v).toLowerCase().indexOf(q) >= 0;
                });
              });
          if (fNote) {
            if (!q) fNote.textContent = "Showing all " + filt.length + " funds.";
            else fNote.textContent = "Showing " + filt.length + " of " + allRows.length + ' funds matching "' + q + '".';
          }
          renderTable(fThead, fTbody, ft.columns, filt, { emptyMsg: "No funds match this filter.", linkAria: "Open RWA.xyz asset page" });
        }
        if (fInp) fInp.addEventListener("input", syncFunds);
        if (fClr && fInp)
          fClr.addEventListener("click", function () {
            fInp.value = "";
            fInp.focus();
            syncFunds();
          });
        syncFunds();
        if (attachTableFullscreenButton && fWrap && fTable) {
          var fundsActionRow = attachTableFullscreenButton(fWrap, fTable, { title: "Included funds" });
          if (appendRwaActionLink && fundsActionRow && payload.bottom_cta && payload.bottom_cta.href) {
            appendRwaActionLink(fundsActionRow, {
              href: payload.bottom_cta.href,
              label: payload.bottom_cta.label || "RWA.xyz",
              className: "btn btn-primary",
            });
          }
        }
      }
    }

    var netView = wireLeague(payload.networks || null, "deep-net", payload);

    var hasNet = !!(payload.networks && payload.networks.columns && payload.networks.columns.length);
    var hasPlat = !!(payload.platforms && payload.platforms.columns && payload.platforms.columns.length);

    $("js-deep-rule-mid").hidden = !(hasNet && hasPlat);

    setOptionalDeepHtml("js-deep-extra-after-network", payload.after_network_block_html);

    var platView = wireLeague(payload.platforms || null, "deep-plat", payload);

    var ctaTargetRow = (platView && platView.actionRow) || (netView && netView.actionRow) || null;
    if (appendRwaActionLink && ctaTargetRow && payload.bottom_cta && payload.bottom_cta.href) {
      appendRwaActionLink(ctaTargetRow, {
        href: payload.bottom_cta.href,
        label: payload.bottom_cta.label || "RWA.xyz",
        className: "btn btn-primary",
      });
      $("js-deep-bottom-cta").hidden = true;
      $("js-deep-bottom-cta").innerHTML = "";
    } else {
      applyBottomCta();
    }

    if (payload.back_href) {
      document.querySelectorAll('a[data-deep-back="explore"]').forEach(function (a) {
        a.setAttribute("href", assetPath(payload.back_href));
      });
    }

    var foot = $("js-deep-footer-note");
    if (foot) foot.textContent = payload.footer_note || "";

    if (typeof global.finalizeHubAnchors === "function") {
      global.finalizeHubAnchors(document.body);
    }
  }

  function boot() {
    var name = document.body.getAttribute("data-rwa-deep-json");
    if (!name) return;
    global
      .loadJson(name)
      .then(renderDeepPage)
      .catch(function (e) {
        var b = $("js-deep-banner");
        if (b) {
          b.hidden = false;
          b.textContent =
            (e && e.message) || "Could not load " + name + ".";
        }
      });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})(typeof window !== "undefined" ? window : this);
