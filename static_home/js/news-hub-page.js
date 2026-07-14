/**
 * Unified news hub: lane filters (digital / etf / regulatory / custody) + magazine layout.
 * URL: news.html?lane=digital|etf|regulatory|custody  (also accepts legacy hash #regulatory etc.)
 */
(function () {
  var PAGE_SIZE = 18;
  var FEATURE_COUNT = 3;

  var LANES = {
    digital: {
      id: "digital",
      feed: "all_articles.json",
      badge: "NEWS",
      title: "Digital asset news",
      dek:
        "Curated headlines from <strong>CoinDesk</strong> and <strong>The Block</strong> — " +
        "duplicates collapsed, up to eight stories per day. Built to scan like a newsroom, filtered for digital assets.",
      searchPlaceholder: "Search title, summary, or source…",
      includeCountry: false,
      includeAccess: false,
      empty: "No digital-asset headlines match. Try another lane or clear search.",
    },
    etf: {
      id: "etf",
      feed: "etf_news.json",
      badge: "ETP",
      title: "ETF &amp; ETP news",
      dek:
        "Crypto and finance headlines focused on exchange-traded products — flows, filings, approvals, and issuers. " +
        "Up to five ranked stories per UTC day.",
      searchPlaceholder: "Search ETF/ETP headlines…",
      includeCountry: false,
      includeAccess: false,
      empty: "No ETF/ETP headlines match. Try another lane or clear search.",
    },
    regulatory: {
      id: "regulatory",
      feed: "all_regulatory.json",
      badge: "NEWS",
      title: "Regulatory &amp; policy news",
      dek:
        "Regulator, central-bank, and policy coverage for digital assets. " +
        "Up to five ranked stories per UTC day — filter by country in search when relevant.",
      searchPlaceholder: "Search title, summary, source, or country…",
      includeCountry: true,
      includeAccess: false,
      empty: "No regulatory headlines match. Try another lane or clear search.",
    },
    custody: {
      id: "custody",
      feed: "all_custodian_news.json",
      badge: "NEWS",
      title: "Custody news",
      dek:
        "Digital-asset custody and infrastructure coverage from Global Custodian and related sources. " +
        "Access badges are best-effort (Free / Subscriber / Check site).",
      searchPlaceholder: "Search title, summary, source, or category…",
      includeCountry: false,
      includeAccess: true,
      empty: "No custody headlines match. Try another lane or clear search.",
    },
  };

  var cache = {};
  var laneId = "digital";
  var all = [];
  var filtered = [];
  var page = 0;

  function esc(s) {
    return typeof escapeHtml === "function" ? escapeHtml(s) : String(s || "");
  }

  function readLaneFromUrl() {
    try {
      var u = new URL(window.location.href);
      var q = (u.searchParams.get("lane") || "").trim().toLowerCase();
      if (LANES[q]) return q;
      var h = (u.hash || "").replace(/^#/, "").toLowerCase();
      if (h === "regulatory" || h === "custody" || h === "etf" || h === "digital") return h;
      if (h === "etp") return "etf";
    } catch (_e) {}
    var bodyLane = (document.body.getAttribute("data-news-lane") || "").trim().toLowerCase();
    if (LANES[bodyLane]) return bodyLane;
    return "digital";
  }

  def writeLaneToUrl(id) {
    try {
      if (!window.location || window.location.protocol === "about:") return;
      var u = new URL(window.location.href);
      u.searchParams.set("lane", id);
      u.hash = "";
      history.replaceState(null, "", u.pathname + u.search + (u.hash || ""));
    } catch (_e) {}
  }

  function lane() {
    return LANES[laneId] || LANES.digital;
  }

  function snip(text, max) {
    var t = String(text || "").trim();
    if (!t) return "";
    if (t.length <= max) return t;
    return t.substring(0, max).replace(/\s+\S*$/, "") + "…";
  }

  function metaLine(a, c) {
    var parts = [
      a.source || "",
      c.includeCountry && a.country ? a.country : "",
      a.category || "",
      typeof fmtTimeOnly === "function" ? fmtTimeOnly(a.published) || "" : "",
    ].filter(Boolean);
    return parts.join(" · ");
  }

  function accessHtml(a, c) {
    if (!c.includeAccess || typeof articleAccessBadgeHtml !== "function") return "";
    return articleAccessBadgeHtml(a.access);
  }

  function setActiveLaneButtons() {
    document.querySelectorAll(".news-hub-lanes__btn").forEach(function (btn) {
      var on = btn.getAttribute("data-lane") === laneId;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
    document.body.classList.remove("lane-digital", "lane-etf", "lane-regulatory", "lane-custody");
    document.body.classList.add("lane-" + laneId);
    var zone = document.querySelector(".inner-rich-zone.zone--news, .inner-rich-zone.zone--etp");
    if (zone) {
      zone.classList.toggle("zone--etp", laneId === "etf");
      zone.classList.toggle("zone--news", laneId !== "etf");
      zone.classList.toggle("home-zone--etp", laneId === "etf");
      zone.classList.toggle("home-zone--news", laneId !== "etf");
    }
    document.body.classList.toggle("page-etp", laneId === "etf");
  }

  function updateChrome() {
    var c = lane();
    var titleEl = document.getElementById("js-news-hub-title");
    var dekEl = document.getElementById("js-news-hub-dek");
    var badgeEl = document.getElementById("js-news-hub-badge");
    var searchEl = document.getElementById("js-article-feed-search");
    if (titleEl) titleEl.innerHTML = c.title;
    if (dekEl) dekEl.innerHTML = c.dek;
    if (badgeEl) badgeEl.textContent = c.badge;
    if (searchEl) searchEl.setAttribute("placeholder", c.searchPlaceholder);
    document.title = titleEl
      ? titleEl.textContent + " — Digital Assets Dashboard"
      : "News — Digital Assets Dashboard";
    setActiveLaneButtons();
  }

  function storyRowHtml(a, c) {
    var href = a.link || "#";
    var title = esc(a.title || "Untitled");
    var dek = snip(a.summary || "", 200);
    var meta = metaLine(a, c);
    var access = accessHtml(a, c);
    return (
      '<li class="news-hub-story">' +
      '<a class="news-hub-story__link" href="' +
      esc(href) +
      '" target="_blank" rel="noopener noreferrer">' +
      '<p class="news-hub-story__title">' +
      title +
      "</p>" +
      (dek ? '<p class="news-hub-story__dek">' + esc(dek) + "</p>" : "") +
      '<div class="news-hub-story__meta">' +
      access +
      esc(meta) +
      "</div>" +
      '<span class="news-hub-story__go" aria-hidden="true">Read →</span>' +
      "</a></li>"
    );
  }

  function featureHtml(items, c) {
    if (!items.length) return "";
    var lead = items[0];
    var side = items.slice(1, FEATURE_COUNT);
    var leadHref = lead.link || "#";
    var leadDek = snip(lead.summary || "", 280);
    var html =
      '<a class="news-hub-lead" href="' +
      esc(leadHref) +
      '" target="_blank" rel="noopener noreferrer">' +
      '<span class="news-hub-lead__kicker">Lead story</span>' +
      '<h2 class="news-hub-lead__title">' +
      esc(lead.title || "Untitled") +
      "</h2>" +
      (leadDek ? '<p class="news-hub-lead__dek">' + esc(leadDek) + "</p>" : "") +
      '<div class="news-hub-lead__meta">' +
      accessHtml(lead, c) +
      "<span>" +
      esc(metaLine(lead, c)) +
      "</span>" +
      '<span class="news-hub-lead__cta">Read story →</span>' +
      "</div></a>";

    if (side.length) {
      html += '<div class="news-hub-side">';
      side.forEach(function (a) {
        var dek = snip(a.summary || "", 160);
        html +=
          '<a class="news-hub-side__card" href="' +
          esc(a.link || "#") +
          '" target="_blank" rel="noopener noreferrer">' +
          '<p class="news-hub-side__title">' +
          esc(a.title || "Untitled") +
          "</p>" +
          (dek ? '<p class="news-hub-side__dek">' + esc(dek) + "</p>" : "") +
          '<div class="news-hub-side__meta">' +
          accessHtml(a, c) +
          esc(metaLine(a, c)) +
          "</div></a>";
      });
      html += "</div>";
    }
    return html;
  }

  function listByDayHtml(items, c) {
    if (!items.length) {
      return '<p class="article-feed-empty">' + esc(c.empty) + "</p>";
    }
    var prevKey = null;
    var html = "";
    var ulOpen = false;
    items.forEach(function (a) {
      var key = typeof articleDateKey === "function" ? articleDateKey(a.published) : "day";
      if (key !== prevKey) {
        if (ulOpen) html += "</ul></section>";
        prevKey = key;
        var label =
          typeof articleDayHeading === "function" ? articleDayHeading(a.published) : String(key);
        html +=
          '<section class="news-hub-day">' +
          '<h3 class="news-hub-day__label">' +
          esc(label) +
          "</h3>" +
          '<ul class="news-hub-stories">';
        ulOpen = true;
      }
      html += storyRowHtml(a, c);
    });
    if (ulOpen) html += "</ul></section>";
    return html;
  }

  function applyFilter() {
    var el = document.getElementById("js-article-feed-search");
    var c = lane();
    var q = (el && el.value ? el.value : "").trim().toLowerCase();
    if (!q) {
      filtered = all.slice();
    } else {
      filtered = all.filter(function (a) {
        var blob =
          (a.title || "") +
          " " +
          (a.summary || "") +
          " " +
          (a.source || "") +
          (c.includeCountry ? " " + (a.country || "") : "") +
          (c.includeAccess ? " " + (a.access || "") + " " + (a.category || "") : "");
        return blob.toLowerCase().indexOf(q) >= 0;
      });
    }
    page = 0;
    render();
  }

  function render() {
    var featureEl = document.getElementById("js-news-hub-feature");
    var listEl = document.getElementById("js-article-feed-list");
    var metaEl = document.getElementById("js-article-feed-meta");
    var navEl = document.getElementById("js-article-feed-nav");
    var latestHead = document.getElementById("js-news-hub-latest-head");
    if (!listEl) return;
    var c = lane();
    var sorted =
      typeof sortArticlesByPublishedDesc === "function"
        ? sortArticlesByPublishedDesc(filtered)
        : filtered.slice();

    var start;
    var slice;
    var featureItems = [];
    var listItems;

    if (page === 0) {
      featureItems = sorted.slice(0, FEATURE_COUNT);
      var rest = sorted.slice(FEATURE_COUNT);
      var listBudget = Math.max(0, PAGE_SIZE - featureItems.length);
      listItems = rest.slice(0, listBudget);
      start = 0;
      if (featureEl) {
        featureEl.hidden = !featureItems.length;
        featureEl.innerHTML = featureHtml(featureItems, c);
      }
      if (latestHead) latestHead.hidden = !listItems.length && !featureItems.length;
    } else {
      var offset = FEATURE_COUNT + (page - 1) * PAGE_SIZE;
      // page 1+ uses full PAGE_SIZE from remaining after features on page 0
      var afterFeature = Math.max(0, sorted.length - FEATURE_COUNT);
      var page0List = Math.max(0, Math.min(PAGE_SIZE - Math.min(FEATURE_COUNT, sorted.length), afterFeature));
      start = FEATURE_COUNT + page0List + (page - 1) * PAGE_SIZE;
      listItems = sorted.slice(start, start + PAGE_SIZE);
      featureItems = [];
      if (featureEl) {
        featureEl.hidden = true;
        featureEl.innerHTML = "";
      }
      if (latestHead) latestHead.hidden = !listItems.length;
    }

    listEl.innerHTML = listByDayHtml(listItems, c);

    var shownStart = page === 0 ? (sorted.length ? 1 : 0) : start + 1;
    var shownEnd =
      page === 0
        ? Math.min(featureItems.length + listItems.length, sorted.length)
        : Math.min(start + listItems.length, sorted.length);

    if (metaEl) {
      metaEl.textContent =
        "Showing " +
        shownStart +
        "–" +
        shownEnd +
        " of " +
        sorted.length +
        " · " +
        all.length +
        " in this lane";
    }

    if (navEl) {
      var remainingAfter0 =
        Math.max(0, sorted.length - FEATURE_COUNT - Math.max(0, PAGE_SIZE - Math.min(FEATURE_COUNT, sorted.length)));
      var extraPages = Math.ceil(remainingAfter0 / PAGE_SIZE);
      var np = 1 + Math.max(0, extraPages);
      if (sorted.length <= FEATURE_COUNT) np = 1;
      navEl.innerHTML =
        '<button type="button" class="btn btn-nav" id="article-feed-prev" ' +
        (page <= 0 ? "disabled" : "") +
        ">Previous</button>" +
        '<span class="etf-news-page-num">Page ' +
        (page + 1) +
        " / " +
        np +
        "</span>" +
        '<button type="button" class="btn btn-nav" id="article-feed-next" ' +
        (page >= np - 1 ? "disabled" : "") +
        ">Next</button>";
      var prev = document.getElementById("article-feed-prev");
      var next = document.getElementById("article-feed-next");
      if (prev)
        prev.onclick = function () {
          if (page > 0) {
            page--;
            render();
            window.scrollTo({ top: 0, behavior: "smooth" });
          }
        };
      if (next)
        next.onclick = function () {
          if (page < np - 1) {
            page++;
            render();
            window.scrollTo({ top: 0, behavior: "smooth" });
          }
        };
    }
  }

  function loadLane(id, opts) {
    opts = opts || {};
    if (!LANES[id]) id = "digital";
    laneId = id;
    writeLaneToUrl(id);
    updateChrome();
    var c = lane();
    var banner = document.getElementById("js-data-banner");
    var searchEl = document.getElementById("js-article-feed-search");
    if (searchEl && !opts.keepSearch) searchEl.value = "";

    function accept(items) {
      all = items || [];
      filtered = all.slice();
      page = 0;
      applyFilter();
    }

    if (cache[c.feed]) {
      accept(cache[c.feed]);
      return;
    }

    if (typeof loadJson !== "function") {
      if (banner) {
        banner.hidden = false;
        banner.textContent = "News hub scripts failed to load.";
      }
      return;
    }

    loadJson(c.feed)
      .then(function (data) {
        cache[c.feed] = data.items || [];
        accept(cache[c.feed]);
      })
      .catch(function () {
        if (banner) {
          banner.hidden = false;
          banner.textContent = "Could not load " + c.feed + ".";
        }
        accept([]);
      });
  }

  function init() {
    laneId = readLaneFromUrl();
    document.querySelectorAll(".news-hub-lanes__btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-lane");
        if (id && id !== laneId) loadLane(id);
      });
    });
    var searchEl = document.getElementById("js-article-feed-search");
    if (searchEl) searchEl.addEventListener("input", applyFilter);
    loadLane(laneId, { keepSearch: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
