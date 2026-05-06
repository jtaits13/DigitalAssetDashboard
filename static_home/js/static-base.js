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

  /** Rewrite bare ``rwa-global.html`` anchors so they work when the page URL is ``/repo`` (no trailing slash). */
  function fixRwaGlobalNavLinks() {
    if (typeof document === "undefined") return;
    var run = function () {
      var abs = assetUrl("rwa-global.html");
      document.querySelectorAll('a[href="rwa-global.html"]').forEach(function (a) {
        a.setAttribute("href", abs);
      });
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
    else run();
  }
  fixRwaGlobalNavLinks();

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
