#!/usr/bin/env python3
"""Serve the client-meeting intake page and persist one shared weekly table.

Run on a machine teammates can reach (your PC on the internal network, or an
internal server that can run Python):

  py -3 tools/client_meeting_updates/server.py

Then share http://<this-machine>:8765/
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from store import MeetingStore  # noqa: E402

MAX_BODY = 1_000_000


class IntakeHandler(SimpleHTTPRequestHandler):
    store: MeetingStore
    static_root: Path

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(self.static_root), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))

    def do_GET(self) -> None:
        if self._block_data_path():
            return
        parsed = urlparse(self.path)
        if parsed.path == "/api/week":
            self._api(self._get_week)
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self._block_data_path():
            return
        parsed = urlparse(self.path)
        if parsed.path == "/api/meetings":
            self._api(self._add_meeting)
            return
        if parsed.path == "/api/import":
            self._api(self._import_rows)
            return
        if parsed.path == "/api/week/reset":
            self._api(self._reset_week)
            return
        self.send_error(404, "Unknown API path")

    def do_PUT(self) -> None:
        if self._block_data_path():
            return
        parsed = urlparse(self.path)
        if parsed.path == "/api/meetings":
            self._api(self._update_meeting)
            return
        self.send_error(404, "Unknown API path")

    def do_DELETE(self) -> None:
        if self._block_data_path():
            return
        parsed = urlparse(self.path)
        if parsed.path == "/api/meetings":
            self._api(self._delete_meeting)
            return
        self.send_error(404, "Unknown API path")

    def _get_week(self) -> dict[str, Any]:
        store, meta = self.store.load()
        return {"store": store, **meta}

    def _add_meeting(self) -> dict[str, Any]:
        return {"store": self.store.add_row(self._read_json())}

    def _update_meeting(self) -> dict[str, Any]:
        return {"store": self.store.update_row(self._read_json())}

    def _delete_meeting(self) -> dict[str, Any]:
        row_id = (parse_qs(urlparse(self.path).query).get("id") or [""])[0]
        return {"store": self.store.delete_row(row_id)}

    def _import_rows(self) -> dict[str, Any]:
        payload = self._read_json()
        incoming = payload.get("rows") if isinstance(payload, dict) else payload
        if not isinstance(incoming, list):
            raise ValueError("Import body must be { rows: [...] }.")
        store, added = self.store.import_rows(incoming)
        return {"store": store, "addedCount": added}

    def _reset_week(self) -> dict[str, Any]:
        return {"store": self.store.reset_week()}

    def _api(self, fn: Callable[[], dict[str, Any]]) -> None:
        try:
            self._send_json(fn())
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
        except KeyError as exc:
            self._send_json({"error": exc.args[0] if exc.args else "Not found"}, status=404)

    def _block_data_path(self) -> bool:
        path = urlparse(self.path).path.lower()
        if path == "/data" or path.startswith("/data/"):
            self.send_error(404, "Not found")
            return True
        return False

    def _read_json(self) -> Any:
        length = int(self.headers.get("Content-Length") or "0")
        if length > MAX_BODY:
            raise ValueError("Request is too large.")
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON.") from exc

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str, port: int, data_dir: Path) -> None:
    IntakeHandler.store = MeetingStore(data_dir)
    IntakeHandler.static_root = ROOT
    server = ThreadingHTTPServer((host, port), IntakeHandler)
    shown_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    print(f"Client meeting intake: http://{shown_host}:{port}/", flush=True)
    print(f"Bound on {host}:{port} — teammates use this machine's internal hostname or IP.", flush=True)
    print("Everyone who opens this URL adds to the same weekly table.", flush=True)
    print("Stop with Ctrl+C.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Shared client-meeting intake server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--data-dir",
        default=str(ROOT / "data"),
        help="Directory for week.json (not served as a public file)",
    )
    args = parser.parse_args()
    run(args.host, args.port, Path(args.data_dir))


if __name__ == "__main__":
    main()
