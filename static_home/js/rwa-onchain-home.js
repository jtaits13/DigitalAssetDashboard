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

  function applyRwaTableSort(theadRow, tbody, colIndex) {
    var st = tbody._rwaTableSort;
    if (!st || !st.rows || !st.rows.length || !st.columns) return;
    if (colIndex < 0 || colIndex >= st.columns.length) return;
    var colName = st.columns[colIndex];
    if (st.sortCol === colIndex) {
      st.sortDir *= -1;
    } else {
      st.sortCol = colIndex;
      st.sortDir = 1;
    }
    var dir = st.sortDir;
    st.rows = st.rows.slice().sort(function (a, b) {
      return compareRwaRows(a, b, colName, dir);
    });
    setTheadSortClasses(theadRow, colIndex, dir);
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

  function stripElementIds(node) {
    if (!node || node.nodeType !== 1) return;
    node.removeAttribute("id");
    Array.prototype.forEach.call(node.children || [], stripElementIds);
  }

  function closeRwaTableModal() {
    var root = document.getElementById("js-rwa-table-modal");
    if (!root) return;
    root.hidden = true;
    document.body.classList.remove("rwa-table-modal-open");
    var body = document.getElementById("js-rwa-table-modal-body");
    if (body) body.innerHTML = "";
  }

  function ensureRwaTableModal() {
    var root = document.getElementById("js-rwa-table-modal");
    if (root) return root;

    root = document.createElement("div");
    root.id = "js-rwa-table-modal";
    root.className = "rwa-table-modal";
    root.hidden = true;
    root.innerHTML =
      '<div class="rwa-table-modal__backdrop" data-rwa-table-modal-close="1"></div>' +
      '<div class="rwa-table-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="js-rwa-table-modal-title">' +
      '<div class="rwa-table-modal__header">' +
      '<div>' +
      '<p class="rwa-table-modal__eyebrow">Full-screen table</p>' +
      '<h2 class="rwa-table-modal__title" id="js-rwa-table-modal-title">Table</h2>' +
      "</div>" +
      '<button type="button" class="btn btn-secondary rwa-table-modal__close" data-rwa-table-modal-close="1">Close</button>' +
      "</div>" +
      '<div class="rwa-table-modal__body" id="js-rwa-table-modal-body"></div>' +
      "</div>";
    document.body.appendChild(root);

    root.addEventListener("click", function (ev) {
      var closeEl = ev.target.closest ? ev.target.closest("[data-rwa-table-modal-close]") : null;
      if (closeEl) closeRwaTableModal();
    });

    if (!document.body._rwaTableModalKeyBound) {
      document.body._rwaTableModalKeyBound = true;
      document.addEventListener("keydown", function (ev) {
        if (ev.key === "Escape") closeRwaTableModal();
      });
    }

    return root;
  }

  function openRwaTableModal(tableEl, opts) {
    if (!tableEl) return;
    var root = ensureRwaTableModal();
    var titleEl = document.getElementById("js-rwa-table-modal-title");
    var body = document.getElementById("js-rwa-table-modal-body");
    if (!root || !titleEl || !body) return;

    titleEl.textContent =
      (opts && opts.title ? String(opts.title) : "") || "Full-screen table";
    body.innerHTML = "";

    var wrap = document.createElement("div");
    wrap.className = "rwa-table-modal__table-wrap";

    var clone = tableEl.cloneNode(true);
    stripElementIds(clone);
    wrap.appendChild(clone);
    body.appendChild(wrap);

    root.hidden = false;
    document.body.classList.add("rwa-table-modal-open");

    var closeBtn = root.querySelector(".rwa-table-modal__close");
    if (closeBtn) closeBtn.focus();
  }

  function createRwaActionButton(cfg) {
    var btn = document.createElement(cfg.tagName === "button" ? "button" : "a");
    btn.className = cfg.className || "btn btn-secondary";
    btn.textContent = cfg.label || "Open";
    if (btn.tagName === "BUTTON") {
      btn.type = "button";
    } else {
      btn.href = cfg.href || "#";
      if (cfg.external) {
        btn.target = "_blank";
        btn.rel = "noopener noreferrer";
      }
    }
    return btn;
  }

  function ensureRwaActionRow(tableWrap, opts) {
    var row = opts && opts.actionRow ? opts.actionRow : null;
    if (!row && tableWrap) {
      var next = tableWrap.nextElementSibling;
      if (next && next.classList && next.classList.contains("rwa-table-actions")) {
        row = next;
      }
    }
    if (!row && tableWrap) {
      row = document.createElement("div");
      row.className = "cta-row rwa-table-actions";
      tableWrap.insertAdjacentElement("afterend", row);
    }
    if (row && row.classList) {
      row.classList.add("rwa-table-actions");
    }
    return row;
  }

  function appendRwaActionLink(row, cfg) {
    if (!row || !cfg || !cfg.href) return null;
    var key = String(cfg.href).trim() + "::" + String(cfg.label || "").trim();
    var existing = null;
    Array.prototype.forEach.call(row.children || [], function (child) {
      if (!existing && child.getAttribute && child.getAttribute("data-rwa-action-key") === key) {
        existing = child;
      }
    });
    if (existing) return existing;
    var btn = createRwaActionButton({
      className: cfg.className || "btn btn-primary",
      label: cfg.label || "RWA.xyz",
      href: cfg.href,
      external: cfg.external !== false,
    });
    btn.setAttribute("data-rwa-action-key", key);
    var fullscreenBtn = row.querySelector('[data-rwa-fullscreen-btn="1"]');
    if (fullscreenBtn) row.insertBefore(btn, fullscreenBtn);
    else row.appendChild(btn);
    return btn;
  }

  function attachRwaTableFullscreenButton(tableWrap, tableEl, opts) {
    if (!tableWrap || !tableEl || tableWrap._rwaFullscreenBound) return;
    tableWrap._rwaFullscreenBound = true;

    var actions = ensureRwaActionRow(tableWrap, opts);
    if (!actions) return null;

    var btn = actions.querySelector('[data-rwa-fullscreen-btn="1"]');
    if (!btn) {
      btn = createRwaActionButton({
        tagName: "button",
        className: "btn btn-secondary",
      });
      btn.setAttribute("data-rwa-fullscreen-btn", "1");
      btn.textContent =
        (opts && opts.buttonLabel ? String(opts.buttonLabel) : "") || "View table full screen";
      btn.addEventListener("click", function () {
        openRwaTableModal(tableEl, {
          title: opts && opts.title ? opts.title : "Full-screen table",
        });
      });
      actions.appendChild(btn);
    }
    return actions;
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
        var isName = c === "Network" || c === "Platform" || c === "Asset manager";
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
    fillRwaTableBody(tbody, columns, rowsCopy, opts);
    wireRwaTableSortDelegate(theadRow, tbody);
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
    attachRwaTableFullscreenButton(
      tbody && tbody.closest ? tbody.closest(".table-wrap") : null,
      tbody && tbody.closest ? tbody.closest("table") : null,
      { title: "RWA Global Market Overview networks table" }
    );

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
    attachRwaTableFullscreenButton: attachRwaTableFullscreenButton,
    appendRwaActionLink: appendRwaActionLink,
  };
})(typeof window !== "undefined" ? window : this);
