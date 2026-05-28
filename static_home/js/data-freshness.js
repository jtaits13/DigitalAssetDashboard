/**
 * Shared "Data as of" labels for static JSON snapshots (export / GitHub Pages).
 */
(function (global) {
  function formatUtcAsOf(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    var y = d.getUTCFullYear();
    var mo = String(d.getUTCMonth() + 1).padStart(2, "0");
    var da = String(d.getUTCDate()).padStart(2, "0");
    var hh = String(d.getUTCHours()).padStart(2, "0");
    var mm = String(d.getUTCMinutes()).padStart(2, "0");
    return y + "-" + mo + "-" + da + " " + hh + ":" + mm + " UTC";
  }

  /**
   * @param {HTMLElement|null} el
   * @param {{ at?: string, source?: string, mode?: string }} opts
   */
  function renderFreshness(el, opts) {
    if (!el) return;
    opts = opts || {};
    var at = formatUtcAsOf(opts.at);
    if (!at) {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    var esc =
      global.escapeHtml ||
      function (x) {
        return String(x);
      };
    var label = opts.label ? String(opts.label).trim() : "Data";
    var parts = [(label || "Data") + " as of " + at];
    if (opts.source) parts.push("· " + opts.source);
    if (opts.mode === "snapshot") parts.push("· static snapshot");
    else if (opts.mode === "live") parts.push("· live chart");
    el.innerHTML = parts.map(function (p) {
      return esc(p);
    }).join(" ");
    el.hidden = false;
  }

  function loadJsonWithTimeout(name, ms) {
    var load =
      typeof global.loadJson === "function"
        ? global.loadJson
        : function () {
            return Promise.reject(new Error("loadJson unavailable"));
          };
    var timeoutMs = ms == null ? 14000 : ms;
    return new Promise(function (resolve, reject) {
      var done = false;
      var timer = setTimeout(function () {
        if (done) return;
        done = true;
        reject(new Error("Timed out loading " + name));
      }, timeoutMs);
      load(name)
        .then(function (data) {
          if (done) return;
          done = true;
          clearTimeout(timer);
          resolve(data);
        })
        .catch(function (err) {
          if (done) return;
          done = true;
          clearTimeout(timer);
          reject(err);
        });
    });
  }

  global.__DATA_FRESHNESS = {
    formatUtcAsOf: formatUtcAsOf,
    renderFreshness: renderFreshness,
    loadJsonWithTimeout: loadJsonWithTimeout,
  };
  global.loadJsonWithTimeout = loadJsonWithTimeout;
})(typeof window !== "undefined" ? window : this);
