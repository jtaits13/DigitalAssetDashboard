(function () {
  var newsEl = document.getElementById("js-home-news-list");
  var regEl = document.getElementById("js-home-reg-list");
  var banner = document.getElementById("js-data-banner");
  var kpiEl = document.getElementById("js-home-kpi");
  var tblBody = document.getElementById("js-home-etp-preview");
  var etpThead = document.getElementById("js-home-etp-thead");
  var etpAllRows = [];
  var etpSort = { key: "assets_usd", dir: -1 };

  function showErr(msg) {
    if (banner) {
      banner.hidden = false;
      banner.textContent = msg;
    }
  }

  function renderList(el, items, linkArticles, useCountry) {
    if (!el) return;
    el.innerHTML = "";
    if (!items || !items.length) {
      el.innerHTML =
        '<li class="headline-list__empty">No items are available right now.</li>';
      return;
    }
    items.forEach(function (a) {
      var li = document.createElement("li");
      var title = escapeHtml(a.title || "Untitled");
      var metaParts = [a.source || "", useCountry && a.country ? a.country : "", fmtDate(a.published) || ""].filter(
        Boolean
      );
      var meta = escapeHtml(metaParts.join(" · "));
      if (linkArticles && (a.link || "").trim()) {
        li.innerHTML =
          '<a class="headline-list__link" href="' +
          escapeHtml(a.link) +
          '" target="_blank" rel="noopener noreferrer">' +
          title +
          "</a>" +
          '<span class="headline-list__meta">' +
          meta +
          "</span>";
      } else {
        li.innerHTML =
          '<span class="headline-list__link headline-list__link--plain">' +
          title +
          "</span>" +
          '<span class="headline-list__meta">' +
          meta +
          "</span>";
      }
      el.appendChild(li);
    });
  }

  function renderKpi(k) {
    if (!kpiEl || !k) return;
    var K = window.__ETP_KPI || {};
    var fmtDelta =
      typeof K.fmtPctDelta === "function"
        ? K.fmtPctDelta
        : function (p) {
            if (p == null || p === "") return '<span class="kpi-delta neutral">—</span>';
            var n = Number(p);
            var cls = n > 0 ? "up" : n < 0 ? "down" : "neutral";
            return '<span class="kpi-delta ' + cls + '">' + (n > 0 ? "+" : "") + n.toFixed(2) + "%</span>";
          };
    kpiEl.innerHTML =
      '<div class="kpi-cell">' +
      '<span class="kpi-label">Total AUM (listed)</span>' +
      '<span class="kpi-val">' +
      escapeHtml(k.total_aum_display || "—") +
      "</span>" +
      fmtDelta(k.aggregate_pct, k.aggregate_window) +
      "</div>";
  }

  function assetsB(r) {
    if (r.assets_usd == null) return "—";
    return (r.assets_usd / 1e9).toFixed(2);
  }

  function parsePrice(s) {
    if (s == null || s === "") return NaN;
    var x = String(s).replace(/,/g, "").replace(/^\$/, "");
    return parseFloat(x);
  }

  function prepareEtpRow(r) {
    var o = Object.assign({}, r);
    o.price_num = parsePrice(r.price);
    return o;
  }

  function cmpEtpCell(a, b, key) {
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

  function sortEtpPreviewRows(arr) {
    var k = etpSort.key === "price" ? "price_num" : etpSort.key;
    var d = etpSort.dir;
    var base = arr.map(prepareEtpRow);
    if (k === "assets_usd" || k === "price_num") {
      return base.slice().sort(function (a, b) {
        var va = k === "assets_usd" ? a.assets_usd : a.price_num;
        var vb = k === "assets_usd" ? b.assets_usd : b.price_num;
        var aBad = va == null || (typeof va === "number" && !isFinite(va));
        var bBad = vb == null || (typeof vb === "number" && !isFinite(vb));
        if (aBad && bBad) return String(a.symbol || "").localeCompare(String(b.symbol || ""));
        if (aBad) return 1;
        if (bBad) return -1;
        var na = Number(va);
        var nb = Number(vb);
        if (d < 0) return nb - na;
        return na - nb;
      });
    }
    return base.slice().sort(function (a2, b2) {
      return d * cmpEtpCell(a2, b2, k);
    });
  }

  function updateHomeEtpSortClass() {
    if (!etpThead) return;
    etpThead.querySelectorAll("th[data-sort]").forEach(function (h) {
      h.classList.remove("is-sorted", "is-sorted-asc", "is-sorted-desc");
      h.removeAttribute("aria-sort");
    });
    var active = etpThead.querySelector('th[data-sort="' + etpSort.key + '"]');
    if (active) {
      active.classList.add("is-sorted", etpSort.dir > 0 ? "is-sorted-asc" : "is-sorted-desc");
      active.setAttribute("aria-sort", etpSort.dir > 0 ? "ascending" : "descending");
    }
  }

  function wireHomeEtpSort() {
    if (!etpThead || etpThead._homeEtpSortBound) return;
    etpThead._homeEtpSortBound = true;
    etpThead.addEventListener("click", function (ev) {
      var th = ev.target.closest("th[data-sort]");
      if (!th) return;
      var key = th.getAttribute("data-sort");
      if (!key) return;
      if (etpSort.key === key) etpSort.dir *= -1;
      else {
        etpSort.key = key;
        etpSort.dir = key === "symbol" || key === "name" ? 1 : -1;
      }
      updateHomeEtpSortClass();
      renderPreview();
    });
  }

  function fmt52cell(p) {
    if (p == null) return '<td class="num">—</td>';
    var n = Number(p);
    var cls = n >= 0 ? "pct up" : "pct down";
    return (
      '<td class="num ' + cls + '">' + (n >= 0 ? "+" : "") + n.toFixed(1) + "%</td>"
    );
  }

  function renderPreview() {
    if (!tblBody) return;
    tblBody.innerHTML = "";
    if (!etpAllRows || !etpAllRows.length) {
      tblBody.innerHTML = '<tr><td colspan="5">No ETP data. Export script not run yet.</td></tr>';
      return;
    }
    var rows = sortEtpPreviewRows(etpAllRows).slice(0, 5);
    rows.forEach(function (r) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        '<td><span class="sym">' +
        escapeHtml(r.symbol) +
        "</span></td>" +
        "<td>" +
        escapeHtml(r.name) +
        "</td>" +
        '<td class="num">' +
        escapeHtml(String(r.price || "—")) +
        "</td>" +
        fmt52cell(r.pct_52w) +
        '<td class="num">' +
        assetsB(r) +
        "</td>";
      tblBody.appendChild(tr);
    });
  }

  Promise.all([
    loadJson("manifest.json").catch(function () {
      return { errors: [] };
    }),
    loadJson("home_news.json").catch(function () {
      return { items: [] };
    }),
    loadJson("regulatory.json").catch(function () {
      return { items: [] };
    }),
    loadJson("etp_kpis.json").catch(function () {
      return null;
    }),
    loadJson("etps.json").catch(function () {
      return { rows: [] };
    }),
    loadJson("rwa_onchain_home.json").catch(function () {
      return null;
    }),
  ])
    .then(function (results) {
      var manifest = results[0];
      var homeNews = results[1];
      var reg = results[2];
      var kpis = results[3];
      var etps = results[4];
      var rwaOnchain = results[5];

      var visibleManifestErrors = (manifest.errors || []).filter(function (msg) {
        return String(msg || "").indexOf("Crypto global snapshot:") !== 0;
      });

      if (visibleManifestErrors.length && banner) {
        banner.hidden = false;
        banner.textContent =
          "Some data sources reported issues (site still works): " + visibleManifestErrors.slice(0, 3).join("; ");
      }

      renderList(newsEl, homeNews.items || [], true, false);
      renderList(regEl, reg.items || [], true, true);
      renderKpi(kpis);
      etpAllRows = etps.rows || [];
      updateHomeEtpSortClass();
      renderPreview();
      wireHomeEtpSort();
      if (typeof renderRwaOnchainHome === "function") {
        renderRwaOnchainHome(rwaOnchain || {});
      }
    })
    .catch(function (e) {
      showErr(
        "Could not load the site data. " +
          (e && e.message ? e.message : "")
      );
    });
})();
