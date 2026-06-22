#!/usr/bin/env python3
"""
Build the executive weekly newsletter and send it through the local Outlook client.

Requires Windows, Outlook installed, and: pip install pywin32

Usage:
  python scripts/send_weekly_newsletter_outlook.py
  python scripts/send_weekly_newsletter_outlook.py --draft   # save to Drafts (test)
  python scripts/send_weekly_newsletter_outlook.py --dry-run # build only, no Outlook

Environment:
  NEWSLETTER_TO_EMAIL   — recipient (default: jack.taitel@jpmchase.com)
  SITE_BASE_URL         — passed through to the newsletter builder

Task Scheduler (Monday 8:30 AM local):
  Run once to register tasks:
    powershell -ExecutionPolicy Bypass -File scripts/setup_weekly_newsletter_scheduler.ps1

  JPM Weekly Newsletter - Keep Awake   Monday 8:15 AM — block sleep through send window
  JPM Weekly Newsletter - Prep         Monday 8:25 AM — start Outlook
  JPM Weekly Newsletter                Monday 8:30 AM — build and send

  Optional auto-login (admin, stores password — see script warnings):
    powershell -ExecutionPolicy Bypass -File scripts/enable_windows_auto_logon.ps1

  The scheduled task must run while your Windows user session can access Outlook
  (logged in, or locked with an active session). Sleep/hibernate: wake timers can
  rouse the PC; shut down or the sign-in screen needs auto-login or manual sign-in.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_TO = "jack.taitel@jpmchase.com"
LOG_DIR = ROOT / "logs"


def _week_label(week_end: datetime) -> str:
    return week_end.strftime("%d %b %Y")


def _attachment_filename(week_end: datetime) -> str:
    return f"Digital Assets Weekly Newsletter {_week_label(week_end)}.html"


def _build_executive_html(*, outlook_body: bool = False) -> tuple[str, datetime]:
    import importlib.util

    builder_path = ROOT / "scripts" / "build_weekly_newsletter.py"
    spec = importlib.util.spec_from_file_location("build_weekly_newsletter", builder_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load newsletter builder from {builder_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    html, week_end = mod.build_newsletter_html(variant="executive", outlook_body=outlook_body)
    return html, week_end


def _get_outlook_application():
    try:
        import pythoncom  # type: ignore[import-untyped]
        import win32com.client  # type: ignore[import-untyped]
    except ImportError as exc:
        raise SystemExit(
            "pywin32 is required for Outlook send. Install with: pip install pywin32"
        ) from exc

    pythoncom.CoInitialize()
    try:
        return win32com.client.GetActiveObject("Outlook.Application")
    except Exception:
        pass
    try:
        return win32com.client.Dispatch("Outlook.Application")
    except Exception as exc:
        raise SystemExit(
            "Could not connect to Outlook. Open the classic Outlook desktop app, "
            "sign in, then retry. If a security prompt appears, choose Allow."
        ) from exc


OL_FORMAT_HTML = 2


def _send_via_outlook(
    *,
    to: str,
    subject: str,
    html_body: str,
    html_file: Path,
    attachment_display_name: str,
    draft: bool,
    attach_html: bool,
) -> None:
    outlook = _get_outlook_application()
    try:
        mail = outlook.CreateItem(0)  # olMailItem
    except Exception as exc:
        raise SystemExit(
            "Outlook blocked creating a mail item (Operation aborted). "
            "Open Outlook first, retry, and approve any 'program is trying to send email' prompt. "
            "In Outlook: File → Options → Trust Center → Programmatic Access → "
            "choose 'Never warn' or 'Warn with override' for testing."
        ) from exc
    mail.To = to
    mail.Subject = subject
    mail.BodyFormat = OL_FORMAT_HTML
    # Outlook-optimized HTML body; attachment carries the full formatted version.
    mail.HTMLBody = html_body
    if attach_html and html_file.is_file():
        att = mail.Attachments.Add(str(html_file.resolve()))
        att.DisplayName = attachment_display_name
    if draft:
        mail.Save()
        mail.Display(False)
        print(f"Saved draft for {to!r} — subject: {subject}")
        if attach_html:
            print(f"Attached: {attachment_display_name}")
    else:
        mail.Send()
        print(f"Sent to {to!r} — subject: {subject}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Send executive weekly newsletter via Outlook.")
    parser.add_argument(
        "--to",
        default=None,
        help=f"Recipient email (default: NEWSLETTER_TO_EMAIL or {DEFAULT_TO})",
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        help="Save to Outlook Drafts instead of sending (safe test).",
    )
    parser.add_argument(
        "--no-attach",
        action="store_true",
        help="Do not attach the .html file (inline body only).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build HTML only; do not open Outlook.",
    )
    parser.add_argument(
        "--update-attachment-mock",
        action="store_true",
        help="Also write static_home/mockups/weekly-newsletter-email-executive-mock.html.",
    )
    args = parser.parse_args()

    import os

    to = (args.to or os.environ.get("NEWSLETTER_TO_EMAIL") or DEFAULT_TO).strip()
    if not to:
        raise SystemExit("No recipient — set --to or NEWSLETTER_TO_EMAIL.")

    print("Building executive newsletter…")
    attachment_html, week_end = _build_executive_html(outlook_body=False)
    body_html, _ = _build_executive_html(outlook_body=True)
    week_label = _week_label(week_end)
    subject = f"Executive weekly brief — week ending {week_label}"
    attachment_name = _attachment_filename(week_end)

    out_path = ROOT / "static_home" / "mockups" / "weekly-newsletter-email-executive-mock.html"
    body_preview_path = ROOT / "static_home" / "mockups" / "weekly-newsletter-email-executive-outlook-body.html"
    attach_path = LOG_DIR / attachment_name
    body_preview_path.parent.mkdir(parents=True, exist_ok=True)
    body_preview_path.write_text(body_html, encoding="utf-8")
    print(f"Wrote Outlook body preview: {body_preview_path}")

    if args.update_attachment_mock:
        out_path.write_text(attachment_html, encoding="utf-8")
        print(f"Wrote attachment mock: {out_path}")
        attach_file = out_path
    else:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        attach_path.write_text(attachment_html, encoding="utf-8")
        attach_file = attach_path
        print(f"Wrote attachment: {attach_path}")

    if args.dry_run:
        print(f"Dry run — would send to {to!r} with subject: {subject}")
        return

    _send_via_outlook(
        to=to,
        subject=subject,
        html_body=body_html,
        html_file=attach_file,
        attachment_display_name=attachment_name,
        draft=args.draft,
        attach_html=not args.no_attach,
    )

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_line = (
        f"{datetime.now().isoformat(timespec='seconds')} "
        f"{'draft' if args.draft else 'sent'} to={to} subject={subject}\n"
    )
    (LOG_DIR / "newsletter-outlook-send.log").open("a", encoding="utf-8").write(log_line)


if __name__ == "__main__":
    main()
