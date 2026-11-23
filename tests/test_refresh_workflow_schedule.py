"""The Pages refresh must survive GitHub dropping a delayed 6-hour cron."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def _cron_lines(text: str) -> list[str]:
    return [
        line.split("cron:", 1)[1].strip().strip('"').strip("'")
        for line in text.splitlines()
        if "cron:" in line and not line.strip().startswith("#")
    ]


def test_refresh_slots_are_daily_and_six_hours_apart() -> None:
    slots = sorted(WORKFLOWS.glob("refresh-static-home-slot-*.yml"))
    assert [path.name for path in slots] == [
        "refresh-static-home-slot-00.yml",
        "refresh-static-home-slot-06.yml",
        "refresh-static-home-slot-12.yml",
        "refresh-static-home-slot-18.yml",
    ]
    hours: list[int] = []
    for path in slots:
        text = path.read_text(encoding="utf-8")
        crons = _cron_lines(text)
        assert crons == [crons[0]]
        minute, hour, day, month, dow = crons[0].split()
        assert minute == "47"
        assert day == month == dow == "*"
        hours.append(int(hour))
        assert "uses: ./.github/workflows/refresh-static-home-data.yml" in text
        assert "secrets: inherit" in text
    assert hours == [0, 6, 12, 18]


def test_reusable_refresh_commits_snapshots_before_pages_deploy() -> None:
    text = (WORKFLOWS / "refresh-static-home-data.yml").read_text(encoding="utf-8")
    assert "workflow_call:" in text
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    commit_at = text.index("name: Commit refreshed JSON snapshots")
    upload_at = text.index("name: Upload static_home as site root")
    deploy_at = text.index("name: Deploy to GitHub Pages")
    retry_at = text.index("name: Retry deploy to GitHub Pages")
    assert commit_at < upload_at < deploy_at < retry_at
    assert "continue-on-error: true" in text
