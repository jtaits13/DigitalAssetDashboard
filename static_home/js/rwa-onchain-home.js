/**
 * Static hub: mirror Streamlit On-chain block (Global Market KPIs + Networks preview + Explore gateways).
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
    if (x > 0) return " pct up";
    if (x < 0) return " pct down";
    return "";
  }

  function delta30Html(frac) {
    if (frac == null || !isFinite(Number(frac))) return "";
    var pct = Number(frac) * 100;
    var cls = pct > 0 ? "up" : pct < 0 ? "down" : "neutral";
    var sign = pct > 0 ? "+" : "";
    return '<span class="rwa-kpi-delta ' + cls + '">' + sign + pct.toFixed(2) + "%</span>";
  }

  function esc(s) {
    var fn = global.escapeHtml;
    return typeof fn === "function" ? fn(String(s == null ? "" : s)) : String(s == null ? "" : s);
  }

  function renderKpis(host, kpis, legendText, kpiOpts) {
    var ko = kpiOpts || {};
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
        return (
          '<div class="rwa-kpi-cell">' +
          '<span class="rwa-kpi-label">' +
          esc(k.label) +
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
  }

  function renderTable(theadRow, tbody, columns, rows, tableOpts) {
    var opts = typeof tableOpts === "string" ? { emptyMsg: tableOpts } : tableOpts || {};
    var emptyMsg = opts.emptyMsg;
    var linkAria = opts.linkAria || "Open link";
    if (!theadRow || !tbody) return;
    if (!columns || !columns.length) {
      theadRow.innerHTML = "";
      tbody.innerHTML =
        '<tr><td colspan="1">On-chain JSON missing or export not run. Run <code>python scripts/export_static_site_data.py</code> to populate <code>data/rwa_onchain_home.json</code>.</td></tr>';
      return;
    }
    theadRow.innerHTML = (columns || [])
      .map(function (c) {
        var label = c === "Link" ? "↗" : esc(c);
        var isName = c === "Network" || c === "Platform" || c === "Asset manager";
        return "<th" + (isName || c === "Link" ? "" : ' class="num"') + ">" + label + "</th>";
      })
      .join("");
    tbody.innerHTML = "";
    if (!rows || !rows.length) {
      var colspan = columns && columns.length ? columns.length : 1;
      tbody.innerHTML =
        '<tr><td colspan="' +
        colspan +
        '">' +
        esc(emptyMsg || "No preview rows. Run export or check RWA fetch.") +
        "</td></tr>";
      return;
    }
    rows.forEach(function (row) {
      var tr = document.createElement("tr");
      var tds = [];
      (columns || []).forEach(function (col) {
        var v = row[col];
        if (col === "Network" || col === "Platform" || col === "Asset manager") {
          var href = row.Link ? esc(row.Link) : "#";
          tds.push(
            "<td><strong><a href=\"" +
              href +
              "\" target=\"_blank\" rel=\"noopener noreferrer\">" +
              esc(v) +
              "</a></strong></td>"
          );
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
        } else if (col === "Market Share" || col === "30D Δ share") {
          tds.push('<td class="num">' + fmtPctPts(v, 2) + "</td>");
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
      card("Explore by Asset Type", ["Stablecoins", "US Treasuries", "Tokenized Stocks"], at) +
      card("Explore by Market Participant", ["Networks", "Platforms", "Asset Managers"], mp) +
      "</div>"
    );
  }

  function renderRwaOnchainHome(data) {
    if (!data) return;
    var banner = document.getElementById("js-rwa-onchain-banner");
    var kpiHost = document.getElementById("js-rwa-kpi-host");
    var noteEl = document.getElementById("js-rwa-preview-note");
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

    renderKpis(kpiHost, data.kpis || [], data.kpi_window_note || "");

    if (noteEl) {
      var total = data.total_networks != null ? data.total_networks : 0;
      var shown = data.preview_count != null ? data.preview_count : 0;
      if (total > 0) {
        noteEl.textContent = "Showing " + shown + " of " + total + " networks from the homepage Global Market Overview table.";
      } else {
        noteEl.textContent = "";
      }
    }

    renderTable(theadRow, tbody, data.columns || [], data.rows || []);

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

    if (exploreHost) {
      exploreHost.innerHTML = exploreSplitHtml(links);
      if (typeof global.finalizeHubAnchors === "function") {
        global.finalizeHubAnchors(exploreHost);
      }
    }
  }

  global.renderRwaOnchainHome = renderRwaOnchainHome;

  /** Shared KPI/table formatters for ``rwa-global-page.js``. */
  global.__RWA_STATIC_HELPERS = {
    renderKpis: renderKpis,
    renderTable: renderTable,
  };
})(typeof window !== "undefined" ? window : this);
