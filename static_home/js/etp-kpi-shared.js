/**
 * ETP top-line KPI: human-readable % lookback tags next to each delta (matches Python captions).
 */
(function (global) {
  function etpWindowCaption(code) {
    if (!code) return "";
    var u = String(code).toUpperCase();
    if (u === "1M") return "1 mo";
    if (u === "1Y") return "1 yr";
    if (u === "1Y*") return "1 yr*";
    if (u === "52W") return "1 yr";
    return String(code);
  }

  function fmtPctDelta(p, winCode) {
    if (p == null || p === "") return '<span class="kpi-delta neutral">—</span>';
    var n = Number(p);
    var sign = n > 0 ? "+" : "";
    var cls = n > 0 ? "up" : n < 0 ? "down" : "neutral";
    var esc =
      global.escapeHtml ||
      function (x) {
        return String(x);
      };
    var tag =
      winCode != null && String(winCode).length
        ? '<span class="kpi-win"> (' + esc(etpWindowCaption(winCode)) + ")</span>"
        : "";
    return (
      '<span class="kpi-delta ' +
      cls +
      '">' +
      sign +
      n.toFixed(2) +
      "%</span>" +
      tag
    );
  }

  function fmtFlowUsd(n) {
    if (n == null || n === "" || isNaN(Number(n))) return "—";
    var x = Number(n);
    var sign = x > 0 ? "+" : x < 0 ? "−" : "";
    var ax = Math.abs(x);
    var body;
    if (ax >= 1e12) body = "$" + (ax / 1e12).toFixed(2) + "T";
    else if (ax >= 1e9) body = "$" + (ax / 1e9).toFixed(2) + "B";
    else if (ax >= 1e6) body = "$" + (ax / 1e6).toFixed(0) + "M";
    else if (ax >= 1e3) body = "$" + (ax / 1e3).toFixed(0) + "K";
    else body = "$" + ax.toLocaleString();
    return sign ? sign + body : body;
  }

  function fmtFlowDelta(usd, winCode) {
    if (usd == null || usd === "" || isNaN(Number(usd)))
      return '<span class="kpi-delta neutral">—</span>';
    var n = Number(usd);
    var cls = n > 0 ? "up" : n < 0 ? "down" : "neutral";
    var esc =
      global.escapeHtml ||
      function (x) {
        return String(x);
      };
    var tag =
      winCode != null && String(winCode).length
        ? '<span class="kpi-win"> (' + esc(etpWindowCaption(winCode)) + ")</span>"
        : "";
    return (
      '<span class="kpi-delta ' + cls + '">' + esc(fmtFlowUsd(n)) + "</span>" + tag
    );
  }

  function fmtFlowCell(usd) {
    if (usd == null || usd === "" || isNaN(Number(usd))) return '<td class="num">—</td>';
    var n = Number(usd);
    var cls = n >= 0 ? "up" : "down";
    return '<td class="num ' + cls + '">' + fmtFlowUsd(n) + "</td>";
  }

  function fmtFlowWindowTag(winCode) {
    if (!winCode) return "";
    var esc =
      global.escapeHtml ||
      function (x) {
        return String(x);
      };
    return (
      '<span class="kpi-delta neutral"><span class="kpi-win"> (' +
      esc(etpWindowCaption(winCode)) +
      ")</span></span>"
    );
  }

  function flowValClass(usd) {
    if (usd == null || usd === "" || isNaN(Number(usd))) return "";
    var n = Number(usd);
    return n > 0 ? " up" : n < 0 ? " down" : "";
  }

  function stockAnalysisFundUrl(symbol) {
    var s = String(symbol || "").trim().toLowerCase();
    if (!s) return "";
    return "https://stockanalysis.com/etf/" + encodeURIComponent(s) + "/";
  }

  function renderSymbolTd(symbol) {
    var esc =
      global.escapeHtml ||
      function (x) {
        return String(x);
      };
    var label = esc(symbol || "—");
    var url = stockAnalysisFundUrl(symbol);
    if (!url) return '<td><span class="sym">' + label + "</span></td>";
    return (
      '<td><a class="sym sym--link" href="' +
      esc(url) +
      '" target="_blank" rel="noopener noreferrer">' +
      label +
      "</a></td>"
    );
  }

  global.__ETP_KPI = {
    fmtPctDelta: fmtPctDelta,
    fmtFlowDelta: fmtFlowDelta,
    fmtFlowCell: fmtFlowCell,
    fmtFlowUsd: fmtFlowUsd,
    fmtFlowWindowTag: fmtFlowWindowTag,
    flowValClass: flowValClass,
    stockAnalysisFundUrl: stockAnalysisFundUrl,
    renderSymbolTd: renderSymbolTd,
  };
})(typeof window !== "undefined" ? window : this);
