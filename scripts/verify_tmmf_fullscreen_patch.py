"""Smoke checks for Streamlit TMMF fullscreen host-portal patch."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
TMMF_PY = REPO / "streamlit_tmmf_static.py"
PARITY_PY = REPO / "streamlit_site_parity.py"


def main() -> int:
    tmmf = TMMF_PY.read_text(encoding="utf-8")
    parity = PARITY_PY.read_text(encoding="utf-8")

    patch_match = re.search(
        r'_STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH = """([\s\S]*?)"""',
        tmmf,
    )
    if not patch_match:
        print("FAIL: host patch block missing")
        return 1
    patch = patch_match.group(1)

    checks = [
        ("st-tmmf-fullscreen-host-portal" in patch, "host portal marker"),
        ("parentDoc" in patch and "importNode" in patch, "parent document portal"),
        ("handleExpandClick" in patch, "click delegation"),
        ("rewireExistingButtons" in patch, "post-render rewire"),
        ("window.loadJson._stTmmfWrapped" in patch, "loadJson hook"),
        ("openIframeFallbackModal" in patch, "iframe fallback"),
        ("origOpen.call(fs" in patch, "no recursive openTableModal"),
    ]
    for ok, label in checks:
        if not ok:
            print(f"FAIL: {label}")
            return 1

    load_json_idx = tmmf.index("window.loadJson = function ()")
    patch_idx = tmmf.index("{_STREAMLIT_TABLE_FULLSCREEN_HOST_PATCH}")
    boot_idx = tmmf.index("{js_boot}")
    if not (load_json_idx < patch_idx < boot_idx):
        print("FAIL: patch template must sit between loadJson and boot in iframe HTML")
        return 1

    if "st-tmmf-host-table-modal" not in parity:
        print("FAIL: host modal CSS missing from streamlit_site_parity.py")
        return 1

    from streamlit_tmmf_static import build_tmmf_body_iframe_html

    html = build_tmmf_body_iframe_html(
        payload={"page_title": "t", "band_label": "b"},
        related_chips="",
    )
    portal_idx = html.index("st-tmmf-fullscreen-host-portal")
    boot_idx = html.index("/* ---- rwa-asset-deep-page.js ---- */")
    if portal_idx > boot_idx:
        print("FAIL: rendered iframe HTML has wrong script order")
        return 1

    print("verify_tmmf_fullscreen_patch: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
