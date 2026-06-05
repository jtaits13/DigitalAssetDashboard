/**
 * Static hub: render the On-chain block (Global Market KPIs + Networks preview + Explore gateways).
 * Data from static_home/data/rwa_onchain_home.json (export_static_site_data.py).
 */
(function (global) {
  function fmtUsdCompact(n) {
    if (n == null || !isFinite(Number(n))) return "—";
    var x = Number(n);
    if (x >= 1e12) return "$" + (x / 1e12).toFixed(2) + "T";
    if (x >= 1e9) return "$" + (x / 1e9).toFixed(2) + "B";
    if (x >= 1e6) return "$" + (x / 1e6).toFixed(2) + "M";
    if (x >= 1e3) return "$" + (x / 1e3).toFixed(2) + "K";
    return "$" + x.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }

  function fmtPctPts(v, digits) {
    if (v == null || !isFinite(Number(v))) return "—";
    var x = Number(v);
    var sign = x > 0 ? "+" : "";
    return sign + x.toFixed(digits != null ? digits : 2) + "%";
  }

  /** Level / ratio as percent (no leading +), for **% distributed** vs signed deltas (7D, share changes). */
  function fmtPctLevel(v, digits) {
    if (v == null || !isFinite(Number(v))) return "—";
    return Number(v).toFixed(digits != null ? digits : 2) + "%";
  }

  function pctCellCls(v) {
    if (v == null || !isFinite(Number(v))) return "";
    var x = Number(v);
    if (x > 0) return " up";
    if (x < 0) return " down";
    return "";
  }

  var PARTICIPANT_KPI_MAX = 5;
  var KPI_DROP_STABLECOIN_HOLDERS = "Total Stablecoin Holders";

  function delta30Html(frac) {
    if (frac == null || !isFinite(Number(frac))) {
      return '<span class="rwa-kpi-delta rwa-kpi-delta--placeholder" aria-hidden="true">&nbsp;</span>';
    }
    var pct = Number(frac) * 100;
    var cls = pct > 0 ? "up" : pct < 0 ? "down" : "neutral";
    var sign = pct > 0 ? "+" : "";
    return '<span class="rwa-kpi-delta ' + cls + '">' + sign + pct.toFixed(2) + "%</span>";
  }

  function normalizeKpisForDisplay(kpis, kpiOpts) {
    var opts = kpiOpts || {};
    var list = (kpis || []).slice();
    if (opts.dropStablecoinHolders) {
      list = list.filter(function (k) {
        return String(k && k.label != null ? k.label : "") !== KPI_DROP_STABLECOIN_HOLDERS;
      });
    }
    var maxN = opts.maxKpis != null ? Number(opts.maxKpis) : opts.participantKpis ? PARTICIPANT_KPI_MAX : 0;
    if (maxN > 0) list = list.slice(0, maxN);
    return list;
  }

  function kpiRenderOptsFromPage(kpiOpts) {
    var opts = Object.assign({}, kpiOpts || {});
    if (typeof document === "undefined" || !document.body) return opts;
    var body = document.body;
    if (body.classList.contains("page-rwa-explore-mp")) {
      opts.participantKpis = true;
    }
    if (body.classList.contains("page-rwa-deep-participants-networks")) {
      opts.participantKpis = true;
      opts.dropStablecoinHolders = true;
    }
    if (body.classList.contains("page-rwa-deep-participants-platforms")) {
      opts.participantKpis = true;
      opts.dropStablecoinHolders = true;
    }
    if (body.classList.contains("page-rwa-deep-participants-am")) {
      opts.participantKpis = true;
    }
    return opts;
  }

  function esc(s) {
    var fn = global.escapeHtml;
    return typeof fn === "function" ? fn(String(s == null ? "" : s)) : String(s == null ? "" : s);
  }

  /** Column keys whose raw JSON values sort numerically (all RWA / export table shapes). */
  var RWA_NUMERIC_SORT = {
    "#": 1,
    "RWA Count": 1,
    Stablecoins: 1,
    "Total Value": 1,
    "Distributed Value": 1,
    "RWA value (distributed)": 1,
    "RWA value (represented)": 1,
    "RWA total (excl. stablecoins)": 1,
    "7D Δ value": 1,
    "% distributed": 1,
    "Market Share": 1,
    "30D Δ share": 1,
  };

  function isRwaTextColumn(col) {
    return (
      col === "Network" ||
      col === "Platform" ||
      col === "Asset manager" ||
      col === "Fund Name" ||
      col === "Networks" ||
      col === "Ticker" ||
      col === "Eligible Investors" ||
      col === "Domicile" ||
      col === "Regulatory Framework" ||
      col === "Custodian" ||
      col === "Terms"
    );
  }

  function compareRwaRows(a, b, col, dir) {
    var va = a[col];
    var vb = b[col];
    if (RWA_NUMERIC_SORT[col]) {
      var na = va == null || va === "" ? NaN : Number(va);
      var nb = vb == null || vb === "" ? NaN : Number(vb);
      var aBad = !isFinite(na);
      var bBad = !isFinite(nb);
      if (aBad && bBad) return 0;
      if (aBad) return 1;
      if (bBad) return -1;
      return dir * (na - nb);
    }
    var sa = va == null ? "" : String(va);
    var sb = vb == null ? "" : String(vb);
    if (!sa && !sb) return 0;
    if (!sa) return 1;
    if (!sb) return -1;
    return dir * sa.localeCompare(sb, undefined, { sensitivity: "base" });
  }

  function clearTheadSortClasses(theadRow) {
    if (!theadRow) return;
    theadRow.querySelectorAll("th").forEach(function (th) {
      th.classList.remove("is-sorted", "is-sorted-asc", "is-sorted-desc");
      th.removeAttribute("aria-sort");
    });
  }

  function setTheadSortClasses(theadRow, colIndex, dir) {
    clearTheadSortClasses(theadRow);
    var ths = theadRow.querySelectorAll("th");
    var th = ths[colIndex];
    if (!th) return;
    th.classList.add("is-sorted", dir > 0 ? "is-sorted-asc" : "is-sorted-desc");
    th.setAttribute("aria-sort", dir > 0 ? "ascending" : "descending");
  }

  function fillRwaTableBody(tbody, columns, rows, opts) {
    var emptyMsg = opts.emptyMsg;
    var linkAria = opts.linkAria || "Open link";
    tbody.innerHTML = "";
    if (!rows || !rows.length) {
      var colspan = columns && columns.length ? columns.length : 1;
      tbody.innerHTML =
        '<tr><td colspan="' +
        colspan +
        '">' +
        esc(emptyMsg || "No preview rows are available.") +
        "</td></tr>";
      return;
    }
    rows.forEach(function (row) {
      var tr = document.createElement("tr");
      var tds = [];
      (columns || []).forEach(function (col) {
        var v = row[col];
        if (col === "Network" || col === "Platform" || col === "Asset manager" || col === "Fund Name") {
          var hrefRaw =
            col === "Fund Name"
              ? row["Fund Link"] || row.Link
              : col === "Platform"
                ? row["Platform Link"] || row.Link
                : row.Link;
          var href = hrefRaw ? esc(hrefRaw) : "";
          if (href) {
            tds.push(
              '<td><a class="sym sym--link" href="' +
                href +
                '" target="_blank" rel="noopener noreferrer">' +
                esc(v) +
                "</a></td>"
            );
          } else {
            tds.push("<td><span class=\"sym\">" + esc(v) + "</span></td>");
          }
        } else if (col === "Link") {
          var h = v ? esc(v) : "#";
          tds.push(
            '<td class="num"><a class="rwa-table-link" href="' +
              h +
              '" target="_blank" rel="noopener noreferrer" aria-label="' +
              esc(linkAria) +
              '">↗</a></td>'
          );
        } else if (
          col === "Total Value" ||
          col === "Distributed Value" ||
          col === "RWA value (distributed)" ||
          col === "RWA value (represented)" ||
          col === "RWA total (excl. stablecoins)"
        ) {
          tds.push('<td class="num">' + fmtUsdCompact(v) + "</td>");
        } else if (col === "7D Δ value") {
          tds.push('<td class="num' + pctCellCls(v) + '">' + fmtPctPts(v, 2) + "</td>");
        } else if (col === "% distributed") {
          tds.push('<td class="num">' + fmtPctLevel(v, 2) + "</td>");
        } else if (col === "Market Share") {
          tds.push('<td class="num">' + fmtPctLevel(v, 2) + "</td>");
        } else if (col === "30D Δ share") {
          tds.push('<td class="num' + pctCellCls(v) + '">' + fmtPctPts(v, 2) + "</td>");
        } else if (col === "Terms" || col === "Networks") {
          tds.push('<td class="data-table__text">' + (v != null ? String(v) : "—") + "</td>");
        } else if (col === "Holders") {
          tds.push(
            '<td class="num">' +
              (v != null && isFinite(Number(v))
                ? esc(Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 }))
                : "—") +
              "</td>"
          );
        } else if (col === "#" || col === "RWA Count" || col === "Stablecoins") {
          tds.push('<td class="num">' + (v != null ? esc(String(v)) : "—") + "</td>");
        } else {
          tds.push("<td>" + (v != null ? esc(String(v)) : "—") + "</td>");
        }
      });
      tr.innerHTML = tds.join("");
      tbody.appendChild(tr);
    });
  }

  var HOME_RWA_PREVIEW_LIMIT = 5;

  function filterRwaHomeRows(rows, q) {
    if (!q) return rows;
    q = q.trim().toLowerCase();
    return rows.filter(function (row) {
      if (row.Network && String(row.Network).toLowerCase().indexOf(q) >= 0) return true;
      return Object.keys(row).some(function (k) {
        if (k === "Link") return false;
        var v = row[k];
        return v != null && String(v).toLowerCase().indexOf(q) >= 0;
      });
    });
  }

  function sortRwaHomeRows(rows, columns, sortCol, sortDir) {
    if (sortCol == null || sortCol < 0 || !columns || !columns[sortCol]) {
      return rows.slice().sort(function (a, b) {
        return (Number(a["#"]) || 9999) - (Number(b["#"]) || 9999);
      });
    }
    var colName = columns[sortCol];
    return rows.slice().sort(function (a, b) {
      return compareRwaRows(a, b, colName, sortDir);
    });
  }

  function updateHomeRwaToolbar(hp, filteredCount, q, displayCount) {
    if (!hp.toolbarEl) return;
    var total = hp.allRows.length;
    if (!total) {
      hp.toolbarEl.hidden = true;
      return;
    }
    hp.toolbarEl.hidden = false;
    var shown = displayCount != null ? displayCount : Math.min(filteredCount, hp.limit);
    var entity = hp.previewEntity || "networks";
    if (hp.previewScope === "explore") {
      if (q) {
        hp.toolbarEl.textContent =
          "Showing " +
          shown +
          " of " +
          total +
          " " +
          entity +
          ' matching "' +
          String(q).trim() +
          '".';
      } else {
        hp.toolbarEl.textContent =
          "Preview: " +
          shown +
          " of " +
          total +
          " " +
          entity +
          ". Search to filter the full list.";
      }
      return;
    }
    if (q) {
      hp.toolbarEl.innerHTML =
        "Showing top " +
        hp.limit +
        " of <strong>" +
        filteredCount +
        "</strong> matching " +
        entity +
        " (of <strong>" +
        total +
        "</strong> listed).";
    } else {
      hp.toolbarEl.innerHTML =
        "Preview: top <strong>" +
        hp.limit +
        "</strong> by rank (of <strong>" +
        total +
        "</strong> listed).";
    }
  }

  function refreshHomeRwaPreview(theadRow, tbody) {
    var hp = tbody._rwaHomePreview;
    if (!hp) return;
    var st = tbody._rwaTableSort;
    var q = hp.searchEl && hp.searchEl.value ? hp.searchEl.value.trim() : "";
    var filtered = filterRwaHomeRows(hp.allRows, q);
    var sortCol = st ? st.sortCol : null;
    var sortDir = st ? st.sortDir : 1;
    var sorted = sortRwaHomeRows(filtered, hp.columns, sortCol, sortDir);
    var previewCap =
      hp.previewLimit != null && hp.previewLimit > 0
        ? hp.previewLimit
        : hp.limit != null && hp.limit > 0
          ? hp.limit
          : null;
    var cap;
    if (hp.previewScope === "explore") {
      cap = q ? sorted.length : previewCap != null ? previewCap : sorted.length;
    } else {
      cap = hp.limit != null && hp.limit > 0 ? hp.limit : sorted.length;
    }
    var display = sorted.slice(0, cap);
    var entity = hp.previewEntity || "networks";
    var emptyMsg = q
      ? "No " + entity + " match your filter. Try another name."
      : hp.opts.emptyMsg || "No preview rows are available.";
    if (!display.length) {
      fillRwaTableBody(tbody, hp.columns, [], { emptyMsg: emptyMsg });
    } else {
      fillRwaTableBody(tbody, hp.columns, display, hp.opts);
    }
    updateHomeRwaToolbar(hp, filtered.length, q, display.length);
  }

  function applyRwaTableSort(theadRow, tbody, colIndex) {
    var st = tbody._rwaTableSort;
    if (!st || !st.columns) return;
    if (colIndex < 0 || colIndex >= st.columns.length) return;
    if (st.sortCol === colIndex) {
      st.sortDir *= -1;
    } else {
      st.sortCol = colIndex;
      st.sortDir = 1;
    }
    setTheadSortClasses(theadRow, colIndex, st.sortDir);
    if (tbody._rwaHomePreview) {
      refreshHomeRwaPreview(theadRow, tbody);
      return;
    }
    if (!st.rows || !st.rows.length) return;
    var colName = st.columns[colIndex];
    var dir = st.sortDir;
    st.rows = st.rows.slice().sort(function (a, b) {
      return compareRwaRows(a, b, colName, dir);
    });
    fillRwaTableBody(tbody, st.columns, st.rows, st.opts);
  }

  function wireRwaTableSortDelegate(theadRow, tbody) {
    var thead = theadRow && theadRow.parentNode;
    if (!thead || thead._rwaSortDelegated) return;
    thead._rwaSortDelegated = true;
    thead.addEventListener("click", function (ev) {
      var th = ev.target.closest("th.th-sortable");
      if (!th) return;
      var idx = parseInt(th.getAttribute("data-sort-col"), 10);
      if (isNaN(idx)) return;
      applyRwaTableSort(theadRow, tbody, idx);
    });
    thead.addEventListener("keydown", function (ev) {
      if (ev.key !== "Enter" && ev.key !== " ") return;
      var th = ev.target.closest && ev.target.closest("th.th-sortable");
      if (!th) return;
      ev.preventDefault();
      var idx = parseInt(th.getAttribute("data-sort-col"), 10);
      if (!isNaN(idx)) applyRwaTableSort(theadRow, tbody, idx);
    });
  }

  function renderKeyObservationsCallout(host, html, options) {
    if (!host) return false;
    var raw = html == null ? "" : String(html);
    if (!raw.trim()) {
      host.innerHTML = "";
      return false;
    }
    var title = (options && options.title) || "Key observations";
    var temp = document.createElement("div");
    temp.innerHTML = raw;
    temp.querySelectorAll("style").forEach(function (node) {
      node.remove();
    });
    var ul = temp.querySelector("ul");
    if (!ul) {
      host.innerHTML = raw;
      return true;
    }
    var listHtml = ul.innerHTML;
    var noteEl = temp.querySelector(
      ".takeaways__note, .etp-takeaway-note, .rwa-gmo-takeaway-note"
    );
    var reviewEl = temp.querySelector(".review-note");
    var noteHtml = "";
    if (noteEl) {
      noteHtml =
        '<p class="crypto-story-callout__note">' + noteEl.innerHTML + "</p>";
    }
    host.innerHTML =
      '<aside class="crypto-story-callout" aria-labelledby="key-obs-callout-title">' +
      '<h3 class="crypto-story-callout__title" id="key-obs-callout-title">' +
      esc(title) +
      "</h3>" +
      '<ul class="crypto-story-callout__list">' +
      listHtml +
      "</ul>" +
      (noteHtml || "") +
      "</aside>";
    if (reviewEl) {
      host.insertAdjacentHTML("beforeend", reviewEl.outerHTML);
    }
    return true;
  }

  function renderKpis(host, kpis, legendText, kpiOpts) {
    var ko = kpiRenderOptsFromPage(kpiOpts);
    kpis = normalizeKpisForDisplay(kpis, ko);
    if (!host) return;
    if (!kpis || !kpis.length) {
      if (ko.hideIfEmpty) {
        host.innerHTML = "";
        host.style.display = "none";
        return;
      }
      host.innerHTML = '<p class="toolbar-note">No headline KPIs returned for this block.</p>';
      return;
    }
    host.style.display = "";
    var cells = kpis
      .map(function (k) {
        var labelHtml =
          global.__KPI_HINTS && typeof global.__KPI_HINTS.wrapKpiLabel === "function"
            ? global.__KPI_HINTS.wrapKpiLabel(k.label, k.hint)
            : esc(k.label);
        return (
          '<div class="rwa-kpi-cell">' +
          '<span class="rwa-kpi-label">' +
          labelHtml +
          "</span>" +
          '<span class="rwa-kpi-val">' +
          esc(k.value_display) +
          "</span>" +
          delta30Html(k.delta_30d_pct) +
          "</div>"
        );
      })
      .join("");
    host.innerHTML =
      '<div class="rwa-kpi-panel-static">' +
      (legendText
        ? '<p class="jd-kpi-window-note rwa-onchain-kpi-legend">' + esc(legendText) + "</p>"
        : "") +
      '<div class="rwa-kpi-row rwa-kpi-row--home-grid">' +
      cells +
      "</div></div>";
    if (global.__KPI_HINTS && typeof global.__KPI_HINTS.bindKpiHints === "function") {
      global.__KPI_HINTS.bindKpiHints(host);
    }
  }

  function renderTable(theadRow, tbody, columns, rows, tableOpts) {
    var opts = typeof tableOpts === "string" ? { emptyMsg: tableOpts } : tableOpts || {};
    if (!theadRow || !tbody) return;
    if (!columns || !columns.length) {
      theadRow.innerHTML = "";
      tbody.innerHTML =
        '<tr><td colspan="1">On-chain data is unavailable.</td></tr>';
      tbody._rwaTableSort = null;
      return;
    }
    theadRow.innerHTML = (columns || [])
      .map(function (c, idx) {
        var label = c === "Link" ? "↗" : esc(c);
        var isName = isRwaTextColumn(c);
        var cls = [];
        if (!(isName || c === "Link")) cls.push("num");
        cls.push("th-sortable");
        return (
          '<th scope="col" class="' +
          cls.join(" ") +
          '" data-sort-col="' +
          idx +
          '" tabindex="0">' +
          label +
          "</th>"
        );
      })
      .join("");
    clearTheadSortClasses(theadRow);
    var rowsCopy = rows && rows.length ? rows.slice() : [];
    tbody._rwaTableSort = {
      rows: rowsCopy,
      columns: columns.slice(),
      opts: opts,
      sortCol: null,
      sortDir: 1,
    };
    if (opts.homePreview) {
      var searchEl = opts.searchEl || null;
      if (!searchEl && opts.searchInputId && typeof document !== "undefined") {
        searchEl = document.getElementById(opts.searchInputId);
      }
      var toolbarEl = opts.toolbarEl || null;
      if (!toolbarEl && opts.toolbarId && typeof document !== "undefined") {
        toolbarEl = document.getElementById(opts.toolbarId);
      }
      var previewCap =
        opts.previewLimit != null ? opts.previewLimit : HOME_RWA_PREVIEW_LIMIT;
      tbody._rwaHomePreview = {
        allRows: rowsCopy,
        columns: columns.slice(),
        opts: opts,
        limit: previewCap,
        previewLimit: previewCap,
        searchEl: searchEl,
        toolbarEl: toolbarEl,
        previewScope: opts.previewScope || "home",
        previewEntity: opts.previewEntity || "networks",
      };
      if (searchEl) {
        if (!searchEl._rwaHomeSearchBound) {
          searchEl._rwaHomeSearchBound = true;
          searchEl.addEventListener("input", function () {
            refreshHomeRwaPreview(theadRow, tbody);
          });
        }
        searchEl._rwaHomePreviewTbody = tbody;
      }
      refreshHomeRwaPreview(theadRow, tbody);
    } else {
      fillRwaTableBody(tbody, columns, rowsCopy, opts);
    }
    wireRwaTableSortDelegate(theadRow, tbody);
  }

  function exploreCompactHtml(links) {
    var L = links || {};
    var at = L.explore_asset_type || "rwa-explore-asset-type.html";
    var mp = L.explore_market_participant || "rwa-explore-market-participant.html";
    return (
      '<nav class="home-explore-compact" aria-label="Explore RWA">' +
      '<span class="home-explore-compact__label">Explore</span>' +
      '<a class="home-explore-compact__btn" href="' +
      esc(at) +
      '">By asset type</a>' +
      '<a class="home-explore-compact__btn" href="' +
      esc(mp) +
      '">By participant</a>' +
      "</nav>"
    );
  }

  function exploreSplitHtml(links) {
    var L = links || {};
    var at = L.explore_asset_type || "rwa-explore-asset-type.html";
    var mp = L.explore_market_participant || "rwa-explore-market-participant.html";
    var card = function (title, items, href) {
      return (
        '<article class="jd-hub-explore-card-static">' +
        '<p class="jd-hub-explore-eyebrow">On-chain</p>' +
        "<h4>" +
        esc(title) +
        "</h4>" +
        '<div class="jd-hub-explore-blurb">' +
        "<p>View on-chain RWA data for:</p>" +
        "<ul>" +
        items.map(function (x) {
          return "<li>" + esc(x) + "</li>";
        }).join("") +
        "</ul>" +
        '<p class="jd-hub-explore-blurb-tail">Use <strong>Explore</strong> to open the hub and go deeper on the next pages.</p>' +
        "</div>" +
        '<a class="btn btn-primary" href="' +
        esc(href) +
        '">Explore</a>' +
        "</article>"
      );
    };
    return (
      '<div class="onchain-explore-split">' +
      card("Explore by Asset Type", ["US Treasuries", "Tokenized Stocks"], at) +
      card("Explore by Market Participant", ["Networks", "Platforms", "Asset Managers"], mp) +
      "</div>"
    );
  }

  function buildPreviewTableExportData(tbody, options) {
    var opts = options || {};
    var hp = tbody && tbody._rwaHomePreview;
    if (!hp || !hp.allRows || !hp.allRows.length) return null;
    var sortState = tbody._rwaTableSort || {};
    var sorted = sortRwaHomeRows(
      hp.allRows.slice(),
      hp.columns,
      sortState.sortCol,
      sortState.sortDir != null ? sortState.sortDir : 1
    );
    var cols = (opts.exportColumns || hp.columns || []).filter(function (c) {
      return c !== "Link";
    });
    return {
      headers: cols,
      sheetName: opts.sheetName,
      rows: sorted.map(function (row) {
        return cols.map(function (c) {
          var v = row[c];
          return v == null ? "" : v;
        });
      }),
    };
  }

  function attachHomePreviewFullscreen(tbody, options) {
    var fs = global.__TABLE_FULLSCREEN;
    if (!fs || !fs.attachTableFullscreenButton || !tbody) return;
    var wrap = tbody.closest ? tbody.closest(".table-wrap") : null;
    var table = wrap ? wrap.querySelector("table") : null;
    if (!wrap || !table) return;
    var opts = options || {};
    fs.attachTableFullscreenButton(wrap, table, {
      title: opts.title || "RWA table preview",
      filename: opts.filename || "rwa-preview",
      getExportData: function () {
        return buildPreviewTableExportData(tbody, {
          exportColumns: opts.exportColumns,
          sheetName: opts.sheetName,
        });
      },
    });
  }

  function renderRwaOnchainHome(data) {
    if (!data) return;
    var isHome =
      typeof document !== "undefined" &&
      document.body &&
      document.body.classList.contains("page-home");
    var banner = document.getElementById("js-rwa-onchain-banner");
    var kpiHost = document.getElementById("js-rwa-kpi-host");
    var theadRow = document.getElementById("js-rwa-thead-row");
    var tbody = document.getElementById("js-rwa-tbody");
    var openFull = document.getElementById("js-rwa-open-full");
    var seeNetworks = document.getElementById("js-rwa-see-networks");
    var captionEl = document.getElementById("js-rwa-caption");
    var exploreHost = document.getElementById("js-rwa-explore-split");

    if (banner) {
      if (data.error && String(data.error).trim()) {
        banner.hidden = false;
        banner.textContent = data.error;
      } else {
        banner.hidden = true;
        banner.textContent = "";
      }
    }

    renderKpis(
      kpiHost,
      data.kpis || [],
      ""
    );

    renderTable(theadRow, tbody, data.columns || [], data.rows || [], {
      emptyMsg: "On-chain data is unavailable.",
      homePreview: true,
      previewLimit: HOME_RWA_PREVIEW_LIMIT,
      searchInputId: "js-home-rwa-search",
      toolbarId: "js-home-rwa-toolbar",
    });
    attachHomePreviewFullscreen(tbody, {
      title: "RWA Global Market Overview networks table",
      filename: "rwa-networks-preview",
    });

    var links = data.links || {};
    if (openFull) {
      var rawOpen = (links.open_full_overview || "rwa-global.html").trim();
      // FastAPI route — not deployed on GitHub Pages; older exports used ``/rwa/global``.
      var low = rawOpen.split("?")[0].toLowerCase();
      if (low === "/rwa/global" || low.indexOf("/rwa/global") === 0) rawOpen = "rwa-global.html";
      var au =
        global.__STATIC && typeof global.__STATIC.assetUrl === "function"
          ? global.__STATIC.assetUrl(rawOpen)
          : rawOpen;
      openFull.setAttribute("href", au);
    }
    if (seeNetworks && links.see_networks_on_rwa_xyz) seeNetworks.setAttribute("href", links.see_networks_on_rwa_xyz);

    if (captionEl) captionEl.textContent = data.caption || "";

    if (exploreHost && !exploreHost.classList.contains("home-explore-compact")) {
      exploreHost.innerHTML = exploreSplitHtml(links);
      if (typeof global.finalizeHubAnchors === "function") {
        global.finalizeHubAnchors(exploreHost);
      }
    }
  }

  global.renderRwaOnchainHome = renderRwaOnchainHome;

  /** Shared KPI/table formatters for ``rwa-global-page.js``. */
  global.__RWA_STATIC_HELPERS = Object.assign(global.__RWA_STATIC_HELPERS || {}, {
    renderKeyObservationsCallout: renderKeyObservationsCallout,
    renderKpis: renderKpis,
    renderTable: renderTable,
    attachHomePreviewFullscreen: attachHomePreviewFullscreen,
    buildPreviewTableExportData: buildPreviewTableExportData,
    exploreCompactHtml: exploreCompactHtml,
  });
})(typeof window !== "undefined" ? window : this);
