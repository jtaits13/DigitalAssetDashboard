(function () {
  var PAGE = 25;
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
          escapeHtml(a.source || "") +
          " · " +
          escapeHtml(fmtDate(a.published) || "") +
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
            "Could not load etf_news.json. Deploy GitHub Pages from CI (runs export) or run scripts/export_static_site_data.py locally.";
        }
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
