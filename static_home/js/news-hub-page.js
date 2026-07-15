/**
 * Unified news hub: lane filters (digital / etf / regulatory / custody) + magazine layout.
 * URL: news.html?lane=digital|etf|regulatory|custody  (also accepts legacy hash #regulatory etc.)
 */
(function () {
  var PAGE_SIZE = 18;
  var FEATURE_COUNT = 3;

  var LANES = {
    digital: {
      id: "digital",
      feed: "all_articles.json",
      badge: "NEWS",
      title: "Digital asset news",
      dek:
        "Curated headlines from <strong>CoinDesk</strong> and <strong>The Block</strong> only — " +
        "duplicates collapsed, up to eight stories per UTC day across a rolling <strong>five</strong>-day window. " +
        "Topic chips map stories to site pages (TMMFs, Stablecoins, RWA Market, U.S. ETPs, Crypto Prices, or Other).",
      searchPlaceholder: "Search all news — title, summary, source, or topic…",
      includeCountry: false,
      includeAccess: false,
      empty: "No digital-asset headlines match. Try another lane or clear search.",
    },
    etf: {
      id: "etf",
      feed: "etf_news.json",
      badge: "ETP",
      title: "ETF &amp; ETP news",
      dek:
        "Crypto and finance headlines focused on exchange-traded products — including specialist ETF outlets " +
        "and Google News ETF queries when direct RSS is blocked. Up to five ranked stories per UTC day " +
        "across a rolling <strong>five</strong>-day window.",
      searchPlaceholder: "Search all news — title, summary, source, or topic…",
      includeCountry: false,
      includeAccess: false,
      empty: "No ETF/ETP headlines match. Try another lane or clear search.",
    },
    regulatory: {
      id: "regulatory",
      feed: "all_regulatory.json",
      badge: "NEWS",
      title: "Regulatory &amp; policy news",
      dek:
        "Regulator, central-bank, and policy coverage for digital assets. " +
        "Up to five ranked stories per UTC day — search runs across every news lane.",
      searchPlaceholder: "Search all news — title, summary, source, or topic…",
      includeCountry: true,
      includeAccess: false,
      empty: "No regulatory headlines match. Try another lane or clear search.",
    },
    custody: {
      id: "custody",
      feed: "all_custodian_news.json",
      badge: "NEWS",
      title: "Custody news",
      dek:
        "Digital-asset custody and infrastructure coverage from Global Custodian and related sources. " +
        "Access badges are best-effort (Free / Subscriber / Check site).",
      searchPlaceholder: "Search all news — title, summary, source, or topic…",
      includeCountry: false,
      includeAccess: true,
      empty: "No custody headlines match. Try another lane or clear search.",
    },
  };

  var cache = {};
  var laneId = "digital";
  var all = [];
  var filtered = [];
  var page = 0;
  var searchAllMode = false;
  var activeQuery = "";
  var corpus = [];
  var corpusReady = false;
  var corpusLoading = null;

  var TOPIC_LABELS = {
    tmmf: "TMMFs",
    stablecoins: "Stablecoins",
    etp: "U.S. ETPs",
    rwa: "RWA Market",
    crypto: "Crypto Prices",
    regulatory: "Regulatory",
    other: "Other",
  };

  var TOPIC_RULES = [
    {
      id: "tmmf",
      re: /\b(?:tokenized\s+money\s+market|money\s+market\s+fund|mmf\b|buidl|cash\s+management\s+fund|liquidity\s+fund|blackrock\s+buidl)\b/i,
    },
    {
      id: "stablecoins",
      re: /\b(?:stablecoin|stable\s*coin|usdc|usdt|tether|dai\b|pyusd|eurc|circle\b|de-?peg|reserves?\s+attestation)\b/i,
    },
    {
      id: "etp",
      re: /\b(?:\betf\b|\betp\b|etns?|exchange[-\s]?traded|spot\s+bitcoin\s+etf|spot\s+ether(?:eum)?\s+etf|ibit\b|fbtc\b|etha\b|arkb\b|bitb\b|farside)\b/i,
    },
    {
      id: "rwa",
      re: /\b(?:\brwa\b|real[-\s]?world\s+assets?|tokenized\s+treasur|tokenised\s+treasur|tokenized\s+stock|tokenised\s+stock|ondo\b|securitize|tokenization\b|tokenised\s+fund|tokenized\s+fund|transfer\s+agent)\b/i,
    },
    {
      id: "crypto",
      re: /\b(?:bitcoin|btc\b|ethereum|ether\b|eth\b|solana|sol\b|xrp\b|crypto\s+(?:price|market|rally|selloff|winter)|spot\s+price|market\s+cap|altcoin|memecoin)\b/i,
    },
    {
      id: "regulatory",
      re: /\b(?:regulation|regulatory|regulator|rulemaking|rule\s+making|compliance|enforcement|enforce\b|oversight|supervision|legislation|legislative|statute|\bbill\b|congress|senate|executive\s+order|framework|lawsuit|litigation|license|licence|approval|proposed\s+rule|final\s+rule|notice\s+of\s+proposed\s+rulemaking|\bnprm\b|investigation|charges?\b|warning\s+notice|market\s+structure|legal\s+action|securities\s+law|market\s+abuse|aml\b|kyc\b|\bsec\b|cftc\b|fincen\b|\bocc\b|\bfdic\b|esma\b|mica\b|genius\s+act|bitlicense|court\s+rules?|court\s+order|align\s+rules|roadmap|fatwa|cbdc\s+ban)\b/i,
    },
  ];

  function esc(s) {
    return typeof escapeHtml === "function" ? escapeHtml(s) : String(s || "");
  }

  function readLaneFromUrl() {
    try {
      var u = new URL(window.location.href);
      var q = (u.searchParams.get("lane") || "").trim().toLowerCase();
      if (LANES[q]) return q;
      var h = (u.hash || "").replace(/^#/, "").toLowerCase();
      if (h === "regulatory" || h === "custody" || h === "etf" || h === "digital") return h;
      if (h === "etp") return "etf";
    } catch (_e) {}
    var bodyLane = (document.body.getAttribute("data-news-lane") || "").trim().toLowerCase();
    if (LANES[bodyLane]) return bodyLane;
    return "digital";
  }

  function writeLaneToUrl(id) {
    try {
      if (!window.location || window.location.protocol === "about:") return;
      var u = new URL(window.location.href);
      u.searchParams.set("lane", id);
      u.hash = "";
      history.replaceState(null, "", u.pathname + u.search + (u.hash || ""));
    } catch (_e) {}
  }

  function lane() {
    return LANES[laneId] || LANES.digital;
  }

  function snip(text, max) {
    var t = String(text || "").trim();
    if (!t) return "";
    if (t.length <= max) return t;
    return t.substring(0, max).replace(/\s+\S*$/, "") + "…";
  }

  function highlightText(text, q) {
    var raw = String(text || "");
    if (!q) return esc(raw);
    var lower = raw.toLowerCase();
    var needle = String(q).toLowerCase();
    if (!needle) return esc(raw);
    var out = "";
    var i = 0;
    while (i < raw.length) {
      var at = lower.indexOf(needle, i);
      if (at < 0) {
        out += esc(raw.slice(i));
        break;
      }
      out += esc(raw.slice(i, at));
      out += '<mark class="news-hub-mark">' + esc(raw.slice(at, at + needle.length)) + "</mark>";
      i = at + needle.length;
    }
    return out;
  }

  function metaExtras(a, c) {
    var parts = [
      a.source || "",
      c.includeCountry && a.country ? a.country : "",
      a.category || "",
      typeof fmtTimeOnly === "function" ? fmtTimeOnly(a.published) || "" : "",
    ].filter(Boolean);
    return parts.join(" · ");
  }

  function classifyTopic(a) {
    var id = String(a.topic || "").trim().toLowerCase();
    if (TOPIC_LABELS[id]) {
      return { id: id, label: a.topic_label || TOPIC_LABELS[id] };
    }
    var blob = ((a.title || "") + " " + (a.summary || "") + " " + (a.category || "")).toLowerCase();
    for (var i = 0; i < TOPIC_RULES.length; i++) {
      if (TOPIC_RULES[i].re.test(blob)) {
        return { id: TOPIC_RULES[i].id, label: TOPIC_LABELS[TOPIC_RULES[i].id] };
      }
    }
    return { id: "other", label: TOPIC_LABELS.other };
  }

  function topicChipHtml(a) {
    var t = classifyTopic(a);
    return (
      '<span class="news-hub-topic news-hub-topic--' +
      t.id +
      '">' +
      esc(t.label) +
      "</span>"
    );
  }

  function accessHtml(a, c) {
    if (!c.includeAccess || typeof articleAccessBadgeHtml !== "function") return "";
    return articleAccessBadgeHtml(a.access);
  }

  function laneBadgeHtml(laneKey) {
    var L = LANES[laneKey];
    if (!L) return "";
    return '<span class="news-hub-lane-tag">' + esc(L.title.replace(/&amp;/g, "&")) + "</span>";
  }

  function setActiveLaneButtons() {
    document.querySelectorAll(".news-hub-lanes__btn").forEach(function (btn) {
      var on = btn.getAttribute("data-lane") === laneId;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
    document.body.classList.remove("lane-digital", "lane-etf", "lane-regulatory", "lane-custody");
    document.body.classList.add("lane-" + laneId);
    var zone = document.querySelector(".inner-rich-zone.zone--news, .inner-rich-zone.zone--etp");
    if (zone) {
      zone.classList.toggle("zone--etp", laneId === "etf");
      zone.classList.toggle("zone--news", laneId !== "etf");
      zone.classList.toggle("home-zone--etp", laneId === "etf");
      zone.classList.toggle("home-zone--news", laneId !== "etf");
    }
    document.body.classList.toggle("page-etp", laneId === "etf");
  }

  function updateChrome() {
    var c = lane();
    var titleEl = document.getElementById("js-news-hub-title");
    var dekEl = document.getElementById("js-news-hub-dek");
    var badgeEl = document.getElementById("js-news-hub-badge");
    var searchEl = document.getElementById("js-article-feed-search");
    if (titleEl) titleEl.innerHTML = c.title;
    if (dekEl) dekEl.innerHTML = c.dek;
    if (badgeEl) badgeEl.textContent = c.badge;
    if (searchEl) searchEl.setAttribute("placeholder", c.searchPlaceholder);
    document.title = titleEl
      ? titleEl.textContent + " — Digital Assets Dashboard"
      : "News — Digital Assets Dashboard";
    setActiveLaneButtons();
  }

  function storyRowHtml(a, c) {
    var href = a.link || "#";
    var titleHtml = highlightText(a.title || "Untitled", activeQuery);
    var dekRaw = snip(a.summary || "", searchAllMode ? 220 : 200);
    var dekHtml = dekRaw ? highlightText(dekRaw, activeQuery) : "";
    var topic = classifyTopic(a);
    var extras = metaExtras(a, c);
    var access = accessHtml(a, c);
    var toplineBits = [topicChipHtml(a)];
    if (searchAllMode && a._hubLane) toplineBits.push(laneBadgeHtml(a._hubLane));
    if (access) toplineBits.push(access);
    if (extras) {
      toplineBits.push('<span class="news-hub-story__when">' + esc(extras) + "</span>");
    }
    return (
      '<li class="news-hub-story' +
      (searchAllMode ? " news-hub-story--result" : "") +
      '">' +
      '<a class="news-hub-story__link" href="' +
      esc(href) +
      '" target="_blank" rel="noopener noreferrer">' +
      '<span class="news-hub-story__rail news-hub-story__rail--' +
      topic.id +
      '" aria-hidden="true"></span>' +
      '<div class="news-hub-story__body">' +
      '<div class="news-hub-story__topline">' +
      toplineBits.join("") +
      "</div>" +
      '<p class="news-hub-story__title">' +
      titleHtml +
      "</p>" +
      (dekHtml ? '<p class="news-hub-story__dek">' + dekHtml + "</p>" : "") +
      "</div>" +
      '<span class="news-hub-story__go" aria-hidden="true">Read →</span>' +
      "</a></li>"
    );
  }

  function featureHtml(items, c) {
    if (!items.length) return "";
    var lead = items[0];
    var side = items.slice(1, FEATURE_COUNT);
    var leadHref = lead.link || "#";
    var leadDek = snip(lead.summary || "", 280);
    var leadExtras = metaExtras(lead, c);
    var html =
      '<a class="news-hub-lead" href="' +
      esc(leadHref) +
      '" target="_blank" rel="noopener noreferrer">' +
      '<span class="news-hub-lead__kicker">Lead story</span>' +
      '<h2 class="news-hub-lead__title">' +
      esc(lead.title || "Untitled") +
      "</h2>" +
      (leadDek ? '<p class="news-hub-lead__dek">' + esc(leadDek) + "</p>" : "") +
      '<div class="news-hub-lead__meta">' +
      topicChipHtml(lead) +
      (searchAllMode && lead._hubLane ? laneBadgeHtml(lead._hubLane) : "") +
      accessHtml(lead, c) +
      (leadExtras ? "<span>" + esc(leadExtras) + "</span>" : "") +
      '<span class="news-hub-lead__cta">Read story →</span>' +
      "</div></a>";

    if (side.length) {
      html += '<div class="news-hub-side">';
      side.forEach(function (a) {
        var dek = snip(a.summary || "", 160);
        var extras = metaExtras(a, c);
        html +=
          '<a class="news-hub-side__card news-hub-side__card--' +
          classifyTopic(a).id +
          '" href="' +
          esc(a.link || "#") +
          '" target="_blank" rel="noopener noreferrer">' +
          '<div class="news-hub-side__topline">' +
          topicChipHtml(a) +
          (searchAllMode && a._hubLane ? laneBadgeHtml(a._hubLane) : "") +
          "</div>" +
          '<p class="news-hub-side__title">' +
          esc(a.title || "Untitled") +
          "</p>" +
          (dek ? '<p class="news-hub-side__dek">' + esc(dek) + "</p>" : "") +
          '<div class="news-hub-side__meta">' +
          accessHtml(a, c) +
          esc(extras) +
          "</div></a>";
      });
      html += "</div>";
    }
    return html;
  }

  function listByDayHtml(items, c) {
    if (!items.length) {
      if (searchAllMode && activeQuery) {
        return (
          '<p class="article-feed-empty news-hub-search-empty">No stories match “' +
          esc(activeQuery) +
          '”. Try another word, or clear search to browse this lane.</p>'
        );
      }
      return '<p class="article-feed-empty">' + esc(c.empty) + "</p>";
    }
    var prevKey = null;
    var html = "";
    var ulOpen = false;
    items.forEach(function (a) {
      var key = typeof articleDateKey === "function" ? articleDateKey(a.published) : "day";
      if (key !== prevKey) {
        if (ulOpen) html += "</ul></section>";
        prevKey = key;
        var label =
          typeof articleDayHeading === "function" ? articleDayHeading(a.published) : String(key);
        var isPrior = String(label).trim().toUpperCase() !== "TODAY";
        html +=
          '<section class="news-hub-day' +
          (isPrior ? " news-hub-day--prior" : "") +
          '">' +
          '<h3 class="news-hub-day__label">' +
          esc(label) +
          "</h3>" +
          '<ul class="news-hub-stories">';
        ulOpen = true;
      }
      html += storyRowHtml(a, c);
    });
    if (ulOpen) html += "</ul></section>";
    return html;
  }

  function matchesQuery(a, q, c) {
    if (!q) return true;
    var topic = classifyTopic(a);
    var blob =
      (a.title || "") +
      " " +
      (a.summary || "") +
      " " +
      (a.source || "") +
      " " +
      topic.label +
      " " +
      topic.id +
      (c.includeCountry ? " " + (a.country || "") : "") +
      (c.includeAccess ? " " + (a.access || "") + " " + (a.category || "") : "");
    return blob.toLowerCase().indexOf(q) >= 0;
  }

  function ensureCorpus() {
    if (corpusReady) return Promise.resolve(corpus);
    if (corpusLoading) return corpusLoading;
    if (typeof loadJson !== "function") return Promise.resolve([]);
    var keys = Object.keys(LANES);
    corpusLoading = Promise.all(
      keys.map(function (id) {
        var feed = LANES[id].feed;
        if (cache[feed]) {
          return Promise.resolve({ id: id, items: cache[feed] });
        }
        return loadJson(feed)
          .then(function (data) {
            cache[feed] = data.items || [];
            return { id: id, items: cache[feed] };
          })
          .catch(function () {
            cache[feed] = cache[feed] || [];
            return { id: id, items: cache[feed] };
          });
      })
    ).then(function (packs) {
      var byLink = {};
      packs.forEach(function (pack) {
        (pack.items || []).forEach(function (item) {
          var key = (item.link || item.title || "").trim();
          if (!key) return;
          if (!byLink[key]) {
            var copy = {};
            Object.keys(item).forEach(function (k) {
              copy[k] = item[k];
            });
            copy._hubLane = pack.id;
            byLink[key] = copy;
          }
        });
      });
      corpus = Object.keys(byLink).map(function (k) {
        return byLink[k];
      });
      corpusReady = true;
      corpusLoading = null;
      return corpus;
    });
    return corpusLoading;
  }

  function applyFilter() {
    var el = document.getElementById("js-article-feed-search");
    var c = lane();
    var raw = (el && el.value ? el.value : "").trim();
    var q = raw.toLowerCase();
    page = 0;
    activeQuery = raw;
    if (!q) {
      searchAllMode = false;
      document.body.classList.remove("is-news-search");
      filtered = all.slice();
      render();
      return;
    }
    searchAllMode = true;
    document.body.classList.add("is-news-search");
    ensureCorpus().then(function (rows) {
      filtered = rows.filter(function (a) {
        return matchesQuery(a, q, c);
      });
      render();
    });
  }

  function setResultsChrome(sorted) {
    var latestHead = document.getElementById("js-news-hub-latest-head");
    if (!latestHead) return;
    if (searchAllMode) {
      latestHead.hidden = false;
      latestHead.innerHTML =
        '<h2 class="news-hub-latest-head__title">Search results</h2>' +
        '<p class="news-hub-latest-head__hint">' +
        (sorted.length
          ? sorted.length +
            " match" +
            (sorted.length === 1 ? "" : "es") +
            " for “" +
            esc(activeQuery) +
            "” · all lanes"
          : "No matches for “" + esc(activeQuery) + "”") +
        "</p>";
      return;
    }
    latestHead.innerHTML =
      '<h2 class="news-hub-latest-head__title">Latest</h2>' +
      '<p class="news-hub-latest-head__hint">Summary under each headline — click through to the source</p>';
  }

  function render() {
    var featureEl = document.getElementById("js-news-hub-feature");
    var listEl = document.getElementById("js-article-feed-list");
    var metaEl = document.getElementById("js-article-feed-meta");
    var navEl = document.getElementById("js-article-feed-nav");
    var latestHead = document.getElementById("js-news-hub-latest-head");
    if (!listEl) return;
    var c = lane();
    var sorted =
      typeof sortArticlesByPublishedDesc === "function"
        ? sortArticlesByPublishedDesc(filtered)
        : filtered.slice();

    setResultsChrome(sorted);
    document.body.classList.toggle("is-news-search", searchAllMode);

    var start = 0;
    var featureItems = [];
    var listItems;
    var np;

    if (searchAllMode) {
      // Results mode: skip magazine lead — show a scannable flat list.
      if (featureEl) {
        featureEl.hidden = true;
        featureEl.innerHTML = "";
      }
      start = page * PAGE_SIZE;
      listItems = sorted.slice(start, start + PAGE_SIZE);
      if (latestHead) latestHead.hidden = false;
      np = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE) || 1);
    } else if (page === 0) {
      featureItems = sorted.slice(0, FEATURE_COUNT);
      var rest = sorted.slice(FEATURE_COUNT);
      var listBudget = Math.max(0, PAGE_SIZE - featureItems.length);
      listItems = rest.slice(0, listBudget);
      start = 0;
      if (featureEl) {
        featureEl.hidden = !featureItems.length;
        featureEl.innerHTML = featureHtml(featureItems, c);
      }
      if (latestHead) latestHead.hidden = !listItems.length && !featureItems.length;
      var remainingAfter0 =
        Math.max(
          0,
          sorted.length -
            FEATURE_COUNT -
            Math.max(0, PAGE_SIZE - Math.min(FEATURE_COUNT, sorted.length))
        );
      var extraPages = Math.ceil(remainingAfter0 / PAGE_SIZE);
      np = 1 + Math.max(0, extraPages);
      if (sorted.length <= FEATURE_COUNT) np = 1;
    } else {
      var afterFeature = Math.max(0, sorted.length - FEATURE_COUNT);
      var page0List = Math.max(
        0,
        Math.min(PAGE_SIZE - Math.min(FEATURE_COUNT, sorted.length), afterFeature)
      );
      start = FEATURE_COUNT + page0List + (page - 1) * PAGE_SIZE;
      listItems = sorted.slice(start, start + PAGE_SIZE);
      featureItems = [];
      if (featureEl) {
        featureEl.hidden = true;
        featureEl.innerHTML = "";
      }
      if (latestHead) latestHead.hidden = !listItems.length;
      var rem0 =
        Math.max(
          0,
          sorted.length -
            FEATURE_COUNT -
            Math.max(0, PAGE_SIZE - Math.min(FEATURE_COUNT, sorted.length))
        );
      np = 1 + Math.max(0, Math.ceil(rem0 / PAGE_SIZE));
      if (sorted.length <= FEATURE_COUNT) np = 1;
    }

    listEl.innerHTML = listByDayHtml(listItems, c);

    var shownStart = sorted.length ? start + 1 : 0;
    var shownEnd = Math.min(start + listItems.length, sorted.length);
    if (!searchAllMode && page === 0) {
      shownStart = sorted.length ? 1 : 0;
      shownEnd = Math.min(featureItems.length + listItems.length, sorted.length);
    }

    if (metaEl) {
      metaEl.textContent = searchAllMode
        ? sorted.length
          ? "Showing " + shownStart + "–" + shownEnd + " of " + sorted.length + " matches"
          : "No matches"
        : "Showing " +
          shownStart +
          "–" +
          shownEnd +
          " of " +
          sorted.length +
          " · " +
          all.length +
          " in this lane";
    }

    if (navEl) {
      navEl.innerHTML =
        '<button type="button" class="btn btn-nav" id="article-feed-prev" ' +
        (page <= 0 ? "disabled" : "") +
        ">Previous</button>" +
        '<span class="etf-news-page-num">Page ' +
        (page + 1) +
        " / " +
        np +
        "</span>" +
        '<button type="button" class="btn btn-nav" id="article-feed-next" ' +
        (page >= np - 1 ? "disabled" : "") +
        ">Next</button>";
      var prev = document.getElementById("article-feed-prev");
      var next = document.getElementById("article-feed-next");
      if (prev)
        prev.onclick = function () {
          if (page > 0) {
            page--;
            render();
            window.scrollTo({ top: 0, behavior: "smooth" });
          }
        };
      if (next)
        next.onclick = function () {
          if (page < np - 1) {
            page++;
            render();
            window.scrollTo({ top: 0, behavior: "smooth" });
          }
        };
    }
  }

  function loadLane(id, opts) {
    opts = opts || {};
    if (!LANES[id]) id = "digital";
    laneId = id;
    writeLaneToUrl(id);
    updateChrome();
    var c = lane();
    var banner = document.getElementById("js-data-banner");
    var searchEl = document.getElementById("js-article-feed-search");
    if (searchEl && !opts.keepSearch) searchEl.value = "";

    function accept(items) {
      all = items || [];
      filtered = all.slice();
      page = 0;
      applyFilter();
    }

    if (cache[c.feed]) {
      accept(cache[c.feed]);
      return;
    }

    if (typeof loadJson !== "function") {
      if (banner) {
        banner.hidden = false;
        banner.textContent = "News hub scripts failed to load.";
      }
      return;
    }

    loadJson(c.feed)
      .then(function (data) {
        cache[c.feed] = data.items || [];
        accept(cache[c.feed]);
      })
      .catch(function () {
        if (banner) {
          banner.hidden = false;
          banner.textContent = "Could not load " + c.feed + ".";
        }
        accept([]);
      });
  }

  function init() {
    laneId = readLaneFromUrl();
    document.querySelectorAll(".news-hub-lanes__btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-lane");
        if (id && id !== laneId) loadLane(id);
      });
    });
    var searchEl = document.getElementById("js-article-feed-search");
    if (searchEl) searchEl.addEventListener("input", applyFilter);
    loadLane(laneId, { keepSearch: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
