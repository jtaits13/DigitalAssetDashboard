"""Live JSON payloads for RWA Explore by Asset Type / Market Participant pages."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape as html_escape
from typing import Any

from rwa_global_page_payloads import _dataframe_json_records, _rwa_kpi_to_dict, _static_rwa_footer_text

EXPLORE_ASSET_PREVIEW_ROWS = 8
PARTICIPANT_KPI_MAX = 5
KPI_LABEL_STABLECOIN_HOLDERS = "Total Stablecoin Holders"

STATIC_RWA_EXPLORE_ASSET_TYPE_PAGE = "rwa-explore-asset-type.html"
STATIC_RWA_EXPLORE_MARKET_PARTICIPANT_PAGE = "rwa-explore-market-participant.html"
STATIC_RWA_PARTICIPANTS_NETWORKS_PAGE = "rwa-participants-networks.html"
STATIC_RWA_PARTICIPANTS_PLATFORMS_PAGE = "rwa-participants-platforms.html"
STATIC_RWA_PARTICIPANTS_ASSET_MANAGERS_PAGE = "rwa-participants-asset-managers.html"
STATIC_RWA_STABLECOINS_PAGE = "rwa-stablecoins.html"
STATIC_RWA_US_TREASURIES_PAGE = "rwa-us-treasuries.html"
STATIC_RWA_TOKENIZED_STOCKS_PAGE = "rwa-tokenized-stocks.html"
STATIC_RWA_TOKENIZED_MMF_PAGE = "rwa-tokenized-mmf.html"

_STATIC_INTERNAL_CTA_PAGE_KEYS: dict[str, str] = {
    STATIC_RWA_STABLECOINS_PAGE: "stablecoins",
    STATIC_RWA_US_TREASURIES_PAGE: "treasuries",
    STATIC_RWA_TOKENIZED_STOCKS_PAGE: "stocks",
    STATIC_RWA_TOKENIZED_MMF_PAGE: "tmmf",
    STATIC_RWA_PARTICIPANTS_NETWORKS_PAGE: "networks",
    STATIC_RWA_PARTICIPANTS_PLATFORMS_PAGE: "platforms",
    STATIC_RWA_PARTICIPANTS_ASSET_MANAGERS_PAGE: "asset_managers",
}


def _explore_preview_table(
    source_rows: list[Any],
    build_df: Any,
    *,
    preview_rows: int = EXPLORE_ASSET_PREVIEW_ROWS,
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = list(source_rows)
    rows_full, columns = _dataframe_json_records(build_df(ordered))
    preview = rows_full[:preview_rows]
    return columns, preview, rows_full


def _participant_kpis_for_export(
    kpis: list[Any],
    *,
    drop_stablecoin_holders: bool = False,
) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for k in kpis:
        row = _rwa_kpi_to_dict(k)
        if drop_stablecoin_holders and row.get("label") == KPI_LABEL_STABLECOIN_HOLDERS:
            continue
        out.append(row)
        if len(out) >= PARTICIPANT_KPI_MAX:
            break
    return out


def _kpi_legend_for_asset(overview_title: str) -> str:
    return (
        "All % changes in this row are 30-day (30D) (RWA.xyz). "
        f"Headline totals from the RWA.xyz {overview_title} Overview."
    )


def _kpi_legend_for_mmf() -> str:
    return (
        "Distributed value uses a 30-day (30D) % change vs summed token values 30 days ago. "
        "Top network share is the largest network by distributed value; the 30D figure is the change in "
        "market-share percentage points (pp), not a percent of total. "
        "Fund universe: fixed curated TMMF population on RWA.xyz US Treasuries and Non-U.S. Government Debt; "
        "KPIs, charts, and league tables use the same fund set."
    )


def _rewrite_explore_payload_for_streamlit(payload: dict[str, Any]) -> dict[str, Any]:
    from streamlit_site_parity import _streamlit_page_href

    out = dict(payload)
    links = dict(out.get("links") or {})
    links["rwa_global"] = _streamlit_page_href("rwa_global")
    links["hub_home"] = "/?jd_scroll=onchain"
    if "explore_asset_type" in links:
        links["explore_asset_type"] = _streamlit_page_href("explore_asset")
    if "explore_market_participant" in links:
        links["explore_market_participant"] = _streamlit_page_href("explore_participant")
    out["links"] = links

    sections: list[dict[str, Any]] = []
    for sec in out.get("sections") or []:
        sec_out = dict(sec)
        ctas: list[dict[str, Any]] = []
        for cta in sec.get("cta") or []:
            cta_out = dict(cta)
            if cta_out.get("internal"):
                page_key = _STATIC_INTERNAL_CTA_PAGE_KEYS.get(str(cta_out.get("href") or ""))
                if page_key:
                    cta_out["href"] = _streamlit_page_href(page_key)
            ctas.append(cta_out)
        sec_out["cta"] = ctas
        sections.append(sec_out)
    out["sections"] = sections
    return out


def build_rwa_explore_asset_type_page_payload(
    *,
    sc_pack: tuple[Any, Any, Any, Any] | None = None,
    tr_pack: tuple[Any, Any, Any, Any] | None = None,
    st_pack: tuple[Any, Any, Any, Any] | None = None,
    mmf_pack: tuple[Any, Any, Any, Any] | None = None,
    for_streamlit: bool = False,
    preview_rows: int = EXPLORE_ASSET_PREVIEW_ROWS,
) -> dict[str, Any]:
    """Build Explore by Asset Type JSON (``rwa_explore_asset_type.json`` shape)."""
    from rwa_league.client import (
        APP_STABLECOINS,
        APP_STOCKS,
        APP_TREASURIES,
        fetch_rwa_stablecoins_data,
        fetch_rwa_tokenized_mmf_data,
        fetch_rwa_tokenized_stocks_data,
        fetch_rwa_treasuries_data,
    )
    from rwa_league.dataframe_table import (
        build_stablecoin_network_dataframe,
        build_stablecoin_platform_dataframe,
        build_tokenized_stock_network_dataframe,
        build_tokenized_stock_platform_dataframe,
        build_us_treasury_network_dataframe,
    )
    from rwa_league.widgets import (
        MMF_RWA_LINK_LABEL,
        STABLECOINS_RWA_LINK_LABEL,
        TREASURIES_RWA_LINK_LABEL,
        TOKENIZED_STOCKS_RWA_LINK_LABEL,
    )

    if sc_pack is None and tr_pack is None and st_pack is None and mmf_pack is None and for_streamlit:
        from rwa_streamlit_fetch_cache import fetch_explore_asset_type_packs_parallel

        sc_pack, tr_pack, st_pack, mmf_pack = fetch_explore_asset_type_packs_parallel()
    elif sc_pack is None:
        try:
            sc_pack = fetch_rwa_stablecoins_data()
        except Exception as exc:
            sc_pack = ([], [], [], str(exc))
    if tr_pack is None:
        try:
            tr_pack = fetch_rwa_treasuries_data()
        except Exception as exc:
            tr_pack = ([], [], [], str(exc))
    if st_pack is None:
        try:
            st_pack = fetch_rwa_tokenized_stocks_data()
        except Exception as exc:
            st_pack = ([], [], [], str(exc))
    if mmf_pack is None:
        try:
            mmf_pack = fetch_rwa_tokenized_mmf_data()
        except Exception as exc:
            mmf_pack = ([], [], [], str(exc))

    sections: list[dict[str, Any]] = []

    sc_net, sc_plat, sc_kpis, sc_err = sc_pack
    sec_sc: dict[str, Any] = {
        "id": "stablecoins",
        "title": "Stablecoins",
        "anchor_id": "jd-rwa-stablecoins",
        "kpi_window_note": _kpi_legend_for_asset("Stablecoins"),
        "kpis": [_rwa_kpi_to_dict(k) for k in sc_kpis],
        "table_subheading": None,
        "columns": [],
        "rows": [],
        "preview_note": "",
        "info_html": "",
        "warn_html": "",
        "cta": [
            {
                "href": STATIC_RWA_STABLECOINS_PAGE,
                "label": "Open full Stablecoins overview",
                "variant": "primary",
                "internal": True,
            },
            {"href": APP_STABLECOINS, "label": STABLECOINS_RWA_LINK_LABEL, "variant": "secondary"},
        ],
    }
    if sc_err and not sc_net and not sc_plat:
        sec_sc["warn_html"] = f'<p class="alert warn">{html_escape(str(sc_err))}</p>'
    elif not sc_net and not sc_plat:
        sec_sc["info_html"] = '<p class="alert info">No Stablecoins league rows returned.</p>'
    elif sc_net:
        cj, rj, rj_full = _explore_preview_table(
            sc_net, build_stablecoin_network_dataframe, preview_rows=preview_rows
        )
        sec_sc["columns"], sec_sc["rows"] = cj, rj
        sec_sc["rows_full"] = rj_full
        sec_sc["table_subheading"] = "By network (Stablecoins · Networks)"
        sec_sc["preview_note"] = (
            f"Preview: first {len(rj)} of {len(rj_full)} networks (Stablecoins · Networks)."
        )
    elif sc_plat:
        cj, rj, rj_full = _explore_preview_table(
            sc_plat, build_stablecoin_platform_dataframe, preview_rows=preview_rows
        )
        sec_sc["columns"], sec_sc["rows"] = cj, rj
        sec_sc["rows_full"] = rj_full
        sec_sc["preview_note"] = (
            f"Preview: first {len(rj)} of {len(rj_full)} platforms (Stablecoins · Platforms)."
        )
    else:
        sec_sc["info_html"] = '<p class="muted"><em>No stablecoin league rows.</em></p>'
    sections.append(sec_sc)

    tr_rows, tr_plat, tr_kpis, tr_err = tr_pack
    sec_tr: dict[str, Any] = {
        "id": "treasuries",
        "title": "US Treasuries",
        "anchor_id": "jd-rwa-treasuries",
        "kpi_window_note": _kpi_legend_for_asset("US Treasuries"),
        "kpis": [_rwa_kpi_to_dict(k) for k in tr_kpis],
        "table_subheading": "By network (Distributed · Networks)",
        "columns": [],
        "rows": [],
        "preview_note": "",
        "info_html": "",
        "warn_html": "",
        "cta": [
            {
                "href": STATIC_RWA_US_TREASURIES_PAGE,
                "label": "Open full US Treasuries overview",
                "variant": "primary",
                "internal": True,
            },
            {"href": APP_TREASURIES, "label": TREASURIES_RWA_LINK_LABEL, "variant": "secondary"},
        ],
    }
    if tr_err and not tr_rows and not tr_plat:
        sec_tr["warn_html"] = f'<p class="alert warn">{html_escape(str(tr_err))}</p>'
    elif not tr_rows and not tr_plat:
        sec_tr["info_html"] = '<p class="alert info">No US Treasuries league rows returned.</p>'
    elif tr_rows:
        cj, rj, rj_full = _explore_preview_table(
            tr_rows, build_us_treasury_network_dataframe, preview_rows=preview_rows
        )
        sec_tr["columns"], sec_tr["rows"] = cj, rj
        sec_tr["rows_full"] = rj_full
        sec_tr["preview_note"] = (
            f"Preview: first {len(rj)} of {len(rj_full)} networks (US Treasuries · Distributed · Networks)."
        )
    else:
        sec_tr["info_html"] = '<p class="muted"><em>No treasury network rows.</em></p>'
    sections.append(sec_tr)

    st_net, st_plat, st_kpis, st_err = st_pack
    sec_st: dict[str, Any] = {
        "id": "tokenized_stocks",
        "title": "Tokenized Stocks",
        "anchor_id": "jd-rwa-tokenized-stocks",
        "kpi_window_note": _kpi_legend_for_asset("Tokenized Stocks"),
        "kpis": [_rwa_kpi_to_dict(k) for k in st_kpis],
        "table_subheading": None,
        "columns": [],
        "rows": [],
        "preview_note": "",
        "info_html": "",
        "warn_html": "",
        "cta": [
            {
                "href": STATIC_RWA_TOKENIZED_STOCKS_PAGE,
                "label": "Open full Tokenized Stocks overview",
                "variant": "primary",
                "internal": True,
            },
            {"href": APP_STOCKS, "label": TOKENIZED_STOCKS_RWA_LINK_LABEL, "variant": "secondary"},
        ],
    }
    if st_err and not st_net and not st_plat:
        sec_st["warn_html"] = f'<p class="alert warn">{html_escape(str(st_err))}</p>'
    elif not st_net and not st_plat:
        sec_st["info_html"] = '<p class="alert info">No Tokenized Stocks league rows returned.</p>'
    elif st_net:
        ordered_n = sorted(st_net, key=lambda r: int(r.rank))
        cj, rj, rj_full = _explore_preview_table(
            ordered_n, build_tokenized_stock_network_dataframe, preview_rows=preview_rows
        )
        sec_st["columns"], sec_st["rows"] = cj, rj
        sec_st["rows_full"] = rj_full
        sec_st["table_subheading"] = "By Network (Distributed · Networks)"
        sec_st["preview_note"] = (
            f"Preview: first {len(rj)} of {len(rj_full)} networks "
            "(Tokenized Stocks · Distributed · Networks), sorted by #."
        )
    elif st_plat:
        cj, rj, rj_full = _explore_preview_table(
            st_plat, build_tokenized_stock_platform_dataframe, preview_rows=preview_rows
        )
        sec_st["columns"], sec_st["rows"] = cj, rj
        sec_st["rows_full"] = rj_full
        sec_st["preview_note"] = (
            f"Preview: first {len(rj)} of {len(rj_full)} platforms "
            "(Tokenized Stocks · Distributed · Platforms)."
        )
    else:
        sec_st["info_html"] = '<p class="alert info">No Tokenized Stocks network or platform rows returned.</p>'
    sections.append(sec_st)

    mmf_net, mmf_plat, mmf_kpis, mmf_err = mmf_pack
    sec_mmf: dict[str, Any] = {
        "id": "tokenized_mmf",
        "title": "Tokenized Money Market Funds",
        "anchor_id": "jd-rwa-tokenized-mmf",
        "kpi_window_note": _kpi_legend_for_mmf(),
        "kpis": [_rwa_kpi_to_dict(k) for k in mmf_kpis],
        "table_subheading": "By network (Tokenized MMFs)",
        "columns": [],
        "rows": [],
        "preview_note": "",
        "info_html": "",
        "warn_html": "",
        "cta": [
            {
                "href": STATIC_RWA_TOKENIZED_MMF_PAGE,
                "label": "Open full Tokenized MMF overview",
                "variant": "primary",
                "internal": True,
            },
            {"href": APP_TREASURIES, "label": MMF_RWA_LINK_LABEL, "variant": "secondary"},
        ],
    }
    if mmf_err and not mmf_net and not mmf_plat:
        sec_mmf["warn_html"] = f'<p class="alert warn">{html_escape(str(mmf_err))}</p>'
    elif not mmf_net and not mmf_plat:
        sec_mmf["info_html"] = '<p class="alert info">No tokenized money market fund rows returned.</p>'
    elif mmf_net:
        cj, rj, rj_full = _explore_preview_table(
            mmf_net, build_us_treasury_network_dataframe, preview_rows=preview_rows
        )
        sec_mmf["columns"], sec_mmf["rows"] = cj, rj
        sec_mmf["rows_full"] = rj_full
        sec_mmf["preview_note"] = (
            f"Preview: first {len(rj)} of {len(rj_full)} networks (Tokenized MMFs), sorted by distributed value."
        )
    else:
        sec_mmf["info_html"] = '<p class="muted"><em>No MMF network rows.</em></p>'
    sections.append(sec_mmf)

    intro_html = (
        "<p><strong>On-chain RWA</strong> by asset—short previews for "
        "<strong>US Treasuries</strong> and <strong>Tokenized Stocks</strong> "
        "(<strong>RWA.xyz</strong>). Stablecoins and tokenized money market funds are on the "
        "<strong>home dashboard</strong>. Use <strong>Open full overview</strong> for search, charts, and full league views.</p>"
    )

    payload: dict[str, Any] = {
        "page_title": "Explore by Asset Type — Digital Assets Dashboard",
        "page_subtitle_html": (
            f"Network or platform previews (first {preview_rows} rows each) for the main asset categories."
        ),
        "intro_html": intro_html,
        "sections": sections,
        "footer_note": _static_rwa_footer_text(),
        "links": {
            "rwa_global": "rwa-global.html",
            "hub_home": "index.html",
        },
    }
    if for_streamlit:
        payload = _rewrite_explore_payload_for_streamlit(payload)
    return payload


def build_rwa_explore_market_participant_page_payload(
    *,
    net_pack: tuple[list[Any], list[Any], Any] | None = None,
    plat_pack: tuple[list[Any], list[Any], Any] | None = None,
    am_pack: tuple[list[Any], list[Any], Any] | None = None,
    for_streamlit: bool = False,
    preview_rows: int = EXPLORE_ASSET_PREVIEW_ROWS,
) -> dict[str, Any]:
    """Build Explore by Market Participant JSON (``rwa_explore_market_participant.json`` shape)."""
    from rwa_league.client import (
        fetch_rwa_asset_managers_page_data,
        fetch_rwa_networks_page_data,
        fetch_rwa_platforms_page_data,
    )
    from rwa_league.dataframe_table import (
        build_rwa_asset_managers_page_dataframe,
        build_rwa_networks_page_dataframe,
        build_rwa_platforms_page_dataframe,
    )
    from rwa_league.widgets import (
        ASSET_MANAGERS_RWA_LINK_LABEL,
        ASSET_MANAGERS_RWA_URL,
        GLOBAL_MARKET_RWA_LINK_LABEL,
        GLOBAL_MARKET_RWA_URL,
        PLATFORMS_RWA_LINK_LABEL,
        PLATFORMS_RWA_URL,
    )

    if net_pack is None and plat_pack is None and am_pack is None and for_streamlit:
        from rwa_streamlit_fetch_cache import fetch_explore_participant_packs_parallel

        net_pack, plat_pack, am_pack = fetch_explore_participant_packs_parallel()
    elif net_pack is None:
        try:
            net_pack = fetch_rwa_networks_page_data()
        except Exception as exc:
            net_pack = ([], [], str(exc))
    if plat_pack is None:
        try:
            plat_pack = fetch_rwa_platforms_page_data()
        except Exception as exc:
            plat_pack = ([], [], str(exc))
    if am_pack is None:
        try:
            am_pack = fetch_rwa_asset_managers_page_data()
        except Exception as exc:
            am_pack = ([], [], str(exc))

    sections: list[dict[str, Any]] = []

    pnet_rows, pnet_kpis, pnet_err = net_pack
    sec_net: dict[str, Any] = {
        "id": "participant_networks",
        "title": "Networks",
        "anchor_id": "jd-rwa-participants-networks",
        "kpi_window_note": _kpi_legend_for_asset("Networks"),
        "kpis": _participant_kpis_for_export(pnet_kpis, drop_stablecoin_holders=True),
        "table_subheading": None,
        "info_html_preview": "",
        "columns": [],
        "rows": [],
        "preview_note": "",
        "info_html": "",
        "warn_html": "",
        "cta": [
            {
                "href": STATIC_RWA_PARTICIPANTS_NETWORKS_PAGE,
                "label": "Open full Participants — Networks overview",
                "variant": "primary",
                "internal": True,
            },
            {"href": GLOBAL_MARKET_RWA_URL, "label": GLOBAL_MARKET_RWA_LINK_LABEL, "variant": "secondary"},
        ],
    }
    if pnet_err and not pnet_rows:
        sec_net["warn_html"] = f'<p class="alert warn">{html_escape(str(pnet_err))}</p>'
    elif not pnet_rows:
        sec_net["info_html"] = '<p class="alert info">No Networks league rows returned.</p>'
    else:
        cj, rj, rj_full = _explore_preview_table(
            pnet_rows, build_rwa_networks_page_dataframe, preview_rows=preview_rows
        )
        sec_net["columns"], sec_net["rows"] = cj, rj
        sec_net["rows_full"] = rj_full
        sec_net["preview_note"] = (
            f"Preview: first {len(rj)} of {len(rj_full)} networks (Distributed · Networks)."
        )
    sections.append(sec_net)

    pplat_rows, pplat_kpis, pplat_err = plat_pack
    sec_plat: dict[str, Any] = {
        "id": "participant_platforms",
        "title": "Platforms",
        "anchor_id": "jd-rwa-participants-platforms",
        "kpi_window_note": _kpi_legend_for_asset("Platforms"),
        "kpis": _participant_kpis_for_export(pplat_kpis, drop_stablecoin_holders=True),
        "table_subheading": None,
        "info_html_preview": "",
        "columns": [],
        "rows": [],
        "preview_note": "",
        "info_html": "",
        "warn_html": "",
        "cta": [
            {
                "href": STATIC_RWA_PARTICIPANTS_PLATFORMS_PAGE,
                "label": "Open full Participants — Platforms overview",
                "variant": "primary",
                "internal": True,
            },
            {"href": PLATFORMS_RWA_URL, "label": PLATFORMS_RWA_LINK_LABEL, "variant": "secondary"},
        ],
    }
    if pplat_err and not pplat_rows:
        sec_plat["warn_html"] = f'<p class="alert warn">{html_escape(str(pplat_err))}</p>'
    elif not pplat_rows:
        sec_plat["info_html"] = '<p class="alert info">No Platforms league rows returned.</p>'
    else:
        cj, rj, rj_full = _explore_preview_table(
            pplat_rows, build_rwa_platforms_page_dataframe, preview_rows=preview_rows
        )
        sec_plat["columns"], sec_plat["rows"] = cj, rj
        sec_plat["rows_full"] = rj_full
        sec_plat["preview_note"] = (
            f"Preview: first {len(rj)} of {len(rj_full)} platforms (Distributed · Platforms)."
        )
    sections.append(sec_plat)

    pam_rows, pam_kpis, pam_err = am_pack
    sec_am: dict[str, Any] = {
        "id": "participant_asset_managers",
        "title": "Asset Managers",
        "anchor_id": "jd-rwa-participants-asset-managers",
        "kpi_window_note": _kpi_legend_for_asset("Asset Managers"),
        "kpis": _participant_kpis_for_export(pam_kpis),
        "table_subheading": None,
        "info_html_preview": "",
        "columns": [],
        "rows": [],
        "preview_note": "",
        "info_html": "",
        "warn_html": "",
        "cta": [
            {
                "href": STATIC_RWA_PARTICIPANTS_ASSET_MANAGERS_PAGE,
                "label": "Open full Participants — Asset Managers overview",
                "variant": "primary",
                "internal": True,
            },
            {"href": ASSET_MANAGERS_RWA_URL, "label": ASSET_MANAGERS_RWA_LINK_LABEL, "variant": "secondary"},
        ],
    }
    if pam_err and not pam_rows:
        sec_am["warn_html"] = f'<p class="alert warn">{html_escape(str(pam_err))}</p>'
    elif not pam_rows:
        sec_am["info_html"] = '<p class="alert info">No Asset Managers league rows returned.</p>'
    else:
        cj, rj, rj_full = _explore_preview_table(
            pam_rows, build_rwa_asset_managers_page_dataframe, preview_rows=preview_rows
        )
        sec_am["columns"], sec_am["rows"] = cj, rj
        sec_am["rows_full"] = rj_full
        sec_am["preview_note"] = (
            f"Preview: first {len(rj)} of {len(rj_full)} asset managers (Distributed · Asset Managers)."
        )
    sections.append(sec_am)

    intro_html = (
        "<p><strong>On-chain RWA</strong> by participant—short previews for "
        "<strong>Networks</strong>, <strong>Platforms</strong>, and <strong>Asset Managers</strong> "
        "(<strong>RWA.xyz</strong>). Use <strong>Open full overview</strong> for search, charts, and full tables.</p>"
    )

    payload: dict[str, Any] = {
        "page_title": "Explore by Market Participant — Digital Assets Dashboard",
        "page_subtitle_html": (
            f"Networks, platforms, and asset managers (first {preview_rows} rows each) for the main participant groups."
        ),
        "intro_html": intro_html,
        "sections": sections,
        "footer_note": _static_rwa_footer_text(),
        "links": {
            "rwa_global": "rwa-global.html",
            "hub_home": "index.html",
            "explore_asset_type": STATIC_RWA_EXPLORE_ASSET_TYPE_PAGE,
        },
    }
    if for_streamlit:
        payload = _rewrite_explore_payload_for_streamlit(payload)
    return payload
