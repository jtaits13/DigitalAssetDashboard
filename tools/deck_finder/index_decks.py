"""Index a local folder of PowerPoint files for keyword slide search."""

from __future__ import annotations

import json
import posixpath
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

TOOL_DIR = Path(__file__).resolve().parent
CONFIG_PATH = TOOL_DIR / "config.json"
CONFIG_EXAMPLE_PATH = TOOL_DIR / "config.example.json"
DATA_DIR = TOOL_DIR / "data"
CATALOG_PATH = DATA_DIR / "catalog.json"

PPTX_SUFFIXES = {".pptx", ".pptm"}
PPT_SUFFIXES = {".ppt", ".pps"}
SKIP_PREFIXES = ("~$", ".")

NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_OFFICE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_SLIDE = f"{NS_OFFICE_REL}/slide"
REL_NOTES = f"{NS_OFFICE_REL}/notesSlide"

_STEM_NOISE = re.compile(
    r"\b(final|copy|updated|draft|latest|new|reviewed)\b",
    re.IGNORECASE,
)
_VERSION = re.compile(r"\b(?:v(?:ersion)?\s*)(\d+)\b", re.IGNORECASE)
_DATE_YMD = re.compile(r"\b\d{4}[-_.]?\d{2}[-_.]?\d{2}\b")
_DATE_8 = re.compile(r"\b\d{8}\b")
_COPY_MARK = re.compile(r"\(\s*copy(?:\s+\d+)?\s*\)", re.IGNORECASE)
_TRAILING_NUM = re.compile(r"[\s._-]+\d+$")
_TOKEN = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def local_tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_xml(data: bytes) -> ET.Element:
    return ET.fromstring(data)


