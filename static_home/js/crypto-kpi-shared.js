/**
 * Shared crypto KPI strip + optional “how to read” callout (home + crypto prices page).
 */
(function (global) {
  function escapeHtml(s) {
    if (global.escapeHtml) return global.escapeHtml(s);
    if (s == null) return "";
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function fmtDelta(pct, window, fmtDeltaFn) {
    if (fmtDeltaFn) return fmtDeltaFn(pct, window);
    if (pct == null || pct === "") return '<span class="kpi-delta neutral">—</span>';
    var n = Number(pct);
    var cls = n > 0 ? "up" : n < 0 ? "down" : "neutral";
    var win = window ? " " + window : "";
    return '<span class="kpi-delta ' + cls + '">' + (n > 0 ? "+" : "") + n.toFixed(2) + "%" + win + "</span>";
  }

  function kpiCell(item, fmtDeltaFn) {
    if (!item) return "";
    var delta = item.delta;
    var deltaHtml =
      delta && delta.pct != null ? fmtDelta(delta.pct, delta.window || "1M", fmtDeltaFn) : "";
    var sub = item.subnote
      ? '<span class="kpi-subnote">' + escapeHtml(item.subnote) + "</span>"
      : "";
    return (
      '<div class="kpi-cell">' +
      '<span class="kpi-label">' +
      escapeHtml(item.label || "") +
      "</span>" +
      '<span class="kpi-val">' +
      escapeHtml(item.value_display || "—") +
      "</span>" +
      sub +
      deltaHtml +
      "</div>"
    );
  }

  function renderCryptoKpis(host, payload) {
    if (!host) return;
    payload = payload || {};
    var K = global.__ETP_KPI || {};
    var fmtDeltaFn = typeof K.fmtPctDelta === "function" ? K.fmtPctDelta : null;
    var parts = [payload.primary, payload.btc_dominance, payload.stablecoin_share];
    host.innerHTML = parts
      .filter(function (p) {
        return p && (p.label || p.value_display);
      })
      .map(function (p) {
        return kpiCell(p, fmtDeltaFn);
      })
      .join("");
  }

  function renderStoryCallout(host, payload) {
    if (!host) return;
    var story = (payload && payload.story_callout) || null;
    if (!story || !story.bullets || !story.bullets.length) {
      host.hidden = true;
      host.innerHTML = "";
      return;
    }
    host.hidden = false;
    var bullets = story.bullets
      .map(function (b) {
        return "<li>" + escapeHtml(b) + "</li>";
      })
      .join("");
    host.innerHTML =
      '<aside class="crypto-story-callout" aria-labelledby="crypto-story-callout-title">' +
      "<h3 class=\"crypto-story-callout__title\" id=\"crypto-story-callout-title\">" +
      escapeHtml(story.title || "How to read this snapshot") +
      "</h3>" +
      '<ul class="crypto-story-callout__list">' +
      bullets +
      "</ul>" +
      "</aside>";
  }

  global.__CRYPTO_KPI = {
    renderCryptoKpis: renderCryptoKpis,
    renderStoryCallout: renderStoryCallout,
    categoryLabel: function (slug) {
      var labels = {
        l1: "Layer 1",
        stablecoin: "Stablecoin",
        cex: "CEX",
        defi: "DeFi",
        meme: "Meme",
        rwa: "RWA / Tokenized",
        other: "Other",
      };
      return labels[slug] || labels.other;
    },
    categoryClass: function (slug) {
      var s = slug === "exchange" ? "cex" : slug || "other";
      return "crypto-cat crypto-cat--" + s;
    },
  };
})(typeof window !== "undefined" ? window : this);
