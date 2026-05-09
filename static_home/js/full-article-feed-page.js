/**
 * Full article list UI: load JSON export, search, paginate, group by local calendar day.
 * Configure via body: data-article-feed="all_articles.json" | "all_regulatory.json"
 * and optional data-article-feed-country="1" to show country in meta + search.
 */
(function () {
  var DEFAULT_PAGE_SIZE = 20;
  var all = [];
  var filtered = [];
  var page = 0;

  function cfg() {
    var b = document.body;
    var pz = parseInt((b && b.getAttribute("data-article-feed-page-size")) || String(DEFAULT_PAGE_SIZE), 10);
    var mp = parseInt((b && b.getAttribute("data-article-feed-max-pages")) || "0", 10);
    return {
      feed: (b && b.getAttribute("data-article-feed") || "all_articles.json").trim(),
      includeCountry: b && b.getAttribute("data-article-feed-country") === "1",
      pageSize: pz > 0 ? pz : DEFAULT_PAGE_SIZE,
      maxPages: mp > 0 ? mp : null,
    };
  }

  function applyFilter() {
    var el = document.getElementById("js-article-feed-search");
    var c = cfg();
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
          (c.includeCountry ? " " + (a.country || "") : "");
        return blob.toLowerCase().indexOf(q) >= 0;
      });
    }
    page = 0;
    render();
  }

  function render() {
    var listEl = document.getElementById("js-article-feed-list");
    var metaEl = document.getElementById("js-article-feed-meta");
    var navEl = document.getElementById("js-article-feed-nav");
    if (!listEl) return;
    var c = cfg();
    var PAGE = c.pageSize;
    var sorted = sortArticlesByPublishedDesc(filtered);
    var maxIdx = sorted.length;
    if (c.maxPages) {
      maxIdx = Math.min(maxIdx, PAGE * c.maxPages);
    }
    var sortedLimited = sorted.slice(0, maxIdx);
    var start = page * PAGE;
    var slice = sortedLimited.slice(start, start + PAGE);
    renderArticleFeedByDay(listEl, slice, {
      includeCountry: c.includeCountry,
      emptyMessage: "No headlines match. Clear search or re-run data export.",
      emptyClass: "article-feed-empty",
    });
    if (metaEl) {
      var denom = sortedLimited.length;
      var pageNote = c.maxPages ? " · max " + c.maxPages + " pages" : "";
      metaEl.textContent =
        "Showing " +
        (denom ? start + 1 : 0) +
        "–" +
        Math.min(start + slice.length, denom) +
        " of " +
        denom +
        " (grouped by day · filtered from " +
        all.length +
        " in export)" +
        pageNote;
    }
    if (navEl) {
      var np = Math.max(1, Math.ceil(sortedLimited.length / PAGE));
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
        prev.addEventListener("click", function () {
          if (page > 0) {
            page--;
            render();
          }
        });
      if (next)
        next.addEventListener("click", function () {
          if (page < np - 1) {
            page++;
            render();
          }
        });
    }
  }

  function init() {
    var searchEl = document.getElementById("js-article-feed-search");
    var banner = document.getElementById("js-data-banner");
    var c = cfg();
    if (searchEl) {
      searchEl.addEventListener("input", applyFilter);
    }
    loadJson(c.feed)
      .then(function (data) {
        all = data.items || [];
        filtered = all.slice();
        render();
      })
      .catch(function () {
        if (banner) {
          banner.hidden = false;
          banner.textContent =
            "Could not load " +
            c.feed +
            ". Open the published site after deploy, or run scripts/export_static_site_data.py locally.";
        }
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
