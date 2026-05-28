/**
 * Client-side monthly review footnotes (Key observations, ETP, RWA deep pages).
 * Mirrors ``home_layout._monthly_review_state`` — overdue after one calendar month.
 */
(function (global) {
  var STALE_CALENDAR_MONTHS = 1;
  var DEFAULT_YEAR = 2026;
  var DEFAULT_MONTH = 4;

  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  function esc(s) {
    var fn = global.escapeHtml;
    return typeof fn === "function" ? fn(String(s == null ? "" : s)) : String(s == null ? "" : s);
  }

  function addCalendarMonths(year, month, delta) {
    var zeroBased = month - 1 + delta;
    return {
      year: year + Math.floor(zeroBased / 12),
      month: (zeroBased % 12) + 1,
    };
  }

  function formatLabel(year, month) {
    if (month < 1 || month > 12) return String(year);
    return MONTHS[month - 1] + " " + String(year);
  }

  function reviewState(year, month) {
    var lastReviewMs = Date.UTC(year, month - 1, 1);
    var nowMs = Date.now();
    var overdueAt = addCalendarMonths(year, month, STALE_CALENDAR_MONTHS);
    var thresholdMs = Date.UTC(overdueAt.year, overdueAt.month - 1, 1);
    var label = formatLabel(year, month);
    var ageDays = Math.max(0, Math.floor((nowMs - lastReviewMs) / 86400000));
    return {
      overdue: nowMs >= thresholdMs,
      label: label,
      ageDays: ageDays,
    };
  }

  function parseReviewMeta(el) {
    var y = parseInt(el.getAttribute("data-review-year") || "", 10);
    var m = parseInt(el.getAttribute("data-review-month") || "", 10);
    if (y >= 2000 && m >= 1 && m <= 12) {
      return { year: y, month: m };
    }
    return { year: DEFAULT_YEAR, month: DEFAULT_MONTH };
  }

  function applyReviewNote(el) {
    if (!el || !el.classList || !el.classList.contains("review-note")) return;
    var meta = parseReviewMeta(el);
    var st = reviewState(meta.year, meta.month);
    el.setAttribute("data-review-year", String(meta.year));
    el.setAttribute("data-review-month", String(meta.month));
    if (st.overdue) {
      el.className = "review-note review-note--due";
      el.innerHTML =
        "<strong>Review due:</strong> last reviewed " +
        esc(st.label) +
        " (" +
        st.ageDays +
        " days ago).";
    } else {
      el.className = "review-note";
      el.innerHTML =
        "Reviewed monthly — Last reviewed: <strong>" + esc(st.label) + "</strong>";
    }
  }

  function applyMonthlyReviewNotes(root) {
    var scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll(".review-note").forEach(applyReviewNote);
  }

  global.__MONTHLY_REVIEW = {
    STALE_CALENDAR_MONTHS: STALE_CALENDAR_MONTHS,
    apply: applyMonthlyReviewNotes,
    applyElement: applyReviewNote,
    reviewState: reviewState,
  };

  function boot() {
    applyMonthlyReviewNotes(document);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(typeof window !== "undefined" ? window : this);
