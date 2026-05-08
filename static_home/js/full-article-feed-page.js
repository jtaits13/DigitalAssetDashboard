/**
 * Full article list UI (mirrors etf-news-page.js): load JSON export, search, paginate.
 * Configure via body: data-article-feed="all_articles.json" | "all_regulatory.json"
 * and optional data-article-feed-country="1" to show country in meta + search.
 */
(function () {
  var PAGE = 25;
  var all = [];
  var filtered = [];
  var page = 0;

  function cfg() {
    var b = document.body;
    return {
      feed: (b && b.getAttribute("data-article-feed") || "all_articles.json").trim(),
      includeCountry: b && b.getAttribute("data-article-feed-country") === "1",
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

  function metaLine(a) {
    var c = cfg();
    var parts = [a.source || "", c.includeCountry && a.country ? a.country : "", fmtDate(a.published) || ""].filter(
      Boolean
    );
    return parts.join(" · ");
  }

  function render() {
    var listEl = document.getElementById("js-article-feed-list");
    var metaEl = document.getElementById("js-article-feed-meta");
    var navEl = document.getElementById("js-article-feed-nav");
    if (!listEl) return;
    var start = page * PAGE;
    var slice = filtered.slice(start, start + PAGE);
    listEl.innerHTML = "";
    if (!slice.length) {
      listEl.innerHTML =
        '<li class="etf-news-empty">No headlines match. Clear search or re-run data export.</li>';
    } else {
      slice.forEach(function (a) {
        var li = document.createElement("li");
        li.className = "etf-news-item";
        var href = a.link || "#";
        li.innerHTML =
          '<a class="etf-news-title" href="' +
          escapeHtml(href) +
          '" target="_blank" rel="noopener noreferrer">' +
          escapeHtml(a.title || "Untitled") +
          "</a>" +
          '<div class="etf-news-meta">' +
          escapeHtml(metaLine(a)) +
          "</div>";
        if (a.summary) {
          li.innerHTML +=
            '<p class="etf-news-sum">' + escapeHtml(a.summary.substring(0, 280)) + "</p>";
        }
        listEl.appendChild(li);
      });
    }
    if (metaEl) {
      metaEl.textContent =
        "Showing " +
        (filtered.length ? start + 1 : 0) +
        "–" +
        Math.min(start + slice.length, filtered.length) +
        " of " +
        filtered.length +
        " (filtered from " +
        all.length +
        " in export)";
    }
    if (navEl) {
      var np = Math.max(1, Math.ceil(filtered.length / PAGE));
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
            ". Deploy from CI (export script) or run scripts/export_static_site_data.py locally.";
        }
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
