/**
 * Home page: Stablecoins + TMMF preview zones (data from explore asset type + optional MMF page export).
 */
(function () {
  var H = window.__RWA_STATIC_HELPERS;
  if (!H || typeof H.renderKpis !== "function" || typeof H.renderTable !== "function") return;

  var HOME_PREVIEW = 5;
  var STABLE_HOME_COLS = ["Network", "Stablecoins", "Total Value", "Market Share", "30D Δ share"];
  var TMMF_FUND_COLS = ["Fund Name", "Ticker", "Platform", "Total Value", "7D Δ value"];
  var TMMF_NET_COLS = ["Network", "Distributed Value", "30D Δ share", "Link"];

  var freshApi = window.__DATA_FRESHNESS || {};
  var loadTimed =
    typeof freshApi.loadJsonWithTimeout === "function"
      ? freshApi.loadJsonWithTimeout
      : function (name) {
          return loadJson(name);
        };

  function findSection(payload, id) {
    var sections = (payload && payload.sections) || [];
    for (var i = 0; i < sections.length; i++) {
      if (sections[i].id === id) return sections[i];
    }
    return null;
  }

  function showBanner(id, msg) {
    var banner = document.getElementById(id);
    if (!banner) return;
    if (msg && String(msg).trim()) {
      banner.hidden = false;
      banner.textContent = msg;
    } else {
      banner.hidden = true;
      banner.textContent = "";
    }
  }

  function renderFreshness(elId, at) {
    if (!freshApi.renderFreshness || !at) return;
    freshApi.renderFreshness(document.getElementById(elId), {
      at: at,
      source: "RWA.xyz",
      mode: "snapshot",
    });
  }

  function renderStablecoinsHome(explore, generatedAt) {
    var section = findSection(explore, "stablecoins");
    var kpiHost = document.getElementById("js-home-stable-kpi");
    var theadRow = document.getElementById("js-home-stable-thead-row");
    var tbody = document.getElementById("js-home-stable-tbody");

    if (!section) {
      showBanner("js-home-stable-banner", "Stablecoins preview data is unavailable.");
      if (kpiHost) kpiHost.innerHTML = "";
      if (tbody) tbody.innerHTML = '<tr><td colspan="5">Stablecoins data is unavailable.</td></tr>';
      return;
    }

    showBanner("js-home-stable-banner", "");
    renderFreshness("js-home-stable-as-of", generatedAt);
    H.renderKpis(kpiHost, section.kpis || [], "");
    var stableRows =
      (section.rows_full && section.rows_full.length ? section.rows_full : section.rows) || [];

    H.renderTable(theadRow, tbody, STABLE_HOME_COLS, stableRows, {
      emptyMsg: "Stablecoins network preview is unavailable.",
      homePreview: true,
      previewLimit: HOME_PREVIEW,
      searchInputId: "js-home-stable-search",
      toolbarId: "js-home-stable-toolbar",
      previewEntity: "networks",
      linkAria: "Open network on RWA.xyz",
    });

    if (typeof H.attachHomePreviewFullscreen === "function") {
      H.attachHomePreviewFullscreen(tbody, {
        title: "Stablecoins networks preview",
        filename: "stablecoins-networks-preview",
        exportColumns: STABLE_HOME_COLS,
      });
    }
  }

  function renderTmmfHome(exploreSection, mmfPage, generatedAt) {
    var kpiHost = document.getElementById("js-home-tmmf-kpi");
    var theadRow = document.getElementById("js-home-tmmf-thead-row");
    var tbody = document.getElementById("js-home-tmmf-tbody");
    var captionEl = document.getElementById("js-home-tmmf-caption");
    var fundsTable = mmfPage && mmfPage.funds_table;

    if (fundsTable && fundsTable.columns && fundsTable.rows_full && fundsTable.rows_full.length) {
      showBanner("js-home-tmmf-banner", mmfPage.error || "");
      renderFreshness("js-home-tmmf-as-of", mmfPage.generated_at || generatedAt);
      H.renderKpis(kpiHost, (mmfPage.kpis || exploreSection && exploreSection.kpis) || [], "");
      if (captionEl) {
        captionEl.textContent =
          "Curated fund population preview. Population may not include all TMMFs in the market.";
      }
      H.renderTable(theadRow, tbody, TMMF_FUND_COLS, fundsTable.rows_full, {
        emptyMsg: "TMMF fund preview is unavailable.",
        homePreview: true,
        previewLimit: HOME_PREVIEW,
        searchInputId: "js-home-tmmf-search",
        toolbarId: "js-home-tmmf-toolbar",
        previewEntity: "funds",
        linkAria: "Open fund on RWA.xyz",
      });
      if (typeof H.attachHomePreviewFullscreen === "function") {
        H.attachHomePreviewFullscreen(tbody, {
          title: "Tokenized money market funds preview",
          filename: "tmmf-funds-preview",
          exportColumns: TMMF_FUND_COLS,
        });
      }
      return;
    }

    if (!exploreSection) {
      showBanner("js-home-tmmf-banner", "TMMF preview data is unavailable.");
      if (kpiHost) kpiHost.innerHTML = "";
      if (tbody) tbody.innerHTML = '<tr><td colspan="5">TMMF data is unavailable.</td></tr>';
      return;
    }

    showBanner("js-home-tmmf-banner", "");
    renderFreshness("js-home-tmmf-as-of", generatedAt);
    H.renderKpis(kpiHost, exploreSection.kpis || [], "");
    if (captionEl) {
      captionEl.textContent = "Network preview (fund-level table on full TMMF page).";
    }
    var netRows =
      (exploreSection.rows_full && exploreSection.rows_full.length
        ? exploreSection.rows_full
        : exploreSection.rows) || [];
    H.renderTable(theadRow, tbody, TMMF_NET_COLS, netRows, {
      emptyMsg: "TMMF network preview is unavailable.",
      homePreview: true,
      previewLimit: HOME_PREVIEW,
      searchInputId: "js-home-tmmf-search",
      toolbarId: "js-home-tmmf-toolbar",
      previewEntity: "networks",
      linkAria: "Open network on RWA.xyz",
    });
    if (typeof H.attachHomePreviewFullscreen === "function") {
      H.attachHomePreviewFullscreen(tbody, {
        title: "Tokenized MMF networks preview",
        filename: "tmmf-networks-preview",
        exportColumns: TMMF_NET_COLS,
      });
    }
  }

  Promise.all([
    loadTimed("rwa_explore_asset_type.json", 12000).catch(function () {
      return null;
    }),
    loadTimed("rwa_tokenized_mmf.json", 12000).catch(function () {
      return null;
    }),
  ]).then(function (results) {
    var explore = results[0];
    var mmfPage = results[1];
    var generatedAt =
      (explore && explore.generated_at) ||
      (mmfPage && mmfPage.generated_at) ||
      (explore && explore.footer_note) ||
      null;
    renderStablecoinsHome(explore, generatedAt);
    renderTmmfHome(findSection(explore, "tokenized_mmf"), mmfPage, generatedAt);
  });
})();
