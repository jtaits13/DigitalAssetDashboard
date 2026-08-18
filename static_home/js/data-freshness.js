/**
 * Shared snapshot freshness labels and stale-data warnings for GitHub Pages.
 */
(function (global) {
  var DEFAULT_REFRESH_HOURS = 6;
  var SECTION_THRESHOLDS = {
    etp: 9,
    crypto: 9,
    rwa: 9,
    news: 12,
    regulatory: 24,
    default: 9,
  };

  function formatUtcAsOf(iso) {
    var d = parseTimestamp(iso);
    if (!d) return "";
    var y = d.getUTCFullYear();
    var mo = String(d.getUTCMonth() + 1).padStart(2, "0");
    var da = String(d.getUTCDate()).padStart(2, "0");
    var hh = String(d.getUTCHours()).padStart(2, "0");
    var mm = String(d.getUTCMinutes()).padStart(2, "0");
    return y + "-" + mo + "-" + da + " " + hh + ":" + mm + " UTC";
  }

  function parseTimestamp(raw) {
    if (!raw) return null;
    var s = String(raw).trim();
    if (!s) return null;
    var d = new Date(s);
    if (!isNaN(d.getTime())) return d;
    var m = s.match(/^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+UTC/);
    if (m) {
      d = new Date(m[1] + "T" + m[2] + "Z");
      if (!isNaN(d.getTime())) return d;
    }
    return null;
  }

  function ageHours(iso) {
    var d = parseTimestamp(iso);
    if (!d) return null;
    return (Date.now() - d.getTime()) / 3600000;
  }

  function formatAge(iso) {
    var age = ageHours(iso);
    if (age == null) return "";
    if (age < 1) return Math.round(age * 60) + " minutes";
    if (age < 48) return Math.round(age) + " hours";
    return Math.round(age / 24) + " days";
  }

  function thresholdHours(manifest, key) {
    var custom =
      manifest &&
      manifest.stale_threshold_hours &&
      manifest.stale_threshold_hours[key];
    if (typeof custom === "number" && custom > 0) return custom;
    if (SECTION_THRESHOLDS[key]) return SECTION_THRESHOLDS[key];
    return SECTION_THRESHOLDS.default;
  }

  function refreshIntervalHours(manifest) {
    var raw = manifest && manifest.refresh_interval_hours;
    if (typeof raw === "number" && raw > 0) return raw;
    return DEFAULT_REFRESH_HOURS;
  }

  function isStale(iso, maxHours) {
    var age = ageHours(iso);
    if (age == null) return false;
    return age > maxHours;
  }

  function staleSectionIssue(label, at, maxHours, refreshHours) {
    if (!at || !isStale(at, maxHours)) return null;
    return (
      label +
      ": snapshot is " +
      formatAge(at) +
      " old (expected refresh about every " +
      refreshHours +
      " hours). Figures may be outdated."
    );
  }

  /**
   * Build stale-data messages from manifest section timestamps and optional overrides.
   * @param {object|null} manifest
   * @param {object} [overrides] keys: etp, crypto, rwa, news, regulatory, export
   */
  function collectStaleIssues(manifest, overrides) {
    manifest = manifest || {};
    overrides = overrides || {};
    var sections = manifest.sections || {};
    var refreshHours = refreshIntervalHours(manifest);
    var issues = [];
    var staleFlags = overrides.staleFlags || {};
    var listed = manifest.stale_sections || [];
    function isBackup(key) {
      return !!(staleFlags[key] || listed.indexOf(key) >= 0);
    }
    var checks = [
      ["U.S. ETPs", overrides.etp || sections.etp || manifest.etp_refreshed_at, "etp"],
      ["Crypto", overrides.crypto || sections.crypto || manifest.crypto_refreshed_at, "crypto"],
      ["RWA / on-chain", overrides.rwa || sections.rwa, "rwa"],
      ["News", overrides.news || sections.news || overrides.home_news, "news"],
      ["Regulatory news", overrides.regulatory || sections.regulatory, "regulatory"],
    ];
    checks.forEach(function (row) {
      var at = row[1];
      var key = row[2];
      if (isBackup(key)) {
        issues.push(
          row[0] +
            ": live data could not be pulled, so the last saved snapshot is shown" +
            (at ? " (" + formatAge(at) + " old)" : "") +
            "."
        );
        return;
      }
      var issue = staleSectionIssue(row[0], at, thresholdHours(manifest, key), refreshHours);
      if (issue) issues.push(issue);
    });
    var exportAt =
      overrides.export ||
      manifest.export_completed_at ||
      manifest.generated_at;
    if (exportAt && isStale(exportAt, refreshHours * 1.5)) {
      issues.push(
        "Site snapshot is " +
          formatAge(exportAt) +
          " old. Automated refresh runs about every " +
          refreshHours +
          " hours."
      );
    }
    return issues;
  }

  function escHtml(value) {
    if (global.escapeHtml) return global.escapeHtml(value);
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /**
   * Show a newsletter-style stale warning on a banner element.
   */
  function showStaleBanner(el, issues, opts) {
    if (!el || !issues || !issues.length) return;
    opts = opts || {};
    var title = opts.title || "Data may be outdated";
    var body =
      opts.body ||
      "Some figures below may not reflect the latest market data. They are still shown from the last good snapshot.";
    el.classList.add("data-banner--stale");
    el.innerHTML =
      "<strong>" +
      escHtml(title) +
      "</strong> " +
      escHtml(body) +
      '<ul class="data-banner__list">' +
      issues
        .map(function (item) {
          return "<li>" + escHtml(item) + "</li>";
        })
        .join("") +
      "</ul>";
    el.hidden = false;
    el.setAttribute("role", "alert");
  }

  /** Merge stale issues into an existing plain-text banner. */
  function mergeStaleIntoBanner(el, issues, prefix) {
    if (!el || !issues || !issues.length) return;
    prefix = prefix || "Some snapshots may be outdated:";
    var existing = String(el.textContent || "").trim();
    var merged = prefix + " " + issues.join(" ");
    if (existing && existing.indexOf(prefix) < 0) {
      merged = existing + " " + merged;
    }
    el.classList.add("data-banner--stale");
    el.textContent = merged;
    el.hidden = false;
    el.setAttribute("role", "alert");
  }

  function showPageStaleWarning(bannerEl, manifest, overrides, opts) {
    var issues = collectStaleIssues(manifest, overrides);
    if (issues.length) showStaleBanner(bannerEl, issues, opts);
    return issues;
  }

  /**
   * @param {HTMLElement|null} el
   * @param {{ at?: string, source?: string, mode?: string, label?: string }} opts
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
    var label = opts.label ? String(opts.label).trim() : "Data";
    var parts = [(label || "Data") + " as of " + at];
    if (opts.source) parts.push("· " + opts.source);
    if (opts.mode === "snapshot") parts.push("· static snapshot");
    else if (opts.mode === "live") parts.push("· live chart");
    el.innerHTML = parts.map(function (p) {
      return escHtml(p);
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
    DEFAULT_REFRESH_HOURS: DEFAULT_REFRESH_HOURS,
    SECTION_THRESHOLDS: SECTION_THRESHOLDS,
    formatUtcAsOf: formatUtcAsOf,
    parseTimestamp: parseTimestamp,
    ageHours: ageHours,
    formatAge: formatAge,
    isStale: isStale,
    collectStaleIssues: collectStaleIssues,
    showStaleBanner: showStaleBanner,
    showPageStaleWarning: showPageStaleWarning,
    mergeStaleIntoBanner: mergeStaleIntoBanner,
    renderFreshness: renderFreshness,
    loadJsonWithTimeout: loadJsonWithTimeout,
  };
  global.loadJsonWithTimeout = loadJsonWithTimeout;
})(typeof window !== "undefined" ? window : this);
