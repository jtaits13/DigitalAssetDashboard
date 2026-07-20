/**
 * Top-line snapshot KPI panel (same framing as RWA overview: panel + legend + grid).
 */
(function (global) {
  function esc(s) {
    if (typeof global.escapeHtml === "function") return global.escapeHtml(s);
    if (s == null) return "";
    return String(s);
  }

  function fmtSnapshotPctDelta(pct, caption) {
    if (pct == null || pct === "" || !isFinite(Number(pct))) {
      return '<span class="rwa-kpi-delta neutral">—</span>';
    }
    var n = Number(pct);
    var cls = n > 0 ? "up" : n < 0 ? "down" : "neutral";
    var sign = n > 0 ? "+" : "";
    var cap =
      caption && String(caption).trim()
        ? ' <span class="rwa-kpi-delta-caption">' + esc(String(caption).trim()) + "</span>"
        : "";
    return (
      '<span class="rwa-kpi-delta ' + cls + '">' + sign + n.toFixed(2) + "%" + cap + "</span>"
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

  function snapshotDeltaPct(part) {
    if (!part) return null;
    if (part.delta && part.delta.pct != null && isFinite(Number(part.delta.pct))) {
      return Number(part.delta.pct);
    }
    if (part.delta_30d_pct != null && isFinite(Number(part.delta_30d_pct))) {
      return Number(part.delta_30d_pct);
    }
    if (part.pct_30d != null && isFinite(Number(part.pct_30d))) {
      return Number(part.pct_30d);
    }
    return null;
  }

  function renderCryptoSnapshot(host, payload) {
    payload = payload || {};
    var pct = fmtSnapshotPctDelta;
    var parts = [payload.primary, payload.btc_dominance, payload.stablecoin_share];
    var cells = parts
      .filter(function (p) {
        return p && (p.label || p.value_display);
      })
      .map(function (p) {
        var deltaPct = snapshotDeltaPct(p);
        if (deltaPct == null && p.delta && p.delta.pct === 0) {
          deltaPct = 0;
        }
        var delta =
          deltaPct != null
            ? pct(deltaPct)
            : '<span class="rwa-kpi-delta neutral">—</span>';
        return snapshotCell(p.label, p.value_display, delta, p.hint);
      })
      .join("");
    if (!cells) {
      host.innerHTML =
        '<div class="rwa-kpi-panel-static rwa-kpi-panel-static--compact"><div class="kpi-cell"><span class="kpi-label">Loading…</span></div></div>';
      return;
    }
    renderSnapshotPanel(host, "", cells);
    var panel = host.querySelector(".rwa-kpi-panel-static");
    if (panel) panel.classList.add("rwa-kpi-panel-static--compact");
  }

  function renderEtpSnapshot(host, k) {
    if (!host || !k) return;
    var pct = fmtSnapshotPctDelta;
    var cells =
      snapshotCell("Total AUM (listed)", k.total_aum_display, pct(k.aggregate_pct)) +
      snapshotCell(
        "Spot BTC/ETH net flow",
        k.net_flow_1m_display,
        pct(k.net_flow_1m_pct, "vs prior 30D")
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
    renderSnapshotPanel(host, "", cells);
  }

  global.__SNAPSHOT_KPI = {
    fmtSnapshotPctDelta: fmtSnapshotPctDelta,
    snapshotCell: snapshotCell,
    renderSnapshotPanel: renderSnapshotPanel,
    renderCryptoSnapshot: renderCryptoSnapshot,
    renderEtpSnapshot: renderEtpSnapshot,
  };
})(typeof window !== "undefined" ? window : this);
