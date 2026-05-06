"""Jinja paths and shared template instance for the FastAPI app."""

from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

_BASE = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(_BASE / "templates"))
STATIC_DIR = _BASE / "static"
