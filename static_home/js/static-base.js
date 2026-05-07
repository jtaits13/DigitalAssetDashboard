/**
 * Resolve /repo/ base for GitHub project pages and load JSON from static_home/data/.
 */
(function (global) {
  function basePath() {
    var p = window.location.pathname;
    if (p.endsWith("/index.html")) return p.slice(0, -"index.html".length);
    if (p.endsWith("/etf-news.html")) return p.slice(0, -"etf-news.html".length);
    if (p.endsWith("/etps.html")) return p.slice(0, -"etps.html".length);
    if (p.endsWith("/rwa-global.html")) return p.slice(0, -"rwa-global.html".length);
    if (p.endsWith("/rwa-explore-asset-type.html")) return p.slice(0, -"rwa-explore-asset-type.html".length);
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
    return basePath() + s.replace(/^\.\//, "");
  }

  function dataUrl(name) {
    return basePath() + "data/" + name;
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
    return fetch(dataUrl(name), { credentials: "same-origin" }).then(function (r) {
      if (!r.ok) throw new Error("Failed to load " + name + ": " + r.status);
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
