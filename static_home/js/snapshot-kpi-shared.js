/**
 * Top-line snapshot KPI panel (same framing as RWA overview: panel + legend + grid).
 */
(function (global) {
  var CRYPTO_KPI_LEGEND_DEFAULT =
    "All % changes in this row are approximately one-month (~30 calendar days). " +
    "Total market cap from CoinPaprika; BTC dominance and stablecoin share from the top-50 list (CoinGecko, CoinCap fallback).";

  var ETP_KPI_LEGEND_DEFAULT =
    "All % changes in this row are typically one-month (~30 calendar days); " +
    "IBIT and ETHA may use one-year figures when one-month Yahoo data is unavailable. " +
    "Aggregate AUM % uses estimated weekly series. " +
    "Fund-flow % compares 30-day Farside spot BTC/ETH ETF totals vs the prior 30 days. " +
    "Dollar totals from StockAnalysis.";

  function esc(s) {
    if (typeof global.escapeHtml === "function") return global.escapeHtml(s);
    if (s == null) return "";
    return String(s);
  }

  function fmtSnapshotPctDelta(pct) {
    if (pct == null || pct === "" || !isFinite(Number(pct))) {
      return '<span class="rwa-kpi-delta neutral">—</span>';
    }
    var n = Number(pct);
    var cls = n > 0 ? "up" : n < 0 ? "down" : "neutral";
    var sign = n > 0 ? "+" : "";
    return (
      '<span class="rwa-kpi-delta ' + cls + '">' + sign + n.toFixed(2) + "%</span>"
    );
  }

  function wrapLabel(label, hint) {
    var H = global.__KPI_HINTS;
    if (H && typeof H.wrapKpiLabel === "function") {
      return H.wrapKpiLabel(label, hint);
    }
    return esc(label);
  }

  function snapshotCell(label, valueDisplay, deltaHtml, hint) {
    return (
      '<div class="rwa-kpi-cell">' +
      '<span class="rwa-kpi-label">' +
      wrapLabel(label, hint) +
      "</span>" +
      '<span class="rwa-kpi-val">' +
      esc(valueDisplay != null && valueDisplay !== "" ? valueDisplay : "—") +
      "</span>" +
      (deltaHtml || "") +
      "</div>"
    );
  }

  function renderSnapshotPanel(host, legendText, cellsHtml) {
    if (!host) return;
    host.innerHTML =
      '<div class="rwa-kpi-panel-static">' +
      (legendText
        ? '<p class="jd-kpi-window-note rwa-onchain-kpi-legend">' + esc(legendText) + "</p>"
        : "") +
      '<div class="rwa-kpi-row rwa-kpi-row--home-grid">' +
      cellsHtml +
      "</div></div>";
    if (global.__KPI_HINTS && typeof global.__KPI_HINTS.bindKpiHints === "function") {
      global.__KPI_HINTS.bindKpiHints(host);
    }
  }

  function renderCryptoSnapshot(host, payload) {
    payload = payload || {};
    var legend = payload.kpi_window_note || CRYPTO_KPI_LEGEND_DEFAULT;
    var pct = fmtSnapshotPctDelta;
    var parts = [payload.primary, payload.btc_dominance, payload.stablecoin_share];
    var cells = parts
      .filter(function (p) {
        return p && (p.label || p.value_display);
      })
      .map(function (p) {
        var delta =
          p.delta && p.delta.pct != null ? pct(p.delta.pct) : '<span class="rwa-kpi-delta neutral">—</span>';
        return snapshotCell(p.label, p.value_display, delta, p.hint);
      })
      .join("");
    if (!cells) {
      host.innerHTML =
        '<div class="rwa-kpi-panel-static"><div class="kpi-cell"><span class="kpi-label">Loading…</span></div></div>';
      return;
    }
    renderSnapshotPanel(host, legend, cells);
  }

  function renderEtpSnapshot(host, k) {
    if (!host || !k) return;
    var legend = k.kpi_window_note || ETP_KPI_LEGEND_DEFAULT;
    var pct = fmtSnapshotPctDelta;
    var cells =
      snapshotCell("Total AUM (listed)", k.total_aum_display, pct(k.aggregate_pct)) +
      snapshotCell(
        "BTC & ETH Fund flows (listed)",
        k.net_flow_1m_display,
        pct(k.net_flow_1m_pct)
      ) +
      snapshotCell(
        "IBIT · AUM",
        k.ibit && k.ibit.aum_display,
        k.ibit && k.ibit.delta && k.ibit.delta.pct != null
          ? pct(k.ibit.delta.pct)
          : '<span class="rwa-kpi-delta neutral">—</span>'
      ) +
      snapshotCell(
        "ETHA · AUM",
        k.etha && k.etha.aum_display,
        k.etha && k.etha.delta && k.etha.delta.pct != null
          ? pct(k.etha.delta.pct)
          : '<span class="rwa-kpi-delta neutral">—</span>'
      );
    renderSnapshotPanel(host, legend, cells);
  }

  global.__SNAPSHOT_KPI = {
    CRYPTO_KPI_LEGEND_DEFAULT: CRYPTO_KPI_LEGEND_DEFAULT,
    ETP_KPI_LEGEND_DEFAULT: ETP_KPI_LEGEND_DEFAULT,
    fmtSnapshotPctDelta: fmtSnapshotPctDelta,
    snapshotCell: snapshotCell,
    renderSnapshotPanel: renderSnapshotPanel,
    renderCryptoSnapshot: renderCryptoSnapshot,
    renderEtpSnapshot: renderEtpSnapshot,
  };
})(typeof window !== "undefined" ? window : this);
