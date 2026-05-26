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
    var snap = global.__SNAPSHOT_KPI;
    if (snap && typeof snap.renderCryptoSnapshot === "function") {
      snap.renderCryptoSnapshot(host, payload || {});
      return;
    }
    payload = payload || {};
    var parts = [payload.primary, payload.btc_dominance, payload.stablecoin_share];
    host.innerHTML = parts
      .filter(function (p) {
        return p && (p.label || p.value_display);
      })
      .map(function (p) {
        return kpiCell(p, null);
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

  function fmtMoverPct(pct) {
    var n = Number(pct);
    if (!isFinite(n)) return "—";
    var cls = n >= 0 ? "up" : "down";
    return (
      '<span class="pct ' +
      cls +
      '">' +
      (n >= 0 ? "+" : "") +
      n.toFixed(2) +
      "%</span>"
    );
  }

  function moverContextHtml(ctx) {
    if (!ctx || !ctx.title) return "";
    var title = escapeHtml(ctx.title);
    if (ctx.link) {
      return (
        '<p class="crypto-top-mover__ctx">' +
        '<a href="' +
        escapeHtml(ctx.link) +
        '" target="_blank" rel="noopener noreferrer">' +
        title +
        "</a></p>"
      );
    }
    return '<p class="crypto-top-mover__ctx">' + title + "</p>";
  }

  function renderKeyObservationsCallout(host, html, options) {
    if (!host) return false;
    var raw = html == null ? "" : String(html);
    if (!raw.trim()) {
      host.hidden = true;
      host.innerHTML = "";
      return false;
    }
    var title = (options && options.title) || "Key observations";
    var temp = document.createElement("div");
    temp.innerHTML = raw;
    temp.querySelectorAll("style").forEach(function (node) {
      node.remove();
    });
    var ul = temp.querySelector("ul");
    host.hidden = false;
    if (!ul) {
      host.innerHTML = raw;
      return true;
    }
    var listHtml = ul.innerHTML;
    var noteEl = temp.querySelector(
      ".takeaways__note, .etp-takeaway-note, .rwa-gmo-takeaway-note, .crypto-story-callout__note"
    );
    var noteHtml = noteEl
      ? '<p class="crypto-story-callout__note">' + noteEl.innerHTML + "</p>"
      : "";
    host.innerHTML =
      '<aside class="crypto-story-callout" aria-labelledby="crypto-key-obs-title">' +
      '<h3 class="crypto-story-callout__title" id="crypto-key-obs-title">' +
      escapeHtml(title) +
      "</h3>" +
      '<ul class="crypto-story-callout__list">' +
      listHtml +
      "</ul>" +
      noteHtml +
      "</aside>";
    return true;
  }

  function renderTopMoversCallout(host, block) {
    if (!host) return;
    block = block || {};
    var movers = block.movers || [];
    if (!movers.length) {
      host.hidden = true;
      host.innerHTML = "";
      return;
    }
    host.hidden = false;
    var items = movers
      .map(function (m) {
        var sym = escapeHtml(m.symbol || "");
        var name = escapeHtml(m.name || "");
        var label = name ? sym + " (" + name + ")" : sym;
        var pctHtml = fmtMoverPct(m.pct_30d).replace(
          'class="pct ',
          'class="crypto-top-mover__pct pct '
        );
        var ctx = moverContextHtml(m.context || {});
        return (
          '<li class="crypto-top-mover">' +
          '<div class="crypto-top-mover__row">' +
          '<span class="crypto-top-mover__label">' +
          label +
          "</span>" +
          pctHtml +
          "</div>" +
          ctx +
          "</li>"
        );
      })
      .join("");
    var note = block.footnote
      ? '<p class="crypto-story-callout__note">' + escapeHtml(block.footnote) + "</p>"
      : "";
    host.innerHTML =
      '<aside class="crypto-story-callout crypto-top-movers" aria-labelledby="crypto-top-movers-title">' +
      '<h3 class="crypto-story-callout__title" id="crypto-top-movers-title">' +
      escapeHtml(block.title || "Top movers (1M)") +
      "</h3>" +
      '<ul class="crypto-story-callout__list crypto-top-movers__list">' +
      items +
      "</ul>" +
      note +
      "</aside>";
  }

  function pickTopMoversFromRows(rows, limit) {
    limit = limit || 3;
    var candidates = (rows || []).filter(function (r) {
      if (!r || (r.category || "").toLowerCase() === "stablecoin") return false;
      var p = Number(r.pct_30d);
      return isFinite(p);
    });
    candidates.sort(function (a, b) {
      return Math.abs(Number(b.pct_30d)) - Math.abs(Number(a.pct_30d));
    });
    return candidates.slice(0, limit).map(function (r) {
      return {
        symbol: r.symbol,
        name: r.name,
        pct_30d: Number(r.pct_30d),
        direction: Number(r.pct_30d) >= 0 ? "up" : "down",
        context: {
          title:
            "Headline context loads on the next data export; check crypto news for recent catalysts.",
          source: "",
        },
      };
    });
  }

  global.__CRYPTO_KPI = {
    renderCryptoKpis: renderCryptoKpis,
    renderStoryCallout: renderStoryCallout,
    renderKeyObservationsCallout: renderKeyObservationsCallout,
    renderTopMoversCallout: renderTopMoversCallout,
    pickTopMoversFromRows: pickTopMoversFromRows,
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
