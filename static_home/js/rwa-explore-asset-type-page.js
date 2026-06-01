/**
 * Static Explore by Asset Type / Market Participant index.
 * Renders from ``rwa_explore_asset_type.json`` or ``rwa_explore_market_participant.json``.
 */
(function (global) {
  function $(id) {
    return document.getElementById(id);
  }

  function assetPath(rel) {
    var S = global.__STATIC;
    return S && typeof S.assetUrl === "function" ? S.assetUrl(rel) : rel;
  }

  function previewEntityFromColumns(columns) {
    var cols = columns || [];
    if (cols.indexOf("Network") >= 0) return { entity: "networks", label: "Filter preview by network name", placeholder: "Filter by network…" };
    if (cols.indexOf("Platform") >= 0) return { entity: "platforms", label: "Filter preview by platform name", placeholder: "Filter by platform…" };
    if (cols.indexOf("Asset Manager") >= 0) {
      return { entity: "asset managers", label: "Filter preview by asset manager", placeholder: "Filter by name…" };
    }
    return { entity: "rows", label: "Filter preview table", placeholder: "Filter…" };
  }

  function renderExploreAssetTypePage(data) {
    var H = global.__RWA_STATIC_HELPERS || {};
    var renderKpis = H.renderKpis;
    var renderTable = H.renderTable;
    var attachTableFullscreenButton = H.attachRwaTableFullscreenButton;
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
    document.querySelectorAll('a[data-exat-link="global"]').forEach(function (el) {
      if (L.rwa_global) el.setAttribute("href", assetPath(L.rwa_global));
    });
    document.querySelectorAll('a[data-exat-link="hub"]').forEach(function (el) {
      if (L.hub_home) el.setAttribute("href", assetPath(L.hub_home));
    });
    var assetTypeEls = document.querySelectorAll('a[data-exat-link="asset-type"]');
    if (L.explore_asset_type) {
      assetTypeEls.forEach(function (el) {
        el.setAttribute("href", assetPath(L.explore_asset_type));
        el.hidden = false;
      });
    } else {
      assetTypeEls.forEach(function (el) {
        el.hidden = true;
      });
    }

    var root = $("js-exat-sections");
    if (!root) return;
    root.innerHTML = "";

    (data.sections || []).forEach(function (sec) {
      var section = document.createElement("section");
      section.className = "hub-section hub-section--panel inner-rich-block rwa-exat-section";
      if (sec.anchor_id) section.id = sec.anchor_id;

      var h2 = document.createElement("h2");
      h2.className = "subsection-head rwa-exat-asset-heading";
      h2.textContent = sec.title || "Section";
      section.appendChild(h2);

      var meth = global.__PAGE_METHODOLOGY;
      var explorePage = document.body.classList.contains("page-rwa-explore-mp")
        ? "participant"
        : "asset";
      if (meth && typeof meth.exploreBullets === "function" && sec.id) {
        var bullets = meth.exploreBullets(explorePage, sec.id);
        if (bullets && typeof meth.buildElement === "function") {
          var panel = meth.buildElement(bullets);
          if (panel) section.appendChild(panel);
        }
      }

      var kpiHost = document.createElement("div");
      kpiHost.className = "rwa-exat-kpi-host";
      section.appendChild(kpiHost);

      var kpiOpts = { hideIfEmpty: true };
      if (document.body.classList.contains("page-rwa-explore-mp")) {
        kpiOpts.participantKpis = true;
        if (sec.id === "participant_networks" || sec.id === "participant_platforms") {
          kpiOpts.dropStablecoinHolders = true;
        }
      }
      renderKpis(kpiHost, sec.kpis || [], sec.kpi_window_note || "", kpiOpts);

      if (sec.info_html_preview) {
        var iprev = document.createElement("div");
        iprev.className = "rwa-exat-preview-caption";
        iprev.innerHTML = sec.info_html_preview;
        section.appendChild(iprev);
      }

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

      var searchId = "js-exat-search-" + String(sec.id || sec.anchor_id || "section");
      var toolbarId = "js-exat-toolbar-" + String(sec.id || sec.anchor_id || "section");
      var previewMeta = previewEntityFromColumns(sec.columns);

      if (sec.columns && sec.columns.length) {
        var searchLabel = document.createElement("label");
        searchLabel.className = "search-field home-preview-search-row rwa-exat-search-row";
        searchLabel.setAttribute("for", searchId);
        searchLabel.innerHTML =
          '<span class="search-field__label">' +
          previewMeta.label +
          '</span><input type="search" class="search-field__input" id="' +
          searchId +
          '" placeholder="' +
          previewMeta.placeholder +
          '" />';
        section.appendChild(searchLabel);

        var toolbar = document.createElement("p");
        toolbar.className = "toolbar-note";
        toolbar.id = toolbarId;
        toolbar.hidden = true;
        section.appendChild(toolbar);

        if (sec.preview_note) {
          var pn = document.createElement("p");
          pn.className = "toolbar-note rwa-exat-preview-note";
          pn.textContent = sec.preview_note;
          section.appendChild(pn);
        }

        var wrap = document.createElement("div");
        wrap.className = "table-wrap rwa-exat-table-wrap";
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

        var searchInput = searchLabel.querySelector("input");
        var previewLimit = (sec.rows || []).length || 8;
        var allRows =
          sec.rows_full && sec.rows_full.length ? sec.rows_full : sec.rows || [];
        renderTable(trh, tbody, sec.columns, allRows, {
          emptyMsg: "No preview rows for this section.",
          linkAria: "Open RWA.xyz",
          homePreview: true,
          previewScope: "explore",
          previewEntity: previewMeta.entity,
          previewLimit: previewLimit,
          searchEl: searchInput,
          toolbarEl: toolbar,
        });
      } else if (sec.preview_note) {
        var pnOnly = document.createElement("p");
        pnOnly.className = "toolbar-note";
        pnOnly.textContent = sec.preview_note;
        section.appendChild(pnOnly);
      }

      var ctaRow = document.createElement("div");
      ctaRow.className = "cta-row rwa-exat-cta-row";
      (sec.cta || []).forEach(function (c) {
        var hrefRaw = String(c.href != null ? c.href : "").trim();
        var a = document.createElement("a");
        a.textContent = c.label || "Open";
        a.className = c.variant === "primary" ? "btn btn-primary" : "btn btn-secondary";
        if (c.internal) {
          var rel = hrefRaw.replace(/^\.\//, "");
          a.href =
            global.__STATIC && typeof global.__STATIC.assetUrl === "function"
              ? global.__STATIC.assetUrl(rel)
              : rel;
          a.removeAttribute("target");
          a.removeAttribute("rel");
        } else {
          a.href = hrefRaw || "#";
          a.target = "_blank";
          a.rel = "noopener noreferrer";
        }
        ctaRow.appendChild(a);
      });

      var tableWrap = section.querySelector(".rwa-exat-table-wrap");
      if (tableWrap && attachTableFullscreenButton) {
        var tableEl = tableWrap.querySelector("table");
        attachTableFullscreenButton(tableWrap, tableEl, {
          title: String(sec.table_subheading || sec.title || "RWA preview table"),
          actionRow: ctaRow,
        });
      }
      section.appendChild(ctaRow);
      if (typeof global.finalizeHubAnchors === "function") {
        global.finalizeHubAnchors(section);
      }

      root.appendChild(section);
    });
  }

  function boot() {
    var intro = $("js-exat-intro");
    var body = document.querySelector(".inner-rich-zone__body");
    if (intro && body && intro.parentElement && intro.parentElement.classList.contains("home-zone__titles")) {
      var banner = $("js-exat-banner");
      var sections = $("js-exat-sections");
      if (banner && banner.parentElement === body) {
        body.insertBefore(intro, sections || banner.nextSibling);
      } else if (sections) {
        body.insertBefore(intro, sections);
      } else {
        body.insertBefore(intro, body.firstChild);
      }
      intro.classList.add("rwa-exat-intro--in-body");
    }

    var name =
      (document.body.getAttribute("data-explore-json") || "rwa_explore_asset_type.json").trim();
    loadJson(name)
      .then(renderExploreAssetTypePage)
      .catch(function (e) {
        var b = $("js-exat-banner");
        if (b) {
          b.hidden = false;
          b.textContent =
            (e && e.message) ||
            "Could not load explore index JSON.";
        }
      });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})(typeof window !== "undefined" ? window : this);
