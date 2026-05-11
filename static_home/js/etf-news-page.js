(function () {
  var PAGE = 20;
  var all = [];
  var filtered = [];
  var page = 0;
  var listEl = document.getElementById("js-etf-news-list");
  var searchEl = document.getElementById("js-etf-news-search");
  var metaEl = document.getElementById("js-etf-news-meta");
  var navEl = document.getElementById("js-etf-news-nav");
  var banner = document.getElementById("js-data-banner");

  function applyFilter() {
    var q = (searchEl && searchEl.value ? searchEl.value : "").trim().toLowerCase();
    if (!q) {
      filtered = all.slice();
    } else {
      filtered = all.filter(function (a) {
        var blob = (
          (a.title || "") +
          " " +
          (a.summary || "") +
          " " +
          (a.source || "")
        ).toLowerCase();
        return blob.indexOf(q) >= 0;
      });
    }
    page = 0;
    render();
  }

  function render() {
    if (!listEl) return;
    var sorted = sortArticlesByPublishedDesc(filtered);
    var start = page * PAGE;
    var slice = sorted.slice(start, start + PAGE);
    renderArticleFeedByDay(listEl, slice, {
      includeCountry: false,
      emptyMessage: "No headlines match. Clear search and try again.",
      emptyClass: "article-feed-empty",
    });
    if (metaEl) {
      metaEl.textContent =
        "Showing " +
        (sorted.length ? start + 1 : 0) +
        "–" +
        Math.min(start + slice.length, sorted.length) +
        " of " +
        sorted.length +
        " (grouped by day · filtered from " +
        all.length +
        " total)";
    }
    if (navEl) {
      var np = Math.max(1, Math.ceil(sorted.length / PAGE));
      navEl.innerHTML =
        '<button type="button" class="btn btn-nav" id="etf-prev" ' +
        (page <= 0 ? "disabled" : "") +
        ">Previous</button>" +
        '<span class="etf-news-page-num">Page ' +
        (page + 1) +
        " / " +
        np +
        "</span>" +
        '<button type="button" class="btn btn-nav" id="etf-next" ' +
        (page >= np - 1 ? "disabled" : "") +
        ">Next</button>";
      var prev = document.getElementById("etf-prev");
      var next = document.getElementById("etf-next");
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
    if (searchEl) {
      searchEl.addEventListener("input", applyFilter);
    }
    loadJson("etf_news.json")
      .then(function (data) {
        all = data.items || [];
        filtered = all.slice();
        render();
      })
      .catch(function () {
        if (banner) {
          banner.hidden = false;
          banner.textContent =
            "Could not load etf_news.json.";
        }
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
