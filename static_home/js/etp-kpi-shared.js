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
    if (u === "52W") return "52W";
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

  global.__ETP_KPI = {
    fmtPctDelta: fmtPctDelta,
  };
})(typeof window !== "undefined" ? window : this);
