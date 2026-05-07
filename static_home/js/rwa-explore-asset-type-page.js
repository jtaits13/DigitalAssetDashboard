/**
 * Static Explore by Asset Type index — ``static_home/data/rwa_explore_asset_type.json``.
 * Mirrors Streamlit ``show_rwa_explore_by_asset_type_widget`` (preview_rows=8).
 */
(function (global) {
  function $(id) {
    return document.getElementById(id);
  }

  function assetPath(rel) {
    var S = global.__STATIC;
    return S && typeof S.assetUrl === "function" ? S.assetUrl(rel) : rel;
  }

  function renderExploreAssetTypePage(data) {
    var H = global.__RWA_STATIC_HELPERS || {};
    var renderKpis = H.renderKpis;
    var renderTable = H.renderTable;
    if (!renderKpis || !renderTable) {
      console.error("rwa-explore-asset-type-page: load rwa-onchain-home.js first.");
      return;
    }

    var sub = $("js-exat-subtitle");
    if (sub) sub.innerHTML = data.page_subtitle_html || "";

    var intro = $("js-exat-intro");
    if (intro) intro.innerHTML = data.intro_html || "";

    var foot = $("js-exat-footer-note");
    if (foot) foot.textContent = data.footer_note || "";

    var L = data.links || {};
    var bg = $("js-exat-back-global");
    var bh = $("js-exat-back-hub");
    if (bg && L.rwa_global) bg.setAttribute("href", assetPath(L.rwa_global));
    if (bh && L.hub_home) bh.setAttribute("href", assetPath(L.hub_home));

    var root = $("js-exat-sections");
    if (!root) return;
    root.innerHTML = "";

    (data.sections || []).forEach(function (sec, idx) {
      if (idx > 0) {
        var hr = document.createElement("hr");
        hr.className = "section-rule";
        root.appendChild(hr);
      }

      var section = document.createElement("section");
      section.className = "hub-section rwa-exat-section";
      if (sec.anchor_id) section.id = sec.anchor_id;

      var h2 = document.createElement("h2");
      h2.className = "subsection-head rwa-exat-asset-heading";
      h2.textContent = sec.title || "Section";
      section.appendChild(h2);

      var kpiHost = document.createElement("div");
      kpiHost.className = "rwa-exat-kpi-host";
      section.appendChild(kpiHost);

      renderKpis(kpiHost, sec.kpis || [], sec.kpi_window_note || "", { hideIfEmpty: true });

      if (sec.warn_html) {
        var w = document.createElement("div");
        w.innerHTML = sec.warn_html;
        while (w.firstChild) {
          section.appendChild(w.firstChild);
        }
      }

      if (sec.info_html) {
        var info = document.createElement("div");
        info.innerHTML = sec.info_html;
        while (info.firstChild) {
          section.appendChild(info.firstChild);
        }
      }

      if (sec.table_subheading) {
        var h3 = document.createElement("h3");
        h3.className = "subsection-head rwa-exat-subhead";
        h3.textContent = sec.table_subheading;
        section.appendChild(h3);
      }

      if (sec.preview_note) {
        var pn = document.createElement("p");
        pn.className = "toolbar-note";
        pn.textContent = sec.preview_note;
        section.appendChild(pn);
      }

      if (sec.columns && sec.columns.length) {
        var wrap = document.createElement("div");
        wrap.className = "table-scroll rwa-exat-table-wrap";
        var table = document.createElement("table");
        table.className = "data-table data-table--dense";
        var thead = document.createElement("thead");
        var trh = document.createElement("tr");
        var tbody = document.createElement("tbody");
        thead.appendChild(trh);
        table.appendChild(thead);
        table.appendChild(tbody);
        wrap.appendChild(table);
        section.appendChild(wrap);

        renderTable(trh, tbody, sec.columns, sec.rows || [], {
          emptyMsg: "No preview rows for this section.",
          linkAria: "Open RWA.xyz",
        });
      }

      var ctaRow = document.createElement("div");
      ctaRow.className = "cta-row rwa-exat-cta-row";
      (sec.cta || []).forEach(function (c) {
        var a = document.createElement("a");
        a.href = c.href || "#";
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.textContent = c.label || "Open";
        a.className = c.variant === "primary" ? "btn btn-primary" : "btn btn-secondary";
        ctaRow.appendChild(a);
      });
      section.appendChild(ctaRow);

      root.appendChild(section);
    });
  }

  function boot() {
    loadJson("rwa_explore_asset_type.json")
      .then(renderExploreAssetTypePage)
      .catch(function (e) {
        var b = $("js-exat-banner");
        if (b) {
          b.hidden = false;
          b.textContent =
            (e && e.message) ||
            "Could not load rwa_explore_asset_type.json. Run python scripts/export_static_site_data.py.";
        }
      });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})(typeof window !== "undefined" ? window : this);
