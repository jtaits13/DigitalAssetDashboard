(function () {
  var newsEl = document.getElementById("js-home-news-list");
  var regEl = document.getElementById("js-home-reg-list");
  var banner = document.getElementById("js-data-banner");
  var kpiEl = document.getElementById("js-home-kpi");
  var tblBody = document.getElementById("js-home-etp-preview");

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
        '<li class="headline-list__empty">No items loaded. Run <code>python scripts/export_static_site_data.py</code> or open the GitHub Pages deploy.</li>';
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
      "</div>" +
      '<div class="kpi-cell">' +
      '<span class="kpi-label">IBIT · AUM</span>' +
      '<span class="kpi-val">' +
      escapeHtml(k.ibit && k.ibit.aum_display) +
      "</span>" +
      (k.ibit && k.ibit.delta ? fmtDelta(k.ibit.delta.pct, k.ibit.delta.window) : "") +
      "</div>" +
      '<div class="kpi-cell">' +
      '<span class="kpi-label">ETHA · AUM</span>' +
      '<span class="kpi-val">' +
      escapeHtml(k.etha && k.etha.aum_display) +
      "</span>" +
      (k.etha && k.etha.delta ? fmtDelta(k.etha.delta.pct, k.etha.delta.window) : "") +
      "</div>";
  }

  function assetsB(r) {
    if (r.assets_usd == null) return "—";
    return (r.assets_usd / 1e9).toFixed(2);
  }

  function fmt52cell(p) {
    if (p == null) return '<td class="num">—</td>';
    var n = Number(p);
    var cls = n >= 0 ? "pct up" : "pct down";
    return (
      '<td class="num ' + cls + '">' + (n >= 0 ? "+" : "") + n.toFixed(1) + "%</td>"
    );
  }

  function renderPreview(rows) {
    if (!tblBody) return;
    tblBody.innerHTML = "";
    if (!rows || !rows.length) {
      tblBody.innerHTML = '<tr><td colspan="5">No ETP data. Export script not run yet.</td></tr>';
      return;
    }
    rows.slice(0, 5).forEach(function (r) {
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

      if (manifest.errors && manifest.errors.length && banner) {
        banner.hidden = false;
        banner.textContent =
          "Some data sources reported issues (site still works): " + manifest.errors.slice(0, 3).join("; ");
      }

      renderList(newsEl, homeNews.items || [], true, false);
      renderList(regEl, reg.items || [], true, true);
      renderKpi(kpis);
      renderPreview(etps.rows || []);
      if (typeof renderRwaOnchainHome === "function") {
        renderRwaOnchainHome(rwaOnchain || {});
      }
    })
    .catch(function (e) {
      showErr(
        "Could not load live JSON (open via GitHub Pages or run export script). " + (e && e.message ? e.message : "")
      );
    });
})();
