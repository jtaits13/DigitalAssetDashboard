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

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var EXPLORE_PREVIEW_ROWS = 8;
  var EXPLORE_ASSET_SECTION_SKIP = { stablecoins: true, tokenized_mmf: true };

  function slugExploreExportFilename(sec) {
    var base = sec.id || sec.anchor_id || sec.title || "rwa-preview";
    return (
      String(base)
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "") || "rwa-preview"
    );
  }

  function previewEntityFromColumns(columns) {
    var cols = columns || [];
    if (cols.indexOf("Network") >= 0) {
      return {
        entity: "networks",
        label: "Search network table",
        placeholder: "Filter by network name\u2026",
        introStrong: "Networks",
      };
    }
    if (cols.indexOf("Platform") >= 0) {
      return {
        entity: "platforms",
        label: "Search platform table",
        placeholder: "Filter by platform name\u2026",
        introStrong: "Platforms",
      };
    }
    if (cols.indexOf("Asset Manager") >= 0) {
      return {
        entity: "asset managers",
        label: "Search asset manager table",
        placeholder: "Filter by asset manager name\u2026",
        introStrong: "Asset managers",
      };
    }
    return {
      entity: "rows",
      label: "Filter preview table",
      placeholder: "Filter\u2026",
      introStrong: "Rows",
    };
  }

  function isParticipantPage() {
    return document.body.classList.contains("page-rwa-explore-mp");
  }

  function filteredSections(data) {
    return (data.sections || []).filter(function (sec) {
      return !EXPLORE_ASSET_SECTION_SKIP[sec.id];
    });
  }

  function primaryInternalCta(sec) {
    var ctas = sec.cta || [];
    var i;
    for (i = 0; i < ctas.length; i++) {
      if (ctas[i].variant === "primary" && ctas[i].internal) return ctas[i];
    }
    for (i = 0; i < ctas.length; i++) {
      if (ctas[i].internal) return ctas[i];
    }
    return ctas[0] || null;
  }

  function ctaHref(cta) {
    if (!cta) return "#";
    var hrefRaw = String(cta.href != null ? cta.href : "").trim();
    if (cta.internal) {
      var rel = hrefRaw.replace(/^\.\//, "");
      return global.__STATIC && typeof global.__STATIC.assetUrl === "function"
        ? global.__STATIC.assetUrl(rel)
        : rel;
    }
    return hrefRaw || "#";
  }

  function tableBlockTitle(sec, meta) {
    if (sec.table_block_title) return sec.table_block_title;
    if (meta.entity === "networks") return "Networks table";
    if (meta.entity === "platforms") return "Platforms table";
    if (meta.entity === "asset managers") return "Asset managers table";
    return (sec.title || "Preview") + " table";
  }

  function tableIntroHtml(sec, meta, isMp) {
    if (sec.table_intro_html) return sec.table_intro_html;
    if (isMp && meta.entity === "networks") {
      return (
        "<strong>Networks</strong> &mdash; distributed and represented RWA value by chain (RWA.xyz). Filter by name below."
      );
    }
    if (isMp && meta.entity === "platforms") {
      return (
        "<strong>Platforms</strong> &mdash; distributed RWA value by issuance platform (RWA.xyz). Filter by name below."
      );
    }
    if (isMp && meta.entity === "asset managers") {
      return "<strong>Asset managers</strong> &mdash; distributed AUM by issuer (RWA.xyz). Filter by name below.";
    }
    return (
      "<strong>" +
      esc(meta.introStrong) +
      "</strong> &mdash; preview league from RWA.xyz. Filter by name below."
    );
  }

  function sectionPreviewDek(sec, isMp) {
    if (sec.info_html_preview) return sec.info_html_preview;
    var title = sec.title || "this category";
    if (isMp) {
      return (
        "Distributed and represented RWA value for <strong>" +
        esc(title) +
        "</strong> &mdash; preview shows the first eight rows; open the full overview for charts and complete tables."
      );
    }
    return (
      "<strong>Networks</strong> league preview for <strong>" +
      esc(title) +
      "</strong> (RWA.xyz) &mdash; first eight rows below; open the full overview for platforms table and complete chart."
    );
  }

  function snapshotFreshnessHtml(data, sec) {
    var note = data.footer_note || "";
    var label = sec.title || "RWA";
    if (note) {
      return "Snapshot &middot; " + esc(label) + " &middot; " + esc(note);
    }
    return "Snapshot &middot; " + esc(label) + " &middot; Source: RWA.xyz";
  }

  function renderJumpNav(sections) {
    var nav = $("js-exat-jump");
    if (!nav || !sections.length) return;
    nav.hidden = false;
    nav.innerHTML =
      '<span class="rwa-explore-mock-jump__label">Jump to</span>' +
      sections
        .map(function (sec) {
          var id = sec.anchor_id || "preview-" + (sec.id || "section");
          return (
            '<a class="rwa-explore-mock-jump__link" href="#' +
            esc(id) +
            '">' +
            esc(sec.title || "Section") +
            "</a>"
          );
        })
        .join("");
  }

  function renderExploreAssetTypePage(data) {
    var H = global.__RWA_STATIC_HELPERS || {};
    var renderKpis = H.renderKpis;
    var renderTable = H.renderTable;
    var attachTableFullscreenButton = H.attachRwaTableFullscreenButton;
    var buildPreviewTableExportData = H.buildPreviewTableExportData;
    if (!renderKpis || !renderTable) {
      console.error("rwa-explore-asset-type-page: load rwa-onchain-home.js first.");
      return;
    }

    var isMp = isParticipantPage();
    var sub = $("js-exat-subtitle");
    if (sub) sub.innerHTML = data.page_subtitle_html || "";

    var intro = $("js-exat-intro");
    if (intro) {
      intro.innerHTML = data.intro_html || "";
      intro.classList.add("rwa-explore-mock-intro");
    }

    var foot = $("js-exat-footer-note");
    if (foot) foot.textContent = data.footer_note || "";

    var ts = $("js-exat-timestamp");
    if (ts && data.footer_note) {
      ts.textContent = "Generated " + data.footer_note;
    }

    var L = data.links || {};
    document.querySelectorAll('a[data-exat-link="global"]').forEach(function (el) {
      if (L.rwa_global) el.setAttribute("href", assetPath(L.rwa_global));
    });
    document.querySelectorAll('a[data-exat-link="hub"]').forEach(function (el) {
      if (L.hub_home) el.setAttribute("href", assetPath(L.hub_home));
    });

    var sections = filteredSections(data);
    renderJumpNav(sections);

    var root = $("js-exat-sections");
    if (!root) return;
    root.innerHTML = "";
    root.classList.add("rwa-explore-previews");

    sections.forEach(function (sec) {
      var anchorId = sec.anchor_id || "preview-" + (sec.id || "section");
      var previewMeta = previewEntityFromColumns(sec.columns);
      var primaryCta = primaryInternalCta(sec);

      var section = document.createElement("section");
      section.className = "rwa-explore-preview" + (isMp ? " rwa-explore-preview--participants" : "");
      section.id = anchorId;
      section.setAttribute("aria-labelledby", anchorId + "-heading");

      var head = document.createElement("div");
      head.className = "rwa-explore-preview__head";
      head.innerHTML =
        '<div class="rwa-explore-preview__head-copy">' +
        '<p class="rwa-explore-preview__eyebrow">' +
        (isMp ? "Participant deep page" : "Asset deep page") +
        "</p>" +
        '<h2 class="subsection-head" id="' +
        esc(anchorId) +
        '-heading">' +
        esc(sec.title || "Section") +
        "</h2>" +
        '<p class="rwa-explore-preview__dek">' +
        sectionPreviewDek(sec, isMp) +
        "</p>" +
        "</div>";
      if (primaryCta) {
        var headLink = document.createElement("a");
        headLink.className = "rwa-explore-preview__head-link";
        headLink.href = ctaHref(primaryCta);
        headLink.textContent = "Full overview \u2192";
        if (!primaryCta.internal) {
          headLink.target = "_blank";
          headLink.rel = "noopener noreferrer";
        }
        head.appendChild(headLink);
      }
      section.appendChild(head);

      var snap = document.createElement("section");
      snap.className = "etp-mock-snapshot";
      snap.setAttribute("aria-labelledby", anchorId + "-snapshot");
      snap.innerHTML =
        '<h3 class="subsection-head u-vh" id="' +
        esc(anchorId) +
        '-snapshot">' +
        esc(sec.title || "Section") +
        " snapshot</h3>" +
        '<p class="data-freshness etp-mock-freshness">' +
        snapshotFreshnessHtml(data, sec) +
        "</p>";

      var kpiHost = document.createElement("div");
      kpiHost.className = "rwa-exat-kpi-host";
      snap.appendChild(kpiHost);

      var kpiOpts = { hideIfEmpty: true };
      if (isMp) {
        kpiOpts.participantKpis = true;
        if (sec.id === "participant_networks" || sec.id === "participant_platforms") {
          kpiOpts.dropStablecoinHolders = true;
        }
      }
      renderKpis(kpiHost, sec.kpis || [], "", kpiOpts);
      var kpiPanel = kpiHost.querySelector(".rwa-kpi-panel-static");
      if (kpiPanel) kpiPanel.classList.add("rwa-kpi-panel-static--compact");

      if (sec.kpi_window_note) {
        var snapNote = document.createElement("p");
        snapNote.className = "etp-mock-snapshot__note";
        snapNote.innerHTML = sec.kpi_window_note;
        snap.appendChild(snapNote);
      }
      section.appendChild(snap);

      if (sec.warn_html) {
        var w = document.createElement("div");
        w.innerHTML = sec.warn_html;
        while (w.firstChild) section.appendChild(w.firstChild);
      }

      var searchId = "js-exat-search-" + String(sec.id || sec.anchor_id || "section");
      var toolbarId = "js-exat-toolbar-" + String(sec.id || sec.anchor_id || "section");
      var actionsId = "js-exat-table-actions-" + String(sec.id || sec.anchor_id || "section");
      var metaActionsId = actionsId + "-meta";
      var tableTitle = tableBlockTitle(sec, previewMeta);

      var ctaRow = document.createElement("div");
      ctaRow.className = "cta-row etp-mock-bottom-cta rwa-exat-cta-row";
      (sec.cta || []).forEach(function (c) {
        var a = document.createElement("a");
        a.textContent = c.label || "Open";
        a.className = c.variant === "primary" ? "btn btn-primary" : "btn btn-secondary";
        a.href = ctaHref(c);
        if (!c.internal) {
          a.target = "_blank";
          a.rel = "noopener noreferrer";
        }
        ctaRow.appendChild(a);
      });

      if (sec.columns && sec.columns.length) {
        var tableBlock = document.createElement("div");
        tableBlock.className =
          "etp-mock-table-block stable-mock-league-block" +
          (isMp ? " participants-mock-league-block" : "");

        var tableHead = document.createElement("div");
        tableHead.className = "rwa-explore-preview__table-head rwa-split-table-head inner-table-head";
        tableHead.innerHTML =
          '<h3 class="subsection-head rwa-split-table-head__title" id="' +
          esc(anchorId) +
          '-table">' +
          esc(tableTitle) +
          '</h3><div class="rwa-split-table-head__actions" id="' +
          actionsId +
          '"></div>';
        tableBlock.appendChild(tableHead);
        var titleActionsEl = tableHead.querySelector(".rwa-split-table-head__actions");

        var tableIntro = document.createElement("p");
        tableIntro.className =
          "stable-mock-league-intro rwa-explore-preview__table-intro" +
          (isMp ? " participants-mock-league-intro" : "");
        tableIntro.innerHTML = tableIntroHtml(sec, previewMeta, isMp);
        tableBlock.appendChild(tableIntro);

        var searchLabel = document.createElement("label");
        searchLabel.className = "search-field etp-mock-table-search";
        searchLabel.setAttribute("for", searchId);
        searchLabel.innerHTML =
          '<span class="search-field__label">' +
          esc(previewMeta.label) +
          '</span><input type="search" class="search-field__input" id="' +
          searchId +
          '" placeholder="' +
          esc(previewMeta.placeholder) +
          '" />';
        tableBlock.appendChild(searchLabel);

        var metaRow = document.createElement("div");
        metaRow.className = "etp-mock-table-meta";
        metaRow.setAttribute("aria-live", "polite");
        var toolbar = document.createElement("p");
        toolbar.className = "etp-mock-table-meta__count toolbar-note";
        toolbar.id = toolbarId;
        toolbar.hidden = true;
        var metaActions = document.createElement("div");
        metaActions.id = metaActionsId;
        metaRow.appendChild(toolbar);
        metaRow.appendChild(metaActions);
        tableBlock.appendChild(metaRow);

        var tableWrap = document.createElement("div");
        tableWrap.className = "table-wrap table-wrap--scroll rwa-split-table-scroll rwa-exat-table-wrap";
        tableWrap.setAttribute("data-fullscreen-title", tableTitle);
        var tableEl = document.createElement("table");
        tableEl.className = "data-table data-table--dense data-table--sortable";
        tableEl.setAttribute("aria-labelledby", anchorId + "-table");
        var thead = document.createElement("thead");
        var trh = document.createElement("tr");
        var tbody = document.createElement("tbody");
        thead.appendChild(trh);
        tableEl.appendChild(thead);
        tableEl.appendChild(tbody);
        tableWrap.appendChild(tableEl);
        tableBlock.appendChild(tableWrap);

        if (sec.preview_note) {
          var footnoteRow = document.createElement("div");
          footnoteRow.className = "rwa-table-footnote-row";
          footnoteRow.innerHTML =
            '<p class="source-cap rwa-table-footnote-row__cap rwa-exat-preview-note">' +
            esc(sec.preview_note) +
            "</p>";
          tableBlock.appendChild(footnoteRow);
        }

        section.appendChild(tableBlock);

        var searchInput = searchLabel.querySelector("input");
        var allRows = sec.rows_full && sec.rows_full.length ? sec.rows_full : sec.rows || [];
        renderTable(trh, tbody, sec.columns, allRows, {
          emptyMsg: "No preview rows for this section.",
          linkAria: "Open RWA.xyz",
          homePreview: true,
          previewScope: "explore",
          previewEntity: previewMeta.entity,
          previewLimit: EXPLORE_PREVIEW_ROWS,
          searchEl: searchInput,
          toolbarEl: toolbar,
        });

        if (attachTableFullscreenButton) {
          attachTableFullscreenButton(tableWrap, tableEl, {
            title: String(sec.table_subheading || sec.title || "RWA preview table"),
            filename: slugExploreExportFilename(sec),
            downloadPlacement: "title-row",
            downloadAnchor: titleActionsEl,
            actionRow: metaActions,
            getExportData: function () {
              if (typeof buildPreviewTableExportData === "function" && tbody) {
                return buildPreviewTableExportData(tbody, {
                  exportColumns: sec.columns,
                  sheetName: String(sec.title || "Data").slice(0, 31),
                });
              }
              return null;
            },
          });
        }
      } else if (sec.preview_note) {
        var pnOnly = document.createElement("p");
        pnOnly.className = "toolbar-note rwa-exat-preview-note";
        pnOnly.textContent = sec.preview_note;
        section.appendChild(pnOnly);
      }

      section.appendChild(ctaRow);
      if (typeof global.finalizeHubAnchors === "function") {
        global.finalizeHubAnchors(section);
      }
      root.appendChild(section);
    });
  }

  function boot() {
    var name = (document.body.getAttribute("data-explore-json") || "rwa_explore_asset_type.json").trim();
    loadJson(name)
      .then(renderExploreAssetTypePage)
      .catch(function (e) {
        var b = $("js-exat-banner");
        if (b) {
          b.hidden = false;
          b.textContent = (e && e.message) || "Could not load explore index JSON.";
        }
      });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})(typeof window !== "undefined" ? window : this);
