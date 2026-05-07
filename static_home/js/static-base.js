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

      var viewport = document.createElement("div");
      viewport.className = "ticker-strip__viewport";
      var track = document.createElement("div");
      track.className = "ticker-strip__track";

      track.appendChild(chips);
      var clone = chips.cloneNode(true);
      clone.setAttribute("aria-hidden", "true");
      clone.classList.add("ticker-strip__chips--marquee-clone");
      track.appendChild(clone);
      viewport.appendChild(track);
      layout.appendChild(viewport);

      function applyShiftAndDuration() {
        var w = chips.offsetWidth;
        if (!w || w < 40) return;
        track.style.setProperty("--ticker-shift", w + "px");
        var pxPerSec = 50;
        var sec = Math.max(18, Math.min(92, w / pxPerSec));
        track.style.animationDuration = sec + "s";
      }

      applyShiftAndDuration();
      window.addEventListener(
        "resize",
        function () {
          applyShiftAndDuration();
        },
        { passive: true }
      );

      try {
        if (typeof ResizeObserver !== "undefined") {
          var ro = new ResizeObserver(function () {
            applyShiftAndDuration();
          });
          ro.observe(strip);
          ro.observe(chips);
        }
      } catch (eRo) {}
    }
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", initCryptoTickerMarquee);
    } else {
      initCryptoTickerMarquee();
    }
  }

  global.loadJson = function (name) {
    var url = dataUrl(name);
    return fetch(url, { credentials: "same-origin" }).then(function (r) {
      if (!r.ok) throw new Error("Failed to load " + name + " (" + url + "): " + r.status);
      return r.json();
    });
  };

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

  global.escapeHtml = function (s) {
    if (s == null) return "";
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  };
})(typeof window !== "undefined" ? window : this);
