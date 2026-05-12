/**
 * Resolve /repo/ base for GitHub project pages and load JSON from static_home/data/.
 * Also resolves ``data/*.json`` and assets from the deployed ``js/static-base.js`` URL when possible,
 * so JSON loads even when ``location.pathname`` is wrong (trailing slashes, pretty URLs).
 */
(function (global) {
  /** e.g. ``data/rwa_stablecoins.json`` → absolute URL sibling to ``js/static-base.js``. */
  function resolvedUrlAgainstStaticHome(relFromSiteRoot) {
    var r = relFromSiteRoot != null ? String(relFromSiteRoot).replace(/^\.\//, "").trim() : "";
    if (!r || /^https?:\/\//i.test(r) || r.charAt(0) === "/") return "";
    var scripts = document.getElementsByTagName("script");
    for (var i = scripts.length - 1; i >= 0; i--) {
      var raw = (scripts[i].src || "").replace(/\\/g, "/");
      if (!/\/static-base\.js(\?|#|$)/i.test(raw)) continue;
      try {
        var baseDir = raw.slice(0, raw.lastIndexOf("/") + 1);
        return new URL("../" + r.replace(/^\/+/, ""), baseDir).href;
      } catch (e) {
        continue;
      }
    }
    return "";
  }

  function basePath() {
    var p = window.location.pathname || "/";
    while (p.length > 1 && p.endsWith("/")) {
      p = p.slice(0, -1);
    }
    if (p.endsWith("/index.html")) return p.slice(0, -"index.html".length);
    if (p.endsWith("/etf-news.html")) return p.slice(0, -"etf-news.html".length);
    if (p.endsWith("/all-articles.html")) return p.slice(0, -"all-articles.html".length);
    if (p.endsWith("/all-regulatory.html")) return p.slice(0, -"all-regulatory.html".length);
    if (p.endsWith("/etps.html")) return p.slice(0, -"etps.html".length);
    if (p.endsWith("/rwa-global.html")) return p.slice(0, -"rwa-global.html".length);
    if (p.endsWith("/rwa-explore-market-participant.html"))
      return p.slice(0, -"rwa-explore-market-participant.html".length);
    if (p.endsWith("/rwa-participants-networks.html")) return p.slice(0, -"rwa-participants-networks.html".length);
    if (p.endsWith("/rwa-participants-platforms.html")) return p.slice(0, -"rwa-participants-platforms.html".length);
    if (p.endsWith("/rwa-participants-asset-managers.html"))
      return p.slice(0, -"rwa-participants-asset-managers.html".length);
    if (p.endsWith("/rwa-stablecoins.html")) return p.slice(0, -"rwa-stablecoins.html".length);
    if (p.endsWith("/rwa-us-treasuries.html")) return p.slice(0, -"rwa-us-treasuries.html".length);
    if (p.endsWith("/rwa-tokenized-stocks.html")) return p.slice(0, -"rwa-tokenized-stocks.html".length);
    if (p.endsWith("/")) return p;
    // ``/repo-name`` with no trailing slash: treat as directory so ``rwa-global.html`` does not resolve to site root.
    if (/^\/[^/]+$/.test(p)) return p + "/";
    return p.replace(/\/[^/]+$/, "/");
  }

  /** Absolute path from server root for static hub assets (works on GitHub project Pages). */
  function assetUrl(rel) {
    var s = rel != null ? String(rel).trim() : "";
    if (!s) return s;
    if (/^https?:\/\//i.test(s)) return s;
    if (s.charAt(0) === "/") return s;
    var abs = resolvedUrlAgainstStaticHome(s.replace(/^\.\//, ""));
    return abs || basePath() + s.replace(/^\.\//, "");
  }

  function dataUrl(name) {
    var n = String(name || "").trim().replace(/^\/+/, "");
    var abs = resolvedUrlAgainstStaticHome("data/" + n);
    return abs || basePath() + "data/" + n;
  }

  global.__STATIC = { basePath: basePath, assetUrl: assetUrl, dataUrl: dataUrl };

  /**
   * Fix relative hub ``*.html`` links under a subtree (injected HTML runs after DOMContentLoaded,
   * so Project Pages ``/repo`` without trailing slash would otherwise resolve beside the hostname).
   */
  function finalizeHubAnchors(scope) {
    var fn =
      global.__STATIC && typeof global.__STATIC.assetUrl === "function"
        ? global.__STATIC.assetUrl
        : null;
    if (!fn || typeof scope.querySelectorAll !== "function") return;
    scope.querySelectorAll("a[href]").forEach(function (a) {
      var raw = (a.getAttribute("href") || "").trim();
      if (!raw || /^https?:\/\//i.test(raw) || raw.charAt(0) === "#") return;
      var hashIx = raw.indexOf("#");
      var pathPart = hashIx >= 0 ? raw.slice(0, hashIx) : raw;
      var hashPart = hashIx >= 0 ? raw.slice(hashIx) : "";
      pathPart = pathPart.replace(/^\.\//, "");
      if (pathPart.indexOf("/") !== -1 || pathPart.indexOf(":") !== -1) return;
      if (!/\.html$/i.test(pathPart)) return;
      a.setAttribute("href", fn(pathPart) + hashPart);
    });
  }

  global.finalizeHubAnchors = finalizeHubAnchors;
  function fixStaticHubHtmlAnchors() {
    if (typeof document === "undefined") return;
    var run = function () {
      var pairs = [
        ["rwa-global.html", "rwa-global.html"],
        ["rwa-explore-asset-type.html", "rwa-explore-asset-type.html"],
        ["rwa-explore-market-participant.html", "rwa-explore-market-participant.html"],
        ["rwa-participants-networks.html", "rwa-participants-networks.html"],
        ["rwa-participants-platforms.html", "rwa-participants-platforms.html"],
        ["rwa-participants-asset-managers.html", "rwa-participants-asset-managers.html"],
        ["rwa-stablecoins.html", "rwa-stablecoins.html"],
        ["rwa-us-treasuries.html", "rwa-us-treasuries.html"],
        ["rwa-tokenized-stocks.html", "rwa-tokenized-stocks.html"],
        ["all-articles.html", "all-articles.html"],
        ["all-regulatory.html", "all-regulatory.html"],
      ];
      pairs.forEach(function (p) {
        var abs = assetUrl(p[1]);
        document.querySelectorAll('a[href="' + p[0] + '"]').forEach(function (a) {
          a.setAttribute("href", abs);
        });
      });
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
    else run();
  }
  fixStaticHubHtmlAnchors();

  global.loadJson = function (name) {
    var url = dataUrl(name);
    return fetch(url, {
      credentials: "same-origin",
      cache: "no-store",
    }).then(function (r) {
      if (!r.ok) throw new Error("Failed to load " + name + " (" + url + "): " + r.status);
      return r.json();
    });
  };

  global.escapeHtml = function (s) {
    if (s == null) return "";
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  };

  /** Fill ``.ticker-strip`` from ``crypto_ticker.json``. */
  function hydrateStaticCryptoTicker(payload) {
    if (!payload || typeof document === "undefined") return;
    var strips = document.querySelectorAll(".ticker-strip");
    var si = 0;
    for (; si < strips.length; si++) {
      var strip = strips[si];
      var layout = strip.querySelector(".ticker-strip__layout");
      if (!layout) continue;
      var lab = strip.querySelector(".ticker-strip__label");
      var chips = null;
      var k = 0;
      var kids = layout.children;
      for (; k < kids.length; k++) {
        if (kids[k].classList && kids[k].classList.contains("ticker-strip__chips")) {
          chips = kids[k];
          break;
        }
      }
      if (!chips) continue;
      if (lab && payload.banner_title) lab.textContent = payload.banner_title;
      if (payload.chips_inner_html) chips.innerHTML = payload.chips_inner_html;
      if (typeof global.finalizeHubAnchors === "function") {
        global.finalizeHubAnchors(strip);
      }
    }
  }

  function initCryptoTickerMarquee() {
    if (typeof document === "undefined") return;
    var strips = document.querySelectorAll(".ticker-strip");
    var si = 0;
    for (; si < strips.length; si++) {
      var strip = strips[si];
      if (!strip || strip.getAttribute("data-ticker-marquee") === "1") continue;
      var layout = strip.querySelector(".ticker-strip__layout");
      if (!layout) continue;
      var chips = null;
      var k = 0;
      var kids = layout.children;
      for (; k < kids.length; k++) {
        if (kids[k].classList && kids[k].classList.contains("ticker-strip__chips")) {
          chips = kids[k];
          break;
        }
      }
      if (!chips) continue;

      strip.setAttribute("data-ticker-marquee", "1");

      chips.classList.add("ticker-strip__drum");

      var viewport = document.createElement("div");
      viewport.className = "ticker-strip__viewport";
      var move = document.createElement("div");
      move.className = "ticker-strip__move";
      move.appendChild(chips);
      var drumB = chips.cloneNode(true);
      drumB.setAttribute("aria-hidden", "true");
      drumB.classList.add("ticker-strip__chips--marquee-clone");
      move.appendChild(drumB);
      viewport.appendChild(move);
      layout.appendChild(viewport);
    }
  }

  function bootStaticCryptoTicker() {
    if (typeof document === "undefined") return;
    var run = function () {
      global
        .loadJson("crypto_ticker.json")
        .then(function (data) {
          hydrateStaticCryptoTicker(data);
          initCryptoTickerMarquee();
        })
        .catch(function () {
          initCryptoTickerMarquee();
        });
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
    else run();
  }
  bootStaticCryptoTicker();

  global.fmtDate = function (iso) {
    if (!iso) return "—";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      return d.toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (e) {
      return iso;
    }
  };

  /** Time of day only (date is shown in the day group heading on full feed pages). */
  global.fmtTimeOnly = function (iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return "";
      return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
    } catch (e) {
      return "";
    }
  };

  /** Local calendar day key for grouping (YYYY-MM-DD), or ``_none`` if unparsable. */
  global.articleDateKey = function (iso) {
    if (!iso) return "_none";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "_none";
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1);
    if (m.length === 1) m = "0" + m;
    var day = String(d.getDate());
    if (day.length === 1) day = "0" + day;
    return y + "-" + m + "-" + day;
  };

  /** Section title: Today / Yesterday / full weekday date / Date unknown. */
  global.articleDayHeading = function (iso) {
    if (!iso) return "Date unknown";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "Date unknown";
    var today = new Date();
    var startToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    var startThat = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    var diffDays = Math.round((startToday - startThat) / 86400000);
    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    return d.toLocaleDateString(undefined, {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  global.sortArticlesByPublishedDesc = function (items) {
    if (!items || !items.length) return [];
    return items.slice().sort(function (a, b) {
      var ta = new Date(a && a.published).getTime();
      var tb = new Date(b && b.published).getTime();
      if (isNaN(ta)) ta = 0;
      if (isNaN(tb)) tb = 0;
      return tb - ta;
    });
  };

  /**
   * Full feed pages: render items grouped by local day, with card layout.
   * ``options.includeCountry``: regulatory meta. ``options.emptyMessage`` / ``emptyClass`` for zero state.
   */
  global.renderArticleFeedByDay = function (container, items, options) {
    options = options || {};
    var emptyMsg =
      options.emptyMessage != null
        ? options.emptyMessage
        : "No headlines match. Clear search and try again.";
    var emptyClass = options.emptyClass || "article-feed-empty";
    var includeCountry = !!options.includeCountry;
    var esc = global.escapeHtml;
    if (!container) return;
    container.innerHTML = "";
    if (!items || !items.length) {
      var p = document.createElement("p");
      p.className = emptyClass;
      p.textContent = emptyMsg;
      container.appendChild(p);
      return;
    }
    var prevKey = null;
    var ul = null;
    var section = null;
    var nDay = 0;
    items.forEach(function (a) {
      var key = global.articleDateKey(a.published);
      if (key !== prevKey) {
        prevKey = key;
        nDay++;
        section = document.createElement("section");
        section.className = "article-feed-day";
        var h = document.createElement("h2");
        h.className = "article-feed-day__label";
        h.id = "article-feed-day-" + nDay + "-" + String(key).replace(/[^a-z0-9-]/gi, "");
        h.textContent = global.articleDayHeading(a.published);
        section.appendChild(h);
        ul = document.createElement("ul");
        ul.className = "article-feed-cards";
        section.appendChild(ul);
        container.appendChild(section);
      }
      var li = document.createElement("li");
      li.className = "article-feed-card";
      var href = a.link || "#";
      var metaParts = [
        a.source || "",
        includeCountry && a.country ? a.country : "",
        global.fmtTimeOnly(a.published) || "",
      ].filter(Boolean);
      var metaStr = metaParts.join(" · ");
      var sumHtml = "";
      if (a.summary) {
        var snip = a.summary.length > 280 ? a.summary.substring(0, 280) + "…" : a.summary;
        sumHtml = '<p class="article-feed-card__sum">' + esc(snip) + "</p>";
      }
      li.innerHTML =
        '<a class="article-feed-card__title" href="' +
        esc(href) +
        '" target="_blank" rel="noopener noreferrer">' +
        esc(a.title || "Untitled") +
        "</a>" +
        '<div class="article-feed-card__meta">' +
        esc(metaStr) +
        "</div>" +
        sumHtml;
      ul.appendChild(li);
    });
  };
})(typeof window !== "undefined" ? window : this);
