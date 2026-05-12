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
  function getTickerParts(strip) {
    if (!strip) return null;
    var layout = strip.querySelector(".ticker-strip__layout");
    if (!layout) return null;
    var lab = strip.querySelector(".ticker-strip__label");
    var viewport = layout.querySelector(".ticker-strip__viewport");
    var move = viewport ? viewport.querySelector(".ticker-strip__move") : null;
    var drums = move ? move.querySelectorAll(".ticker-strip__chips") : [];
    if (drums && drums.length) {
      return {
        layout: layout,
        label: lab,
        viewport: viewport,
        move: move,
        primary: drums[0],
        clone: drums.length > 1 ? drums[1] : null,
      };
    }
    var chips = null;
    var k = 0;
    var kids = layout.children;
    for (; k < kids.length; k++) {
      if (kids[k].classList && kids[k].classList.contains("ticker-strip__chips")) {
        chips = kids[k];
        break;
      }
    }
    if (!chips) return null;
    return {
      layout: layout,
      label: lab,
      viewport: null,
      move: null,
      primary: chips,
      clone: null,
    };
  }

  function hydrateStaticCryptoTicker(payload) {
    if (!payload || typeof document === "undefined") return;
    var strips = document.querySelectorAll(".ticker-strip");
    var si = 0;
    for (; si < strips.length; si++) {
      var strip = strips[si];
      var parts = getTickerParts(strip);
      if (!parts || !parts.primary) continue;
      if (parts.label && payload.banner_title) parts.label.textContent = payload.banner_title;
      if (payload.chips_inner_html) {
        parts.primary.innerHTML = payload.chips_inner_html;
        if (parts.clone) parts.clone.innerHTML = payload.chips_inner_html;
      }
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
      var parts = getTickerParts(strip);
      if (!parts || !parts.primary) continue;

      strip.setAttribute("data-ticker-marquee", "1");
      parts.primary.classList.add("ticker-strip__drum");

      if (parts.viewport && parts.move) {
        if (!parts.clone) {
          parts.clone = parts.primary.cloneNode(true);
          parts.clone.setAttribute("aria-hidden", "true");
          parts.clone.classList.add("ticker-strip__chips--marquee-clone");
          parts.move.appendChild(parts.clone);
        } else {
          parts.clone.setAttribute("aria-hidden", "true");
          parts.clone.classList.add("ticker-strip__chips--marquee-clone");
        }
        continue;
      }

      var viewport = document.createElement("div");
      viewport.className = "ticker-strip__viewport";
      var move = document.createElement("div");
      move.className = "ticker-strip__move";
      move.appendChild(parts.primary);
      var drumB = parts.primary.cloneNode(true);
      drumB.setAttribute("aria-hidden", "true");
      drumB.classList.add("ticker-strip__chips--marquee-clone");
      move.appendChild(drumB);
      viewport.appendChild(move);
      parts.layout.appendChild(viewport);
    }
  }

  function tickerNeedsOverflow(parts) {
    if (!parts || !parts.viewport || !parts.move) return false;
    return parts.move.scrollWidth > parts.viewport.clientWidth + 8;
  }

  function tickerPrefersReducedMotion() {
    return !!(global.matchMedia && global.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  function tickerAnimationUnavailable(parts) {
    if (!parts || !parts.move) return true;
    if (tickerPrefersReducedMotion()) return true;
    if (typeof global.getComputedStyle !== "function") return false;
    var style = global.getComputedStyle(parts.move);
    if (!style) return false;
    var name = style.animationName || style.webkitAnimationName || "";
    var duration = style.animationDuration || style.webkitAnimationDuration || "";
    return !name || name === "none" || !duration || duration === "0s" || duration === "0ms";
  }

  function tickerTranslateX(node) {
    if (!node || typeof global.getComputedStyle !== "function") return null;
    var style = global.getComputedStyle(node);
    if (!style) return null;
    var raw = style.transform || style.webkitTransform || "";
    if (!raw || raw === "none") return 0;
    var matrix3d = raw.match(/^matrix3d\((.+)\)$/);
    if (matrix3d) {
      var vals3d = matrix3d[1].split(",");
      return vals3d.length > 12 ? parseFloat(vals3d[12]) || 0 : 0;
    }
    var matrix2d = raw.match(/^matrix\((.+)\)$/);
    if (matrix2d) {
      var vals2d = matrix2d[1].split(",");
      return vals2d.length > 4 ? parseFloat(vals2d[4]) || 0 : 0;
    }
    var translate = raw.match(/translateX\(([-0-9.]+)px\)/i);
    return translate ? parseFloat(translate[1]) || 0 : null;
  }

  function clearTickerMotionProbe(strip) {
    if (!strip) return;
    if (strip.__tickerMotionProbe && typeof global.clearTimeout === "function") {
      global.clearTimeout(strip.__tickerMotionProbe);
    }
    strip.__tickerMotionProbe = 0;
  }

  function stopJsTicker(strip) {
    if (!strip) return;
    clearTickerMotionProbe(strip);
    if (strip.classList) strip.classList.remove("ticker-strip--js-marquee");
    var state = strip.__tickerJsMarquee;
    if (state) {
      if (state.timer && typeof global.clearInterval === "function") global.clearInterval(state.timer);
      if (state.enter && strip.removeEventListener) strip.removeEventListener("mouseenter", state.enter);
      if (state.leave && strip.removeEventListener) strip.removeEventListener("mouseleave", state.leave);
      strip.__tickerJsMarquee = null;
    }
    var parts = getTickerParts(strip);
    if (parts && parts.move) parts.move.style.transform = "";
  }

  function startJsTicker(strip, parts) {
    if (!strip || !parts || !parts.move || !parts.primary) return;
    stopJsTicker(strip);
    if (!strip.classList || typeof global.setInterval !== "function") return;
    var state = {
      offset: 0,
      lastTick: Date.now(),
      paused: false,
      timer: 0,
      enter: null,
      leave: null,
    };
    state.enter = function () {
      state.paused = true;
    };
    state.leave = function () {
      state.paused = false;
      state.lastTick = Date.now();
    };
    strip.addEventListener("mouseenter", state.enter);
    strip.addEventListener("mouseleave", state.leave);
    strip.classList.add("ticker-strip--js-marquee");
    state.timer = global.setInterval(function () {
      if (!document.body || !document.body.contains(strip)) {
        stopJsTicker(strip);
        return;
      }
      var nextParts = getTickerParts(strip);
      if (!nextParts || !nextParts.viewport || !nextParts.move || !nextParts.primary) {
        stopJsTicker(strip);
        return;
      }
      if (tickerPrefersReducedMotion() || !tickerNeedsOverflow(nextParts)) {
        stopJsTicker(strip);
        return;
      }
      var now = Date.now();
      if (state.paused) {
        state.lastTick = now;
        return;
      }
      var primaryWidth = nextParts.primary.scrollWidth;
      if (!primaryWidth) return;
      var speed = primaryWidth / 72000;
      if (!isFinite(speed) || speed <= 0) speed = 0.02;
      state.offset += (now - state.lastTick) * speed;
      state.lastTick = now;
      while (state.offset >= primaryWidth) state.offset -= primaryWidth;
      nextParts.move.style.transform = "translateX(" + (-state.offset).toFixed(2) + "px)";
    }, 16);
    strip.__tickerJsMarquee = state;
  }

  function refreshCryptoTickerLayout(strip) {
    clearTickerMotionProbe(strip);
    var parts = getTickerParts(strip);
    if (!parts || !parts.primary) return;
    if (!parts.viewport || !parts.move) {
      stopJsTicker(strip);
      return;
    }
    var forceJsTicker = strip.getAttribute("data-ticker-mode") === "js";
    if (tickerPrefersReducedMotion() || !tickerNeedsOverflow(parts)) {
      stopJsTicker(strip);
      return;
    }
    if (forceJsTicker) {
      startJsTicker(strip, parts);
      return;
    }
    if (tickerAnimationUnavailable(parts)) {
      startJsTicker(strip, parts);
      return;
    }
    stopJsTicker(strip);
    if (
      typeof global.setTimeout !== "function" ||
      typeof global.getComputedStyle !== "function" ||
      (typeof document !== "undefined" && document.visibilityState === "hidden")
    ) {
      return;
    }
    var startX = tickerTranslateX(parts.move);
    strip.__tickerMotionProbe = global.setTimeout(function () {
      strip.__tickerMotionProbe = 0;
      if (!document.body || !document.body.contains(strip)) return;
      var nextParts = getTickerParts(strip);
      if (!nextParts || !nextParts.viewport || !nextParts.move) return;
      if (tickerPrefersReducedMotion() || !tickerNeedsOverflow(nextParts)) {
        return;
      }
      var endX = tickerTranslateX(nextParts.move);
      if (startX == null || endX == null || Math.abs(endX - startX) < 0.5) startJsTicker(strip, nextParts);
    }, 900);
  }

  function refreshAllCryptoTickerLayouts() {
    if (typeof document === "undefined") return;
    var strips = document.querySelectorAll(".ticker-strip");
    var si = 0;
    for (; si < strips.length; si++) {
      refreshCryptoTickerLayout(strips[si]);
    }
  }

  var tickerLayoutRefreshTimer = 0;

  function scheduleCryptoTickerLayoutRefresh() {
    if (typeof global.setTimeout !== "function") {
      refreshAllCryptoTickerLayouts();
      return;
    }
    if (tickerLayoutRefreshTimer) global.clearTimeout(tickerLayoutRefreshTimer);
    tickerLayoutRefreshTimer = global.setTimeout(function () {
      tickerLayoutRefreshTimer = 0;
      refreshAllCryptoTickerLayouts();
    }, 120);
  }

  function bootStaticCryptoTicker() {
    if (typeof document === "undefined") return;
    var run = function () {
      global
        .loadJson("crypto_ticker.json")
        .then(function (data) {
          hydrateStaticCryptoTicker(data);
          initCryptoTickerMarquee();
          refreshAllCryptoTickerLayouts();
        })
        .catch(function () {
          initCryptoTickerMarquee();
          refreshAllCryptoTickerLayouts();
        });
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
    else run();
    if (typeof global.addEventListener === "function") {
      global.addEventListener("resize", scheduleCryptoTickerLayoutRefresh);
    }
    if (typeof document !== "undefined" && typeof document.addEventListener === "function") {
      document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "visible") scheduleCryptoTickerLayoutRefresh();
      });
    }
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
