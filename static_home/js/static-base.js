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
    if (p.endsWith("/crypto-prices.html")) return p.slice(0, -"crypto-prices.html".length);
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
    if (p.endsWith("/rwa-tokenized-mmf.html")) return p.slice(0, -"rwa-tokenized-mmf.html".length);
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

  function pageNameFromPathname(pathname) {
    var p = pathname != null ? String(pathname) : "";
    while (p.length > 1 && p.endsWith("/")) {
      p = p.slice(0, -1);
    }
    var ix = p.lastIndexOf("/");
    return (ix >= 0 ? p.slice(ix + 1) : p).toLowerCase();
  }

  function resolveSameSiteReferrerBack(options) {
    options = options || {};
    var fallback = options.fallback || {
      href: "etps.html",
      label: "← Back to home",
    };
    var home = options.home || { href: "index.html", label: "← Back to home" };
    var etps = options.etps || {
      href: "etps.html",
      label: "← Back to home",
    };
    var ref = typeof document !== "undefined" ? document.referrer : "";
    if (!ref) return fallback;
    try {
      var refUrl = new URL(ref, window.location.href);
      var here = new URL(window.location.href);
      if (refUrl.origin !== here.origin) return fallback;
      var name = pageNameFromPathname(refUrl.pathname);
      if (!name || name === "index.html") {
        return {
          href: home.href + (refUrl.hash || ""),
          label: home.label,
        };
      }
      if (name === "etps.html") return etps;
    } catch (e) {
      /* ignore malformed referrer */
    }
    return fallback;
  }

  function applyReferrerBackLinks(scope, options) {
    var target = resolveSameSiteReferrerBack(options);
    var root = scope && typeof scope.querySelectorAll === "function" ? scope : document;
    var fn =
      global.__STATIC && typeof global.__STATIC.assetUrl === "function"
        ? global.__STATIC.assetUrl
        : null;
    var hashIx = target.href.indexOf("#");
    var pathPart = hashIx >= 0 ? target.href.slice(0, hashIx) : target.href;
    var hashPart = hashIx >= 0 ? target.href.slice(hashIx) : "";
    var href = (fn ? fn(pathPart) : pathPart) + hashPart;
    root.querySelectorAll("a[data-referrer-back]").forEach(function (a) {
      a.setAttribute("href", href);
      a.textContent = target.label;
    });
  }

  global.resolveSameSiteReferrerBack = resolveSameSiteReferrerBack;
  global.applyReferrerBackLinks = applyReferrerBackLinks;
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
        ["rwa-tokenized-mmf.html", "rwa-tokenized-mmf.html"],
        ["all-articles.html", "all-articles.html"],
        ["all-regulatory.html", "all-regulatory.html"],
        ["crypto-prices.html", "crypto-prices.html"],
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

  /**
   * Wrap label text with a CoinGecko-derived blurb (``about_blurb`` on JSON rows).
   * Uses a real DOM subtree for the popup (CSS ``content: attr(...)`` is unreliable for long text).
   */
  global.escapeAttr = function (s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;")
      .replace(/</g, "&lt;")
      .replace(/\r?\n/g, " ");
  };

  global.wrapCryptoHint = function (text, blurb, extraClass) {
    var t = text == null ? "" : String(text);
    var b = blurb == null ? "" : String(blurb).trim();
    if (!b) return global.escapeHtml(t);
    var cls = "crypto-hint" + (extraClass ? " " + extraClass : "");
    return (
      '<span class="' +
      cls +
      '" tabindex="0">' +
      '<span class="crypto-hint__label">' +
      global.escapeHtml(t) +
      "</span>" +
      '<span class="crypto-hint__bubble" role="tooltip">' +
      global.escapeHtml(b) +
      "</span></span>"
    );
  };

  /**
   * Chrome: a bubble with ``pointer-events: none`` lets the pointer hit elements behind it, so the
   * hint no longer matches ``:hover`` and the tooltip vanishes. Toggle ``crypto-hint--open`` explicitly.
   *
   * Hints inside ``.table-wrap--scroll`` use ``position: fixed`` for the bubble so ``overflow: auto``
   * does not clip the popup (crypto prices full table).
   */
  var cryptoBubbleScrollParents =
    typeof WeakSet !== "undefined"
      ? new WeakSet()
      : { has: function () { return false; }, add: function () {} };
  var cryptoBubbleResizeBound = false;

  function positionCryptoBubble(h) {
    if (!h || !h.classList || !h.classList.contains("crypto-hint--fixed-bubble")) return;
    var bubble = h.querySelector(".crypto-hint__bubble");
    var label = h.querySelector(".crypto-hint__label");
    if (!bubble || !label) return;
    var lr = label.getBoundingClientRect();
    var margin = 12;
    var vw = typeof window !== "undefined" ? window.innerWidth : 1200;
    var maxW = Math.min(26 * 16, vw * 0.94);
    var left = Math.max(margin, Math.min(lr.left, vw - maxW - margin));
    bubble.style.position = "fixed";
    bubble.style.left = left + "px";
    bubble.style.top = lr.bottom + margin + "px";
    bubble.style.right = "auto";
    bubble.style.bottom = "auto";
    bubble.style.maxWidth = "min(26rem, calc(100vw - " + margin * 2 + "px))";
  }

  function clearCryptoBubblePosition(h) {
    var bubble = h && h.querySelector ? h.querySelector(".crypto-hint__bubble") : null;
    if (!bubble) return;
    bubble.style.removeProperty("position");
    bubble.style.removeProperty("left");
    bubble.style.removeProperty("top");
    bubble.style.removeProperty("right");
    bubble.style.removeProperty("bottom");
    bubble.style.removeProperty("max-width");
  }

  function bindCryptoBubbleScrollContainer(container) {
    if (!container || !container.addEventListener) return;
    if (cryptoBubbleScrollParents.has(container)) return;
    cryptoBubbleScrollParents.add(container);
    container.addEventListener("scroll", function () {
      var open = container.querySelectorAll(".crypto-hint--open.crypto-hint--fixed-bubble");
      var j = 0;
      for (; j < open.length; j++) positionCryptoBubble(open[j]);
    });
  }

  function bindCryptoBubbleWindowResize() {
    if (cryptoBubbleResizeBound || typeof window === "undefined" || !window.addEventListener) return;
    cryptoBubbleResizeBound = true;
    window.addEventListener("resize", function () {
      var open = document.querySelectorAll(".crypto-hint--open.crypto-hint--fixed-bubble");
      var j = 0;
      for (; j < open.length; j++) positionCryptoBubble(open[j]);
    });
  }

  global.bindCryptoHints = function (root) {
    if (!root || !root.querySelectorAll) return;
    bindCryptoBubbleWindowResize();
    var hints = root.querySelectorAll(".crypto-hint");
    var i = 0;
    for (; i < hints.length; i++) {
      var h = hints[i];
      if (h.getAttribute("data-hint-bound") === "1") continue;
      h.setAttribute("data-hint-bound", "1");
      var scrollWrap = h.closest ? h.closest(".table-wrap--scroll") : null;
      if (scrollWrap) bindCryptoBubbleScrollContainer(scrollWrap);

      h.addEventListener("mouseenter", function () {
        this.classList.add("crypto-hint--open");
        if (this.closest && this.closest(".table-wrap--scroll")) {
          this.classList.add("crypto-hint--fixed-bubble");
          var self = this;
          requestAnimationFrame(function () {
            positionCryptoBubble(self);
          });
        }
      });
      h.addEventListener("mouseleave", function (ev) {
        var rt = ev.relatedTarget;
        if (rt && this.contains(rt)) return;
        this.classList.remove("crypto-hint--open");
        this.classList.remove("crypto-hint--fixed-bubble");
        clearCryptoBubblePosition(this);
      });
      h.addEventListener("focusin", function () {
        this.classList.add("crypto-hint--open");
        if (this.closest && this.closest(".table-wrap--scroll")) {
          this.classList.add("crypto-hint--fixed-bubble");
          var self = this;
          requestAnimationFrame(function () {
            positionCryptoBubble(self);
          });
        }
      });
      h.addEventListener("focusout", function (ev) {
        var rt = ev.relatedTarget;
        if (rt && this.contains(rt)) return;
        this.classList.remove("crypto-hint--open");
        this.classList.remove("crypto-hint--fixed-bubble");
        clearCryptoBubblePosition(this);
      });
    }
  };

  function getTickerParts(strip) {
    if (!strip) return null;
    var layout = strip.querySelector(".ticker-strip__layout");
    if (!layout) return null;
    var label = strip.querySelector(".ticker-strip__label");
    var mode = (strip.getAttribute("data-ticker-mode") || "").trim();
    if (mode === "pills") {
      var pillCount = parseInt(strip.getAttribute("data-pill-count"), 10);
      if (!isFinite(pillCount) || pillCount < 1) pillCount = 8;
      return {
        strip: strip,
        layout: layout,
        label: label,
        mode: mode,
        primary: layout.querySelector(".ticker-strip__pills"),
        pillCount: pillCount,
      };
    }
    var viewport = layout.querySelector(".ticker-strip__viewport");
    var move = viewport ? viewport.querySelector(".ticker-strip__move") : null;
    var drums = move ? move.querySelectorAll(".ticker-strip__chips") : [];
    if (drums && drums.length) {
      return {
        strip: strip,
        layout: layout,
        label: label,
        mode: "marquee",
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
      strip: strip,
      layout: layout,
      label: label,
      mode: "marquee",
      primary: chips,
      clone: null,
      viewport: null,
      move: null,
    };
  }

  function tickerChildElements(container) {
    var items = [];
    if (!container) return items;
    var i = 0;
    for (; i < container.children.length; i++) {
      items.push(container.children[i]);
    }
    return items;
  }

  function tickerItemSymbol(node) {
    if (!node || typeof node.querySelector !== "function") return "";
    var strong = node.querySelector("strong");
    return strong && strong.textContent ? String(strong.textContent).trim().toUpperCase() : "";
  }

  function initCryptoTickerPills(parts) {
    if (!parts || parts.mode !== "pills" || !parts.primary) return;
    var pillsHost = parts.primary;
    var limit = parts.pillCount || 8;
    var items = tickerChildElements(pillsHost);
    var preferred = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "LINK", "AVAX"];
    var chosenItems = [];
    var remaining = items.slice();
    var pi = 0;
    for (; pi < preferred.length && chosenItems.length < limit; pi++) {
      var ri = 0;
      for (; ri < remaining.length; ri++) {
        if (tickerItemSymbol(remaining[ri]) === preferred[pi]) {
          chosenItems.push(remaining.splice(ri, 1)[0]);
          break;
        }
      }
    }
    while (chosenItems.length < limit && remaining.length) {
      chosenItems.push(remaining.shift());
    }
    pillsHost.innerHTML = "";
    chosenItems.forEach(function (item) {
      if (item.classList) item.classList.add("ticker-strip__pill-item");
      pillsHost.appendChild(item);
    });
  }

  /** Fill ``.ticker-strip`` from ``crypto_ticker.json``. */
  function hydrateStaticCryptoTicker(payload) {
    if (!payload || typeof document === "undefined") return;
    var strips = document.querySelectorAll(".ticker-strip");
    var si = 0;
    for (; si < strips.length; si++) {
      var parts = getTickerParts(strips[si]);
      if (!parts || !parts.primary) continue;
      if (parts.label && payload.banner_title) parts.label.textContent = payload.banner_title;
      if (payload.chips_inner_html) {
        parts.primary.innerHTML = payload.chips_inner_html;
        if (parts.clone) parts.clone.innerHTML = payload.chips_inner_html;
      }
      if (typeof global.finalizeHubAnchors === "function") {
        global.finalizeHubAnchors(parts.strip);
      }
    }
  }

  function initCryptoTickerDisplays() {
    if (typeof document === "undefined") return;
    var strips = document.querySelectorAll(".ticker-strip");
    var si = 0;
    for (; si < strips.length; si++) {
      var parts = getTickerParts(strips[si]);
      if (!parts || !parts.primary) continue;
      if (parts.mode === "pills") {
        initCryptoTickerPills(parts);
        continue;
      }
      if (parts.strip.getAttribute("data-ticker-marquee") === "1") continue;

      parts.strip.setAttribute("data-ticker-marquee", "1");
      parts.primary.classList.add("ticker-strip__drum");

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

  function bootStaticCryptoTicker() {
    if (typeof document === "undefined") return;
    var run = function () {
      global
        .loadJson("crypto_ticker.json")
        .then(function (data) {
          hydrateStaticCryptoTicker(data);
          initCryptoTickerDisplays();
        })
        .catch(function () {
          initCryptoTickerDisplays();
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

  /** Relative time for dashboard headline rails (e.g. ``3h ago``). */
  global.fmtRelativeTime = function (iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return "";
      var seconds = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
      if (seconds < 60) return "just now";
      var minutes = Math.floor(seconds / 60);
      if (minutes < 60) return minutes + "m ago";
      var hours = Math.floor(minutes / 60);
      if (hours < 24) return hours + "h ago";
      var days = Math.floor(hours / 24);
      if (days < 7) return days + "d ago";
      var weeks = Math.floor(days / 7);
      if (weeks < 5) return weeks + "w ago";
      return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    } catch (e) {
      return "";
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
  global.articleAccessBadgeHtml = function (access) {
    var a = String(access || "unknown").toLowerCase();
    if (a === "free") {
      return '<span class="article-access article-access--free">Free</span>';
    }
    if (a === "subscriber") {
      return '<span class="article-access article-access--subscriber">Subscriber</span>';
    }
    return '<span class="article-access article-access--unknown">Check site</span>';
  };

  var ZONE_CHART_PREFIX = {
    rwa: "hx-rwa",
    stable: "hx-stable",
    tmmf: "hx-tmmf",
    etp: "hx-etp",
    crypto: "hx-crypto",
  };

  var ZONE_CHART_FALLBACK = {
    rwa: { bright: "#2a5f82", base: "#1a3d5c", dark: "#142f47", brightRgb: "42, 95, 130" },
    stable: { bright: "#3d78a0", base: "#2d5f7f", dark: "#234c66", brightRgb: "61, 120, 160" },
    tmmf: { bright: "#507188", base: "#3e5c74", dark: "#31485c", brightRgb: "80, 113, 136" },
    etp: { bright: "#2a5080", base: "#1e3a58", dark: "#162d45", brightRgb: "42, 80, 128" },
    crypto: { bright: "#6e869e", base: "#5a7088", dark: "#485a6e", brightRgb: "110, 134, 158" },
  };

  function readCssCustomProp(el, name) {
    if (!el || typeof getComputedStyle !== "function") return "";
    try {
      return getComputedStyle(el).getPropertyValue(name).trim();
    } catch (e) {
      return "";
    }
  }

  function detectZoneChartKey(scope) {
    var zones = ["rwa", "stable", "tmmf", "etp", "crypto"];
    var i;
    if (scope && scope.closest) {
      for (i = 0; i < zones.length; i++) {
        if (scope.closest(".zone--" + zones[i])) return zones[i];
      }
    }
    var article = document.querySelector(".inner-rich-zone");
    if (article && article.classList) {
      for (i = 0; i < zones.length; i++) {
        if (article.classList.contains("zone--" + zones[i])) return zones[i];
      }
    }
    var bc = document.body && document.body.className ? document.body.className : "";
    if (/\bzone--(\w+)\b/.test(bc)) {
      var m = bc.match(/\bzone--(\w+)\b/);
      if (m && ZONE_CHART_FALLBACK[m[1]]) return m[1];
    }
    if (/home-zone--etp|page-etp|mock-etp|page-inner--etp/.test(bc)) return "etp";
    if (/home-zone--crypto|page-crypto|mock-crypto/.test(bc)) return "crypto";
    if (/home-zone--stable|page-stable|mock-stable/.test(bc)) return "stable";
    if (/home-zone--tmmf|mock-tmmf/.test(bc)) return "tmmf";
    return "rwa";
  }

  /**
   * Ranked horizontal-bar series: top N rows plus an optional Other bucket (share sums to ~100%).
   * Other is pinned to the bottom of the chart; top N stay in rank order above it.
   */
  global.buildTopNPlusOtherChartRows = function (rows, opts) {
    opts = opts || {};
    var nameCol = opts.nameCol || "Network";
    var valCol = opts.valCol || "Total Value";
    var topN = opts.topN != null ? Number(opts.topN) : 5;
    var otherLabel = opts.otherLabel || "Other";
    var minOtherShare = opts.minOtherShare != null ? Number(opts.minOtherShare) : 0.05;
    var includeOther = opts.includeOther !== false;

    var sortedDesc = (rows || []).slice().sort(function (a, b) {
      return (Number(b[valCol]) || 0) - (Number(a[valCol]) || 0);
    });
    if (!sortedDesc.length) {
      return { y: [], x: [], text: [], hasOther: false, barCount: 0 };
    }

    function shareOf(r) {
      var ms = r["Market Share"];
      return ms != null && isFinite(Number(ms)) ? Number(ms) : 0;
    }

    var topRanked = sortedDesc.slice(0, topN);
    var remainder = sortedDesc.slice(topN);
    var displayRows = topRanked.slice().reverse();
    var hasOther = false;

    if (includeOther && remainder.length) {
      var otherValue = remainder.reduce(function (s, r) {
        return s + (Number(r[valCol]) || 0);
      }, 0);
      var otherShare = remainder.reduce(function (s, r) {
        return s + shareOf(r);
      }, 0);
      if (otherShare <= 0) {
        var topSum = topRanked.reduce(function (s, r) {
          return s + shareOf(r);
        }, 0);
        otherShare = Math.max(0, 100 - topSum);
      }
      if (otherValue > 0 || otherShare >= minOtherShare) {
        var otherRow = {};
        otherRow[nameCol] = otherLabel;
        otherRow[valCol] = otherValue;
        otherRow["Market Share"] = otherShare;
        displayRows.unshift(otherRow);
        hasOther = true;
      }
    }

    var y = displayRows.map(function (r) {
      return String(r[nameCol] != null ? r[nameCol] : "—").trim() || "—";
    });
    var x = displayRows.map(function (r) {
      return Number(r[valCol]) || 0;
    });
    var text = displayRows.map(function (r) {
      var ms = r["Market Share"];
      if (ms == null || !isFinite(Number(ms))) return "—% share";
      return Number(ms).toFixed(2) + "% share";
    });

    return { y: y, x: x, text: text, hasOther: hasOther, barCount: displayRows.length };
  };

  /** Zone-aware Plotly/chart colors aligned to ``site-experience.css`` inner-page themes. */
  global.getZoneChartTheme = function (scope) {
    var key = detectZoneChartKey(scope);
    var fb = ZONE_CHART_FALLBACK[key] || ZONE_CHART_FALLBACK.rwa;
    var prefix = ZONE_CHART_PREFIX[key] || ZONE_CHART_PREFIX.rwa;
    var anchor =
      scope && scope.closest
        ? scope.closest(".inner-rich-zone") || scope.closest("[class*='zone--']")
        : null;
    if (!anchor) {
      anchor = document.querySelector(".inner-rich-zone") || document.documentElement;
    }
    var bar = readCssCustomProp(anchor, "--" + prefix + "-bright") || fb.bright;
    var base = readCssCustomProp(anchor, "--" + prefix) || fb.base;
    var brightRgb =
      readCssCustomProp(anchor, "--" + prefix + "-bright-rgb") ||
      readCssCustomProp(document.documentElement, "--" + prefix + "-bright-rgb") ||
      fb.brightRgb;
    brightRgb = brightRgb.replace(/\s+/g, " ").trim();
    return {
      zone: key,
      bar: bar,
      barLine: base,
      ink: base,
      inkMuted: bar,
      barFillRgba: "rgba(" + brightRgb + ", 0.14)",
    };
  };

  global.renderArticleFeedByDay = function (container, items, options) {
    options = options || {};
    var emptyMsg =
      options.emptyMessage != null
        ? options.emptyMessage
        : "No headlines match. Clear search and try again.";
    var emptyClass = options.emptyClass || "article-feed-empty";
    var includeCountry = !!options.includeCountry;
    var includeAccess = !!options.includeAccess;
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
      var isLead = false;
      if (key !== prevKey) {
        prevKey = key;
        nDay++;
        isLead = true;
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
      li.className = "article-feed-card" + (isLead ? " article-feed-card--lead" : "");
      var href = a.link || "#";
      var metaParts = [
        a.source || "",
        includeCountry && a.country ? a.country : "",
        a.category || "",
        global.fmtTimeOnly(a.published) || "",
      ].filter(Boolean);
      var metaStr = metaParts.join(" · ");
      var accessHtml = includeAccess ? global.articleAccessBadgeHtml(a.access) : "";
      var sumHtml = "";
      if (a.summary) {
        var snip = a.summary.length > 160 ? a.summary.substring(0, 160).replace(/\s+\S*$/, "") + "…" : a.summary;
        sumHtml = '<p class="article-feed-card__sum">' + esc(snip) + "</p>";
      }
      li.innerHTML =
        '<a class="article-feed-card__title" href="' +
        esc(href) +
        '" target="_blank" rel="noopener noreferrer">' +
        esc(a.title || "Untitled") +
        "</a>" +
        sumHtml +
        '<div class="article-feed-card__meta">' +
        accessHtml +
        esc(metaStr) +
        "</div>";
      ul.appendChild(li);
    });
  };
})(typeof window !== "undefined" ? window : this);
