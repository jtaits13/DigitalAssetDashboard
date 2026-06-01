"""Verify site-experience nav assets on every static_home HTML page."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "static_home"


def normalize_nav(html: str) -> str:
    m = re.search(r'<header class="site-header"[\s\S]*?</header>', html)
    nav = m.group(0) if m else ""
    nav = re.sub(r"\bis-active\b", "", nav)
    nav = re.sub(r'\sclass="\s*"', "", nav)
    nav = re.sub(r'class="\s+', 'class="', nav)
    nav = re.sub(r'\s+"', '"', nav)
    return re.sub(r"\s+", " ", nav).strip()


def extract_nav(html: str) -> str:
    m = re.search(r'<header class="site-header"[\s\S]*?</header>', html)
    return m.group(0) if m else ""


def main() -> None:
    files = sorted(ROOT.glob("*.html"))
    issues: list[str] = []
    nav_hashes: dict[str, list[str]] = {}

    for path in files:
        text = path.read_text(encoding="utf-8")
        if "site-experience.css" not in text:
            issues.append(f"{path.name}: missing site-experience.css")
        elif "site-experience.css?v=3" not in text:
            issues.append(f"{path.name}: site-experience.css not at v=3")
        if "site-experience.js" not in text:
            issues.append(f"{path.name}: missing site-experience.js")
        body = re.search(r"<body\b[^>]*\sclass=\"([^\"]+)\"", text, re.S)
        if not body or "site-experience" not in body.group(1):
            issues.append(f"{path.name}: body missing site-experience class")
        if "home-experience" in text:
            issues.append(f"{path.name}: stale home-experience reference")
        if 'styles.css?v=79' not in text:
            issues.append(f"{path.name}: styles.css not at v=79")

        nav = extract_nav(text)
        if not nav:
            issues.append(f"{path.name}: missing site-header block")
        else:
            normalized = normalize_nav(text)
            h = hashlib.sha256(normalized.encode()).hexdigest()[:12]
            nav_hashes.setdefault(h, []).append(path.name)

    print(f"Checked {len(files)} HTML pages.")
    if issues:
        print("\nIssues:")
        for item in issues:
            print(" -", item)
    else:
        print("All pages include site-experience CSS (v3), JS, body class, and styles.css v79.")

    print(f"\nDistinct nav structures (ignoring is-active): {len(nav_hashes)}")
    for h, names in sorted(nav_hashes.items(), key=lambda x: -len(x[1])):
        print(f" - {h} ({len(names)} pages): {', '.join(names[:5])}{'...' if len(names) > 5 else ''}")

    if len(nav_hashes) > 1:
        refs = list(nav_hashes.values())
        na = normalize_nav((ROOT / refs[0][0]).read_text(encoding="utf-8"))
        nb = normalize_nav((ROOT / refs[1][0]).read_text(encoding="utf-8"))
        if na != nb:
            print("\nNav diff sample (first mismatching pair):")
            import difflib
            for line in difflib.unified_diff(
                na.splitlines(), nb.splitlines(), lineterm="", fromfile=refs[0][0], tofile=refs[1][0]
            ):
                if line.startswith(("+", "-", "@")):
                    print(line[:200])


if __name__ == "__main__":
    main()
