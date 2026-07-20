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

Task Scheduler (Monday 8:40 AM local):
  Run once to register tasks:
    powershell -ExecutionPolicy Bypass -File scripts/setup_weekly_newsletter_scheduler.ps1

  JPM Weekly Newsletter - Keep Awake   Monday 8:25 AM — block sleep through send window
  JPM Weekly Newsletter - Prep         Monday 8:35 AM — start Outlook
  JPM Weekly Newsletter                Monday 8:40 AM — build and send (wake + missed-run)
  JPM Weekly Newsletter - Catch-up     At logon/unlock — send if Monday was missed

  Manual send: powershell -File scripts/run_weekly_newsletter_outlook.ps1 -Force
  Send state: logs/newsletter-last-send.json  Run log: logs/newsletter-outlook-run.log
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
    errors: list[str] = []
    for getter in (
        lambda: win32com.client.GetActiveObject("Outlook.Application"),
        lambda: win32com.client.gencache.EnsureDispatch("Outlook.Application"),
        lambda: win32com.client.Dispatch("Outlook.Application"),
    ):
        try:
            return getter()
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
    detail = "; ".join(errors) if errors else "unknown error"
    raise SystemExit(
        "Could not connect to classic Outlook desktop (OUTLOOK.EXE). "
        "Close the new Outlook app if it is open, open classic Outlook, sign in, then retry. "
        f"COM details: {detail}"
    )


OL_FORMAT_HTML = 2


def _encode_header(value: str) -> str:
    from email.header import Header

    return str(Header(value, "utf-8"))


def _write_compose_eml(
    *,
    to: str,
    subject: str,
    html_body: str,
    html_file: Path | None,
    attachment_display_name: str,
) -> Path:
    """Write a draft .eml Outlook can open when COM CreateItem is blocked."""
    import mimetypes
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = _encode_header(subject)
    msg["X-Unsent"] = "1"  # Outlook opens as an unsent compose window
    msg.set_content("HTML newsletter — view this message in HTML.")
    msg.add_alternative(html_body, subtype="html")
    if html_file is not None and html_file.is_file():
        data = html_file.read_bytes()
        ctype, _ = mimetypes.guess_type(attachment_display_name)
        maintype, subtype = (ctype or "text/html").split("/", 1)
        msg.add_attachment(
            data,
            maintype=maintype,
            subtype=subtype,
            filename=attachment_display_name,
        )
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    out = LOG_DIR / "newsletter-compose-fallback.eml"
    out.write_bytes(msg.as_bytes())
    return out


def _open_compose_fallback(
    *,
    to: str,
    subject: str,
    html_body: str,
    html_file: Path,
    attachment_display_name: str,
) -> None:
    import os
    import subprocess

    eml = _write_compose_eml(
        to=to,
        subject=subject,
        html_body=html_body,
        html_file=html_file,
        attachment_display_name=attachment_display_name,
    )
    print(f"COM send blocked — opening Outlook compose fallback: {eml}")
    print("Review the message in Outlook, then click Send.")
    try:
        os.startfile(str(eml))  # type: ignore[attr-defined]
    except Exception:
        subprocess.Popen(["cmd", "/c", "start", "", str(eml)], shell=False)


def _create_mail_item(outlook):
    import time

    last_exc: Exception | None = None
    for attempt in range(1, 4):
        try:
            return outlook.CreateItem(0)  # olMailItem
        except Exception as exc:
            last_exc = exc
            time.sleep(1.5 * attempt)
    assert last_exc is not None
    raise last_exc


def _send_via_outlook(
    *,
    to: str,
    subject: str,
    html_body: str,
    html_file: Path,
    attachment_display_name: str,
    draft: bool,
    attach_html: bool,
    allow_fallback: bool = True,
) -> str:
    """Send/draft via Outlook COM. Returns 'sent', 'draft', or 'fallback'."""
    outlook = _get_outlook_application()
    try:
        mail = _create_mail_item(outlook)
    except Exception as exc:
        if allow_fallback and not draft:
            _open_compose_fallback(
                to=to,
                subject=subject,
                html_body=html_body,
                html_file=html_file,
                attachment_display_name=attachment_display_name,
            )
            return "fallback"
        raise SystemExit(
            "Outlook blocked creating a mail item (Operation aborted).\n"
            "Usually this is classic Outlook Programmatic Access / antivirus guard.\n"
            "Fix (classic Outlook desktop):\n"
            "  1. File → Options → Trust Center → Trust Center Settings… → Programmatic Access\n"
            "  2. Choose 'Never warn me about suspicious activity' (or 'Warn me…' and click Allow)\n"
            "  3. If the options are greyed out, antivirus is controlling the guard — "
            "update Defender / corp AV, or ask IT to allow Outlook automation.\n"
            "  4. Use classic Outlook (OUTLOOK.EXE), not the new Outlook app.\n"
            "Then re-run: powershell -File scripts\\run_weekly_newsletter_outlook.ps1 -Force\n"
            f"COM detail: {type(exc).__name__}: {exc}"
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
        return "draft"
    try:
        mail.Send()
    except Exception as exc:
        # CreateItem worked but Send was blocked — leave the window open for a click.
        try:
            mail.Display(True)
        except Exception:
            pass
        if allow_fallback:
            print(
                "Outlook blocked Send() — compose window should be open; click Send manually. "
                f"({type(exc).__name__}: {exc})"
            )
            return "fallback"
        raise
    print(f"Sent to {to!r} — subject: {subject}")
    return "sent"


def _append_send_log(*, to: str, subject: str, draft: bool) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_line = (
        f"{datetime.now().isoformat(timespec='seconds')} "
        f"{'draft' if draft else 'sent'} to={to} subject={subject}\n"
    )
    log_path = LOG_DIR / "newsletter-outlook-send.log"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(log_line)
        fh.flush()


def _record_send_state(*, week_label: str, to: str, draft: bool) -> None:
    if draft:
        return
    try:
        from newsletter_send_state import write_send_state

        write_send_state(week_label=week_label, to=to, draft=draft)
    except Exception as exc:
        print(f"Warning: could not write send state: {exc}", file=sys.stderr)


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
        "--force",
        action="store_true",
        help="Send even if this week's newsletter was already sent.",
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

    if not args.force and not args.draft and not args.dry_run:
        try:
            from newsletter_send_state import already_sent_for_current_week

            if already_sent_for_current_week():
                print("Newsletter for the current week was already sent (use --force to resend).")
                return
        except Exception as exc:
            print(f"Warning: send-state check skipped: {exc}", file=sys.stderr)

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

    result = _send_via_outlook(
        to=to,
        subject=subject,
        html_body=body_html,
        html_file=attach_file,
        attachment_display_name=attachment_name,
        draft=args.draft,
        attach_html=not args.no_attach,
    )

    if result == "fallback":
        _append_send_log(to=to, subject=subject, draft=True)
        print(
            "Newsletter was opened for manual Send (COM automation blocked). "
            "Send state was not marked complete — re-run after you send, or use -Force later if needed."
        )
        return

    _append_send_log(to=to, subject=subject, draft=args.draft)
    _record_send_state(week_label=week_label, to=to, draft=args.draft)


if __name__ == "__main__":
    main()