def zip_join(base_dir: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/").replace("\\", "/")
    return posixpath.normpath(posixpath.join(base_dir, target.replace("\\", "/")))


def text_of(el: ET.Element | None) -> str:
    if el is None or el.text is None:
        return ""
    return str(el.text).strip()


def iter_paragraph_text(root: ET.Element) -> list[str]:
    paras: list[str] = []
    for el in root.iter():
        if local_tag(el.tag) != "p":
            continue
        if "drawingml" not in (el.tag or ""):
            continue
        runs: list[str] = []
        for child in el.iter():
            if local_tag(child.tag) == "t" and child.text:
                runs.append(child.text)
        joined = "".join(runs).strip()
        if joined:
            paras.append(joined)
    return paras


def shape_ph_type(shape: ET.Element) -> str | None:
    for el in shape.iter():
        if local_tag(el.tag) == "ph":
            raw = el.attrib.get("type")
            if raw:
                return raw
            for key, val in el.attrib.items():
                if local_tag(key) == "type":
                    return val
    return None


def extract_slide_fields(slide_root: ET.Element) -> tuple[str, str]:
    title_parts: list[str] = []
    body_parts: list[str] = []
    for el in slide_root.iter():
        if local_tag(el.tag) != "sp":
            continue
        ph = shape_ph_type(el)
        paras = iter_paragraph_text(el)
        if not paras:
            continue
        if ph in {"title", "ctrTitle", "subTitle"}:
            title_parts.extend(paras)
        else:
            body_parts.extend(paras)
    title = " ".join(title_parts).strip()
    body = "\n".join(body_parts).strip()
    if not title:
        all_paras = iter_paragraph_text(slide_root)
        if all_paras:
            title = all_paras[0]
            rest = all_paras[1:]
            if not body:
                body = "\n".join(rest).strip()
    return title, body


def extract_notes_text(notes_root: ET.Element) -> str:
    notes: list[str] = []
    for el in notes_root.iter():
        if local_tag(el.tag) != "sp":
            continue
        ph = shape_ph_type(el)
        if ph in {"sldImg", "sldNum", "hdr", "ftr", "dt"}:
            continue
        if ph not in {None, "body"}:
            continue
        paras = iter_paragraph_text(el)
        for para in paras:
            low = para.lower()
            if low in {"click to add notes", "notes"}:
                continue
            notes.append(para)
    return "\n".join(notes).strip()


def read_core_props(zf: zipfile.ZipFile) -> dict[str, str]:
    out = {"title": "", "author": "", "modified": ""}
    names = {name.lower(): name for name in zf.namelist()}
    core_name = names.get("docprops/core.xml")
    if not core_name:
        return out
    try:
        root = parse_xml(zf.read(core_name))
    except ET.ParseError:
        return out
    for el in root.iter():
        tag = local_tag(el.tag)
        if tag == "title" and not out["title"]:
            out["title"] = text_of(el)
        elif tag == "creator" and not out["author"]:
            out["author"] = text_of(el)
        elif tag == "modified" and not out["modified"]:
            out["modified"] = text_of(el)
    return out


def relationship_map(zf: zipfile.ZipFile, rels_path: str) -> list[tuple[str, str, str]]:
    if rels_path not in zf.namelist():
        return []
    try:
        root = parse_xml(zf.read(rels_path))
    except ET.ParseError:
        return []
    rows: list[tuple[str, str, str]] = []
    for el in root.iter():
        if local_tag(el.tag) != "Relationship":
            continue
        rid = el.attrib.get("Id") or ""
        rel_type = el.attrib.get("Type") or ""
        target = el.attrib.get("Target") or ""
        if rid and target:
            rows.append((rid, rel_type, target))
    return rows


def slide_targets_in_order(zf: zipfile.ZipFile) -> list[str]:
    names = set(zf.namelist())
    rels = {rid: (typ, target) for rid, typ, target in relationship_map(zf, "ppt/_rels/presentation.xml.rels")}
    ordered: list[str] = []
    if "ppt/presentation.xml" in names:
        try:
            root = parse_xml(zf.read("ppt/presentation.xml"))
            for el in root.iter():
                if local_tag(el.tag) != "sldId":
                    continue
                rid = ""
                for key, val in el.attrib.items():
                    if local_tag(key) == "id" and key != "id":
                        rid = val
                        break
                    if key.endswith("}id") and "relationships" in key:
                        rid = val
                        break
                if not rid:
                    rid = el.attrib.get(f"{{{NS_OFFICE_REL}}}id") or ""
                info = rels.get(rid)
                if not info:
                    continue
                _typ, target = info
                path = zip_join("ppt", target)
                if path in names:
                    ordered.append(path)
        except ET.ParseError:
            ordered = []
    if ordered:
        return ordered
    slides = sorted(
        name for name in names if name.startswith("ppt/slides/slide") and name.endswith(".xml")
    )
    return slides


def notes_path_for_slide(zf: zipfile.ZipFile, slide_path: str) -> str | None:
    parent, fname = posixpath.split(slide_path)
    rels_path = f"{parent}/_rels/{fname}.rels"
    for _rid, typ, target in relationship_map(zf, rels_path):
        if typ != REL_NOTES and not typ.endswith("/notesSlide"):
            continue
        path = zip_join(parent, target)
        if path in zf.namelist():
            return path
    return None


def extract_pptx(path: Path) -> list[dict[str, Any]]:
    slides: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as zf:
        for number, slide_path in enumerate(slide_targets_in_order(zf), start=1):
            try:
                root = parse_xml(zf.read(slide_path))
            except (KeyError, ET.ParseError):
                slides.append(
                    {"number": number, "title": "", "body": "", "notes": "", "text": ""}
                )
                continue
            title, body = extract_slide_fields(root)
            notes = ""
            notes_path = notes_path_for_slide(zf, slide_path)
            if notes_path:
                try:
                    notes = extract_notes_text(parse_xml(zf.read(notes_path)))
                except ET.ParseError:
                    notes = ""
            blob = "\n".join(part for part in (title, body, notes) if part)
            slides.append(
                {
                    "number": number,
                    "title": title[:500],
                    "body": body[:8000],
                    "notes": notes[:4000],
                    "text": blob[:12000],
                }
            )
    if not slides:
        slides.append({"number": 1, "title": "", "body": "", "notes": "", "text": ""})
    return slides


def iso_from_mtime(mtime: float) -> str:
    return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()


def parse_office_modified(raw: str) -> datetime | None:
    if not raw:
        return None
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def version_number(filename: str) -> int:
    match = _VERSION.search(filename)
    return int(match.group(1)) if match else 0


def normalize_stem(filename: str) -> str:
    stem = Path(filename).stem.lower()
    stem = _COPY_MARK.sub(" ", stem)
    stem = _DATE_YMD.sub(" ", stem)
    stem = _DATE_8.sub(" ", stem)
    stem = _VERSION.sub(" ", stem)
    stem = _STEM_NOISE.sub(" ", stem)
    stem = re.sub(r"[_\-]+", " ", stem)
    stem = _TRAILING_NUM.sub("", stem)
    stem = re.sub(r"[^a-z0-9]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem or Path(filename).stem.lower()


def family_id_for(rel_path: str, filename: str) -> str:
    parent = posixpath.dirname(rel_path.replace("\\", "/")).lower()
    return f"{parent}/{normalize_stem(filename)}".strip("/")


def assign_families(decks: list[dict[str, Any]]) -> None:
    groups: dict[str, list[dict[str, Any]]] = {}
    for deck in decks:
        fid = family_id_for(deck["rel_path"], deck["filename"])
        deck["family_id"] = fid
        groups.setdefault(fid, []).append(deck)

    def sort_key(deck: dict[str, Any]) -> tuple:
        office = parse_office_modified(deck.get("modified") or "")
        fs = parse_office_modified(deck.get("fs_modified") or "")
        newest = office or fs or datetime.min.replace(tzinfo=timezone.utc)
        return (newest, version_number(deck["filename"]), deck.get("size") or 0)

    for fid, members in groups.items():
        ranked = sorted(members, key=sort_key, reverse=True)
        latest_id = ranked[0]["id"]
        for deck in members:
            deck["family_size"] = len(members)
            deck["is_latest"] = deck["id"] == latest_id
            deck["version_number"] = version_number(deck["filename"])


def load_config() -> dict[str, Any]:
    if CONFIG_PATH.is_file():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    elif CONFIG_EXAMPLE_PATH.is_file():
        data = json.loads(CONFIG_EXAMPLE_PATH.read_text(encoding="utf-8"))
        data["deck_folder"] = ""
    else:
        data = {"deck_folder": "", "port": 8765}
    data.setdefault("port", 8765)
    data.setdefault("deck_folder", "")
    return data


def save_config(deck_folder: str, port: int | None = None) -> dict[str, Any]:
    current = load_config()
    current["deck_folder"] = str(Path(deck_folder).expanduser().resolve()) if deck_folder else ""
    if port is not None:
        current["port"] = int(port)
    CONFIG_PATH.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    return current


def iter_deck_files(folder: Path) -> list[Path]:
    files: list[Path] = []
    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        if path.name.startswith(SKIP_PREFIXES):
            continue
        suffix = path.suffix.lower()
        if suffix in PPTX_SUFFIXES or suffix in PPT_SUFFIXES:
            files.append(path)
    return sorted(files)


def relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def index_file(path: Path, root: Path) -> dict[str, Any]:
    rel = relative_posix(path, root)
    stat = path.stat()
    suffix = path.suffix.lower()
    core = {"title": "", "author": "", "modified": ""}
    slides: list[dict[str, Any]] = []
    error = ""
    if suffix in PPTX_SUFFIXES:
        try:
            with zipfile.ZipFile(path) as zf:
                core = read_core_props(zf)
            slides = extract_pptx(path)
        except (zipfile.BadZipFile, OSError, KeyError, ET.ParseError) as exc:
            error = str(exc)
            slides = [{"number": 1, "title": "", "body": "", "notes": "", "text": ""}]
    else:
        slides = [{"number": 1, "title": "", "body": "", "notes": "", "text": ""}]
        error = "legacy .ppt — filename and dates only"

    inferred = core.get("title") or (slides[0]["title"] if slides else "") or path.stem
    folder = posixpath.dirname(rel)
    return {
        "id": rel,
        "path": str(path.resolve()),
        "rel_path": rel,
        "filename": path.name,
        "folder": folder,
        "title": inferred,
        "author": core.get("author") or "",
        "modified": core.get("modified") or "",
        "fs_modified": iso_from_mtime(stat.st_mtime),
        "size": stat.st_size,
        "ext": suffix,
        "slide_count": len(slides),
        "slides": slides,
        "error": error,
    }


def build_catalog(folder: Path) -> dict[str, Any]:
    folder = folder.resolve()
    decks = [index_file(path, folder) for path in iter_deck_files(folder)]
    assign_families(decks)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "deck_folder": str(folder),
        "deck_count": len(decks),
        "slide_count": sum(int(d.get("slide_count") or 0) for d in decks),
        "decks": decks,
    }


def write_catalog(catalog: dict[str, Any], path: Path | None = None) -> Path:
    dest = path or CATALOG_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dest


def load_catalog(path: Path | None = None) -> dict[str, Any] | None:
    dest = path or CATALOG_PATH
    if not dest.is_file():
        return None
    return json.loads(dest.read_text(encoding="utf-8"))


def tokenize_query(query: str) -> list[str]:
    parts = [p.lower() for p in _TOKEN.findall(query or "")]
    return [p for p in parts if len(p) >= 2 or p.isdigit()]


def _haystack(*parts: str) -> str:
    return "\n".join(p for p in parts if p).lower()


def score_slide(deck: dict[str, Any], slide: dict[str, Any], tokens: list[str]) -> int | None:
    filename = deck.get("filename") or ""
    folder = deck.get("folder") or ""
    deck_title = deck.get("title") or ""
    title = slide.get("title") or ""
    body = slide.get("body") or ""
    notes = slide.get("notes") or ""
    score = 0
    for token in tokens:
        in_title = token in title.lower()
        in_body = token in body.lower()
        in_notes = token in notes.lower()
        in_file = token in filename.lower() or token in folder.lower() or token in deck_title.lower()
        if not (in_title or in_body or in_notes or in_file):
            return None
        if in_title:
            score += 12
        elif in_file:
            score += 7
        elif in_body:
            score += 4
        elif in_notes:
            score += 2
    recency = parse_office_modified(deck.get("modified") or "") or parse_office_modified(
        deck.get("fs_modified") or ""
    )
    if recency:
        days = max(0, (datetime.now(timezone.utc) - recency).days)
        score += max(0, 30 - min(days, 30))
    if deck.get("is_latest"):
        score += 3
    return score


def html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def highlight_snippet(text: str, tokens: list[str], radius: int = 90) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    if not clean:
        return ""
    low = clean.lower()
    best = -1
    for token in tokens:
        idx = low.find(token)
        if idx != -1 and (best == -1 or idx < best):
            best = idx
    if best == -1:
        clipped = clean[: radius * 2]
        return html_escape(clipped)
    start = max(0, best - radius)
    end = min(len(clean), best + len(tokens[0]) + radius)
    snippet = clean[start:end]
    prefix = "…" if start else ""
    suffix = "…" if end < len(clean) else ""
    escaped = html_escape(snippet)
    for token in sorted(set(tokens), key=len, reverse=True):
        escaped = re.sub(
            re.escape(html_escape(token)),
            lambda m: f"<mark>{m.group(0)}</mark>",
            escaped,
            flags=re.IGNORECASE,
        )
    return f"{prefix}{escaped}{suffix}"


def deck_public(deck: dict[str, Any], include_slides: bool = False) -> dict[str, Any]:
    row = {
        "id": deck["id"],
        "rel_path": deck["rel_path"],
        "filename": deck["filename"],
        "folder": deck.get("folder") or "",
        "title": deck.get("title") or deck["filename"],
        "author": deck.get("author") or "",
        "modified": deck.get("modified") or "",
        "fs_modified": deck.get("fs_modified") or "",
        "size": deck.get("size") or 0,
        "ext": deck.get("ext") or "",
        "slide_count": deck.get("slide_count") or 0,
        "family_id": deck.get("family_id") or "",
        "family_size": deck.get("family_size") or 1,
        "is_latest": bool(deck.get("is_latest")),
        "error": deck.get("error") or "",
    }
    if include_slides:
        row["slides"] = [
            {
                "number": s.get("number"),
                "title": s.get("title") or "",
            }
            for s in deck.get("slides") or []
        ]
    return row


def search_catalog(
    catalog: dict[str, Any],
    query: str,
    *,
    latest_only: bool = True,
    folder: str = "",
    modified_after: str = "",
) -> dict[str, Any]:
    tokens = tokenize_query(query)
    after = parse_office_modified(modified_after) if modified_after else None
    folder_norm = folder.replace("\\", "/").strip().lower()
    groups: list[dict[str, Any]] = []

    for deck in catalog.get("decks") or []:
        if latest_only and not deck.get("is_latest"):
            continue
        deck_folder = (deck.get("folder") or "").replace("\\", "/").lower()
        if folder_norm and deck_folder != folder_norm and not deck_folder.startswith(folder_norm + "/"):
            continue
        modified = parse_office_modified(deck.get("modified") or "") or parse_office_modified(
            deck.get("fs_modified") or ""
        )
        if after and modified and modified < after:
            continue

        slide_hits: list[dict[str, Any]] = []
        best = 0
        file_blob = _haystack(
            deck.get("filename") or "",
            deck.get("folder") or "",
            deck.get("title") or "",
        )
        if tokens:
            for slide in deck.get("slides") or []:
                scored = score_slide(deck, slide, tokens)
                if scored is None:
                    continue
                content_blob = _haystack(
                    slide.get("title") or "",
                    slide.get("body") or "",
                    slide.get("notes") or "",
                )
                if not any(token in content_blob for token in tokens):
                    continue
                snippet_src = slide.get("body") or slide.get("title") or slide.get("notes") or ""
                if not any(token in snippet_src.lower() for token in tokens):
                    snippet_src = content_blob
                slide_hits.append(
                    {
                        "number": slide.get("number"),
                        "title": slide.get("title") or f"Slide {slide.get('number')}",
                        "score": scored,
                        "snippet_html": highlight_snippet(
                            snippet_src or deck.get("filename") or "",
                            tokens,
                        ),
                    }
                )
                best = max(best, scored)
            if not slide_hits:
                if not all(token in file_blob for token in tokens):
                    continue
                best = 7 * len(tokens)
            else:
                slide_hits.sort(key=lambda h: (-int(h["score"]), int(h["number"] or 0)))
        groups.append(
            {
                "deck": deck_public(deck, include_slides=not tokens),
                "score": best,
                "hits": slide_hits,
            }
        )

    if tokens:
        groups.sort(
            key=lambda g: (int(g["score"]), g["deck"].get("fs_modified") or ""),
            reverse=True,
        )
    else:
        groups.sort(key=lambda g: g["deck"].get("fs_modified") or "", reverse=True)

    folders = sorted(
        {
            (d.get("folder") or "").replace("\\", "/")
            for d in catalog.get("decks") or []
            if d.get("folder")
        }
    )
    return {
        "query": query,
        "tokens": tokens,
        "latest_only": latest_only,
        "result_count": len(groups),
        "slide_hit_count": sum(len(g["hits"]) for g in groups),
        "folders": folders,
        "groups": groups,
    }


def reindex(deck_folder: str | None = None) -> dict[str, Any]:
    config = load_config()
    folder_raw = deck_folder or config.get("deck_folder") or ""
    folder = Path(folder_raw).expanduser()
    if not folder_raw or not folder.is_dir():
        raise FileNotFoundError("Set deck_folder to an existing directory before indexing.")
    if deck_folder:
        save_config(str(folder))
    catalog = build_catalog(folder)
    write_catalog(catalog)
    return catalog


def main() -> int:
    catalog = reindex()
    print(f"Indexed {catalog['deck_count']} decks / {catalog['slide_count']} slides")
    print(f"Wrote {CATALOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
