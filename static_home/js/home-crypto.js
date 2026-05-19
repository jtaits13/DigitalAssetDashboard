(function () {
  var HOME_CRYPTO_PREVIEW_LIMIT = 5;
  var cryptoAllRows = [];

  var els = {
    banner: document.getElementById("js-home-crypto-banner"),
    kpi: document.getElementById("js-home-crypto-kpi"),
    story: document.getElementById("js-home-crypto-story"),
    tbody: document.getElementById("js-home-crypto-preview"),
    source: document.getElementById("js-home-crypto-source"),
    search: document.getElementById("js-home-crypto-search"),
    toolbar: document.getElementById("js-home-crypto-toolbar"),
  };

  function cryptoKpiApi() {
    return (typeof window !== "undefined" && window.__CRYPTO_KPI) || {};
  }

  function categoryLabel(row) {
    if (row.category_label) return row.category_label;
    var api = cryptoKpiApi();
    return api.categoryLabel ? api.categoryLabel(row.category || "other") : row.category || "Other";
  }

  function categoryClass(row) {
    var slug = row.category || "other";
    var api = cryptoKpiApi();
    return api.categoryClass ? api.categoryClass(slug) : "crypto-cat crypto-cat--" + slug;
  }

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

  function fmtPctTd(pct) {
    if (pct == null) return '<td class="num">—</td>';
    var n = Number(pct);
    if (!isFinite(n)) return '<td class="num">—</td>';
    var cls = n >= 0 ? "pct up" : "pct down";
    return '<td class="num ' + cls + '">' + (n >= 0 ? "+" : "") + n.toFixed(2) + "%</td>";
  }

  function renderKpi(payload) {
    var api = cryptoKpiApi();
    if (api.renderCryptoKpis && els.kpi) {
      api.renderCryptoKpis(els.kpi, payload || {});
    }
    if (els.story) {
      els.story.hidden = true;
      els.story.innerHTML = "";
    }
  }

  function filterCryptoRows(rows) {
    var q = (els.search && els.search.value ? els.search.value : "").trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(function (row) {
      return (
        (row.symbol && row.symbol.toLowerCase().indexOf(q) >= 0) ||
        (row.name && row.name.toLowerCase().indexOf(q) >= 0) ||
        (row.category && row.category.toLowerCase().indexOf(q) >= 0) ||
        (row.category_label && String(row.category_label).toLowerCase().indexOf(q) >= 0)
      );
    });
  }

  function sortCryptoRows(arr) {
    return arr.slice().sort(function (a, b) {
      return Number(b.market_cap_usd || 0) - Number(a.market_cap_usd || 0);
    });
  }

  function renderPreview() {
    if (!els.tbody) return;
    els.tbody.innerHTML = "";
    if (!cryptoAllRows || !cryptoAllRows.length) {
      els.tbody.innerHTML =
        '<tr><td colspan="7">No crypto price data is available right now.</td></tr>';
      if (els.toolbar) els.toolbar.hidden = true;
      return;
    }
    var filtered = filterCryptoRows(cryptoAllRows);
    if (els.toolbar) {
      var q = (els.search && els.search.value ? els.search.value : "").trim();
      els.toolbar.hidden = false;
      if (q) {
        els.toolbar.innerHTML =
          "Showing top " +
          HOME_CRYPTO_PREVIEW_LIMIT +
          " of <strong>" +
          filtered.length +
          "</strong> matching coins (of <strong>" +
          cryptoAllRows.length +
          "</strong> listed).";
      } else {
        els.toolbar.innerHTML =
          "Preview: top <strong>" +
          HOME_CRYPTO_PREVIEW_LIMIT +
          "</strong> by market cap (of <strong>" +
          cryptoAllRows.length +
          "</strong> listed).";
      }
    }
    if (!filtered.length) {
      els.tbody.innerHTML =
        '<tr><td colspan="7">No coins match your filter. Try another name or ticker.</td></tr>';
      return;
    }
    var rows = sortCryptoRows(filtered).slice(0, HOME_CRYPTO_PREVIEW_LIMIT);
    var w = typeof window !== "undefined" ? window : {};
    var wrap =
      typeof w.wrapCryptoHint === "function"
        ? w.wrapCryptoHint
        : function (txt) {
            return w.escapeHtml ? w.escapeHtml(String(txt || "")) : String(txt || "");
          };
    rows.forEach(function (row) {
      var tr = document.createElement("tr");
      var blurb = (row.about_blurb || "").trim();
      tr.innerHTML =
        '<td class="num">' +
        escapeHtml(String(row.rank != null ? row.rank : "—")) +
        "</td>" +
        '<td><span class="sym">' +
        wrap(row.symbol || "", blurb, "") +
        "</span></td>" +
        "<td>" +
        escapeHtml(row.name || "") +
        "</td>" +
        '<td><span class="' +
        escapeHtml(categoryClass(row)) +
        '">' +
        escapeHtml(categoryLabel(row)) +
        "</span></td>" +
        '<td class="num">' +
        escapeHtml(fmtPrice(row.price_usd)) +
        "</td>" +
        fmtPctTd(row.pct_30d) +
        '<td class="num">' +
        escapeHtml(fmtCap(row.market_cap_usd)) +
        "</td>";
      els.tbody.appendChild(tr);
    });
    if (typeof window !== "undefined" && typeof window.bindCryptoHints === "function") {
      window.bindCryptoHints(els.tbody);
    }
  }

  var freshApi = window.__DATA_FRESHNESS || {};
  var loadTimed =
    typeof freshApi.loadJsonWithTimeout === "function"
      ? freshApi.loadJsonWithTimeout
      : function (name) {
          return loadJson(name);
        };

  if (els.search) {
    els.search.addEventListener("input", renderPreview);
  }

  Promise.all([
    loadTimed("crypto_kpis.json", 12000).catch(function () {
      return null;
    }),
    loadTimed("crypto_prices.json", 12000).catch(function () {
      return { rows: [] };
    }),
  ])
    .then(function (results) {
      var kpis = results[0];
      var prices = results[1] || { rows: [] };
      if (freshApi.renderFreshness) {
        freshApi.renderFreshness(document.getElementById("js-home-crypto-as-of"), {
          at: (kpis && kpis.generated_at) || prices.generated_at,
          source: (kpis && kpis.source) || prices.source || "CoinPaprika + CoinGecko",
          mode: "snapshot",
        });
      }
      renderKpi(kpis || {});
      cryptoAllRows = prices.rows || [];
      renderPreview();
      if (els.source && kpis && kpis.source_note) {
        els.source.textContent = kpis.source_note;
      }
      if ((prices && prices.error) || (kpis && kpis.error)) {
        showErr(prices.error || kpis.error);
      }
    })
    .catch(function (err) {
      showErr("Could not load crypto market data. " + (err && err.message ? err.message : ""));
      cryptoAllRows = [];
      renderPreview();
    });
})();
