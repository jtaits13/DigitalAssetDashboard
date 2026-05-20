#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "static_home"


def read(p: Path) -> str:
    raw = p.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252")


issues = []
for p in sorted(ROOT.rglob("*")):
    if p.suffix.lower() not in {".html", ".js", ".css"}:
        continue
    t = read(p)
    rel = p.relative_to(ROOT.parent)
    for i, line in enumerate(t.splitlines(), 1):
        if "? Back" in line or "? Explore" in line or "? RWA" in line:
            issues.append(f"{rel}:{i}: {line.strip()[:100]}")
        if "\ufffd" in line:
            issues.append(f"{rel}:{i}: U+FFFD {line.strip()[:80]}")
        if "headlines ?" in line:
            issues.append(f"{rel}:{i}: {line.strip()[:100]}")

for x in issues:
    print(x)
print("total", len(issues))
