"""Local HTTP server for the PowerPoint slide/deck finder."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import index_decks  # noqa: E402

STATIC_DIR = TOOL_DIR / "static"
HTML_NAME = "deck-finder.html"


def _json_bytes(payload: object, status: int = 200) -> tuple[int, bytes, str]:
    return status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8"


def _error(message: str, status: int = 400) -> tuple[int, bytes, str]:
    return _json_bytes({"ok": False, "error": message}, status)


def resolved_under_root(root: Path, rel_or_abs: str) -> Path:
    root = root.resolve()
    raw = Path(rel_or_abs)
    candidate = raw.resolve() if raw.is_absolute() else (root / rel_or_abs).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PermissionError("Path is outside the configured deck folder.") from exc
    return candidate


def open_powerpoint_at_slide(path: Path, slide: int | None) -> str:
    path_str = str(path.resolve())
    if os.name != "nt":
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.Popen([opener, path_str], close_fds=True)
        return "opened"
    os.startfile(path_str)  # type: ignore[attr-defined]
    if not slide:
        return "opened"
    escaped = path_str.replace("'", "''")
    script = f"""
$ErrorActionPreference = 'Stop'
$target = '{escaped}'
$slideNum = {int(slide)}
$ppt = $null
try {{
  $ppt = [Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application')
}} catch {{
  $ppt = New-Object -ComObject PowerPoint.Application
}}
$ppt.Visible = -1
$deadline = (Get-Date).AddSeconds(15)
$pres = $null
do {{
  foreach ($p in @($ppt.Presentations)) {{
    if ($p.FullName -eq $target) {{ $pres = $p; break }}
  }}
  if ($null -eq $pres) {{ Start-Sleep -Milliseconds 400 }}
}} while (($null -eq $pres) -and ((Get-Date) -lt $deadline))
if ($null -eq $pres) {{
  $pres = $ppt.Presentations.Open($target, 0, 0, -1)
}}
$ppt.Activate()
Start-Sleep -Milliseconds 300
try {{
  $ppt.ActiveWindow.View.GotoSlide($slideNum)
}} catch {{
  $pres.Slides.Item($slideNum).Select()
}}
"""
    subprocess.Popen(
        ["powershell", "-NoProfile", "-STA", "-WindowStyle", "Hidden", "-Command", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    return "opened-at-slide"


def status_payload() -> dict:
    config = index_decks.load_config()
    folder = Path(config.get("deck_folder") or "")
    catalog = index_decks.load_catalog()
    folder_ok = bool(config.get("deck_folder")) and folder.is_dir()
    folders: list[str] = []
    if catalog:
        folders = sorted(
            {
                (d.get("folder") or "").replace("\\", "/")
                for d in catalog.get("decks") or []
                if d.get("folder")
            }
        )
    return {
        "ok": True,
        "configured": folder_ok,
        "deck_folder": str(folder) if folder_ok else (config.get("deck_folder") or ""),
        "port": int(config.get("port") or 8765),
        "catalog_exists": catalog is not None,
        "generated_at": (catalog or {}).get("generated_at") or "",
        "deck_count": (catalog or {}).get("deck_count") or 0,
        "slide_count": (catalog or {}).get("slide_count") or 0,
        "folders": folders,
        "example_config": str(index_decks.CONFIG_EXAMPLE_PATH),
    }


class DeckFinderHandler(BaseHTTPRequestHandler):
    server_version = "DeckFinder/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON object required")
        return data

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path in {"/", "/index.html"}:
                html_path = STATIC_DIR / HTML_NAME
                body = html_path.read_bytes()
                self._send(200, body, "text/html; charset=utf-8")
                return
            if path == "/api/status":
                self._send(*_json_bytes(status_payload()))
                return
            if path == "/api/search":
                qs = parse_qs(parsed.query)
                query = (qs.get("q") or [""])[0]
                folder = (qs.get("folder") or [""])[0]
                latest = (qs.get("latest_only") or ["1"])[0].lower() not in {"0", "false", "no"}
                modified_after = (qs.get("modified_after") or [""])[0]
                catalog = index_decks.load_catalog()
                if catalog is None:
                    self._send(*_error("No catalog yet. Re-index the folder first.", 404))
                    return
                result = index_decks.search_catalog(
                    catalog,
                    query,
                    latest_only=latest,
                    folder=folder,
                    modified_after=modified_after,
                )
                self._send(*_json_bytes({"ok": True, **result}))
                return
            if path.startswith("/static/"):
                rel = path[len("/static/") :]
                target = (STATIC_DIR / rel).resolve()
                target.relative_to(STATIC_DIR.resolve())
                if not target.is_file():
                    self._send(*_error("Not found", 404))
                    return
                ctype = "text/html; charset=utf-8"
                if target.suffix == ".css":
                    ctype = "text/css; charset=utf-8"
                elif target.suffix == ".js":
                    ctype = "application/javascript; charset=utf-8"
                self._send(200, target.read_bytes(), ctype)
                return
            self._send(*_error("Not found", 404))
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self._send(*_error(str(exc), 500))

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            payload = self._read_json()
        except (ValueError, json.JSONDecodeError) as exc:
            self._send(*_error(f"Invalid JSON: {exc}"))
            return
        try:
            if path == "/api/config":
                folder = str(payload.get("deck_folder") or "").strip()
                if not folder:
                    self._send(*_error("deck_folder is required"))
                    return
                dest = Path(folder).expanduser()
                if not dest.is_dir():
                    self._send(*_error(f"Not a directory: {dest}"))
                    return
                index_decks.save_config(str(dest.resolve()))
                self._send(*_json_bytes({"ok": True, **status_payload()}))
                return
            if path == "/api/reindex":
                config = index_decks.load_config()
                folder = str(payload.get("deck_folder") or config.get("deck_folder") or "").strip()
                if folder:
                    dest = Path(folder).expanduser()
                    if not dest.is_dir():
                        self._send(*_error(f"Not a directory: {dest}"))
                        return
                    index_decks.save_config(str(dest.resolve()))
                catalog = index_decks.reindex()
                self._send(
                    *_json_bytes(
                        {
                            "ok": True,
                            "deck_count": catalog["deck_count"],
                            "slide_count": catalog["slide_count"],
                            "generated_at": catalog["generated_at"],
                            **status_payload(),
                        }
                    )
                )
                return
            if path == "/api/open":
                rel = str(payload.get("path") or payload.get("rel_path") or "").strip()
                slide_raw = payload.get("slide")
                slide = int(slide_raw) if slide_raw not in (None, "", 0, "0") else None
                config = index_decks.load_config()
                root = Path(config.get("deck_folder") or "")
                if not root.is_dir():
                    self._send(*_error("Deck folder is not configured.", 400))
                    return
                target = resolved_under_root(root, rel)
                if not target.is_file():
                    self._send(*_error(f"File not found: {target}", 404))
                    return
                how = open_powerpoint_at_slide(target, slide)
                self._send(*_json_bytes({"ok": True, "opened": how, "path": str(target), "slide": slide}))
                return
            self._send(*_error("Not found", 404))
        except PermissionError as exc:
            self._send(*_error(str(exc), 403))
        except FileNotFoundError as exc:
            self._send(*_error(str(exc), 400))
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self._send(*_error(str(exc), 500))


def main() -> int:
    config = index_decks.load_config()
    port = int(config.get("port") or 8765)
    server = ThreadingHTTPServer(("127.0.0.1", port), DeckFinderHandler)
    url = f"http://127.0.0.1:{port}/"
    print(f"Deck finder running at {url}")
    print("Set the PowerPoint folder in the page if this is the first run, then Re-index.")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
