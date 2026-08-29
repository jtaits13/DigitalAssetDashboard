from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL_DIR = ROOT / "Powerpoint Search Project"
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import index_decks  # noqa: E402
import serve  # noqa: E402

NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def _shape(shape_id: int, name: str, ph_type: str, paragraphs: list[str]) -> str:
    runs = "".join(
        f"<a:p><a:r><a:t>{text}</a:t></a:r></a:p>" for text in paragraphs
    )
    ph = f'<p:ph type="{ph_type}"/>' if ph_type else "<p:ph/>"
    return f"""
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr id="{shape_id}" name="{name}"/>
          <p:cNvSpPr/>
          <p:nvPr>{ph}</p:nvPr>
        </p:nvSpPr>
        <p:spPr/>
        <p:txBody>
          <a:bodyPr/>
          <a:lstStyle/>
          {runs}
        </p:txBody>
      </p:sp>
    """


def _slide_xml(title: str, body_lines: list[str]) -> str:
    body = _shape(3, "Content", "body", body_lines)
    title_shape = _shape(2, "Title", "ctrTitle", [title])
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr/>
      {title_shape}
      {body}
    </p:spTree>
  </p:cSld>
</p:sld>
"""


def _notes_xml(notes: str) -> str:
    body = _shape(2, "Notes", "body", [notes])
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:notes xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr/>
      {body}
    </p:spTree>
  </p:cSld>
</p:notes>
"""


def write_pptx(
    path: Path,
    *,
    title: str,
    slides: list[tuple[str, list[str]]],
    notes: dict[int, str] | None = None,
    author: str = "Tester",
    modified: str = "2026-08-01T12:00:00Z",
) -> Path:
    notes = notes or {}
    sld_ids = []
    rels = []
    files: dict[str, str] = {}
    overrides = [
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
    ]
    for i, (slide_title, body_lines) in enumerate(slides, start=1):
        rid = f"rId{i + 1}"
        sld_ids.append(f'<p:sldId id="{255 + i}" r:id="{rid}"/>')
        rels.append(
            f'<Relationship Id="{rid}" Type="{NS_R}/slide" Target="slides/slide{i}.xml"/>'
        )
        files[f"ppt/slides/slide{i}.xml"] = _slide_xml(slide_title, body_lines)
        overrides.append(
            f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        )
        slide_rels = []
        if i in notes:
            slide_rels.append(
                f'<Relationship Id="rId1" Type="{NS_R}/notesSlide" Target="../notesSlides/notesSlide{i}.xml"/>'
            )
            files[f"ppt/notesSlides/notesSlide{i}.xml"] = _notes_xml(notes[i])
            overrides.append(
                f'<Override PartName="/ppt/notesSlides/notesSlide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>'
            )
        if slide_rels:
            files[f"ppt/slides/_rels/slide{i}.xml.rels"] = (
                f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<Relationships xmlns="{NS_REL}">{"".join(slide_rels)}</Relationships>'
            )

    files["[Content_Types].xml"] = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  {"".join(overrides)}
</Types>
"""
    files["_rels/.rels"] = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{NS_REL}">
  <Relationship Id="rId1" Type="{NS_R}/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>
"""
    files["docProps/core.xml"] = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{title}</dc:title>
  <dc:creator>{author}</dc:creator>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{modified}</dcterms:modified>
</cp:coreProperties>
"""
    files["ppt/presentation.xml"] = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">
  <p:sldIdLst>
    {"".join(sld_ids)}
  </p:sldIdLst>
  <p:sldSz cx="9144000" cy="6858000"/>
</p:presentation>
"""
    files["ppt/_rels/presentation.xml.rels"] = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{NS_REL}">
  {"".join(rels)}
</Relationships>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        for name, xml in files.items():
            zf.writestr(name, xml)
    return path


@pytest.fixture
def deck_folder(tmp_path: Path) -> Path:
    write_pptx(
        tmp_path / "RWA" / "Tokenized Treasuries Overview v1.pptx",
        title="Tokenized Treasuries Overview",
        slides=[
            ("Tokenized Treasuries Overview", ["Agenda", "Market map"]),
            ("BlackRock BUIDL AUM Q2", ["BUIDL AUM rose in Q2", "Share vs money funds"]),
        ],
        notes={2: "Use this slide for client emails on BUIDL."},
        modified="2026-01-01T00:00:00Z",
    )
    write_pptx(
        tmp_path / "RWA" / "Tokenized Treasuries Overview v2.pptx",
        title="Tokenized Treasuries Overview",
        slides=[
            ("Tokenized Treasuries Overview", ["Updated agenda"]),
            ("BlackRock BUIDL AUM Q2", ["BUIDL AUM rose in Q2", "Latest comparison vs MMF yield"]),
            ("T-bill comparison vs MMF yield", ["Onchain T-bills vs tokenized MMF yield"]),
        ],
        notes={2: "Updated talking points for Q2 emails."},
        modified="2026-08-01T00:00:00Z",
    )
    write_pptx(
        tmp_path / "Stablecoins" / "Stablecoin Flows.pptx",
        title="Stablecoin Flows",
        slides=[("USDT vs USDC", ["Net issuance last week"])],
        modified="2026-07-15T00:00:00Z",
    )
    return tmp_path


def test_extracts_slide_text_and_notes(deck_folder: Path) -> None:
    catalog = index_decks.build_catalog(deck_folder)
    v2 = next(d for d in catalog["decks"] if d["filename"].endswith("v2.pptx"))
    assert v2["slide_count"] == 3
    slide2 = v2["slides"][1]
    assert "BUIDL" in slide2["title"]
    assert "MMF yield" in slide2["body"]
    assert "talking points" in slide2["notes"]
    assert v2["author"] == "Tester"


def test_latest_version_grouped_by_family(deck_folder: Path) -> None:
    catalog = index_decks.build_catalog(deck_folder)
    rwa = [d for d in catalog["decks"] if d["folder"] == "RWA"]
    assert len(rwa) == 2
    assert {d["family_id"] for d in rwa} == {"rwa/tokenized treasuries overview"}
    latest = next(d for d in rwa if d["is_latest"])
    older = next(d for d in rwa if not d["is_latest"])
    assert latest["filename"].endswith("v2.pptx")
    assert older["filename"].endswith("v1.pptx")
    assert latest["family_size"] == 2


def test_keyword_search_finds_slide_not_just_deck(deck_folder: Path) -> None:
    catalog = index_decks.build_catalog(deck_folder)
    result = index_decks.search_catalog(catalog, "BlackRock BUIDL AUM Q2", latest_only=True)
    assert result["result_count"] == 1
    group = result["groups"][0]
    assert group["deck"]["filename"].endswith("v2.pptx")
    numbers = [hit["number"] for hit in group["hits"]]
    assert 2 in numbers
    assert "<mark>" in group["hits"][0]["snippet_html"]


def test_latest_only_hides_older_copy(deck_folder: Path) -> None:
    catalog = index_decks.build_catalog(deck_folder)
    hidden = index_decks.search_catalog(catalog, "BUIDL", latest_only=True)
    shown = index_decks.search_catalog(catalog, "BUIDL", latest_only=False)
    assert hidden["result_count"] == 1
    assert shown["result_count"] == 1
    assert shown["deck_hit_count"] == 2
    assert shown["groups"][0]["deck"]["filename"].endswith("v2.pptx")
    assert shown["groups"][0]["older"][0]["deck"]["filename"].endswith("v1.pptx")


def test_browse_nests_older_versions_together(deck_folder: Path) -> None:
    catalog = index_decks.build_catalog(deck_folder)
    result = index_decks.search_catalog(catalog, "", latest_only=False)
    assert result["result_count"] == 2
    assert result["deck_hit_count"] == 3
    treasuries = next(g for g in result["groups"] if "Treasuries" in g["deck"]["title"])
    assert treasuries["deck"]["filename"].endswith("v2.pptx")
    assert len(treasuries["older"]) == 1
    assert treasuries["older"][0]["deck"]["filename"].endswith("v1.pptx")


def test_and_query_requires_all_tokens(deck_folder: Path) -> None:
    catalog = index_decks.build_catalog(deck_folder)
    miss = index_decks.search_catalog(catalog, "BUIDL bitcoin", latest_only=False)
    assert miss["result_count"] == 0
    hit = index_decks.search_catalog(catalog, "T-bill MMF yield", latest_only=True)
    assert hit["result_count"] == 1
    assert hit["groups"][0]["hits"][0]["number"] == 3


def test_open_rejects_path_outside_folder(tmp_path: Path) -> None:
    root = tmp_path / "decks"
    root.mkdir()
    outside = tmp_path / "secret.pptx"
    outside.write_bytes(b"nope")
    with pytest.raises(PermissionError):
        serve.resolved_under_root(root, str(outside))


def test_reindex_roundtrip(deck_folder: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    catalog_path = tmp_path / "catalog.json"
    monkeypatch.setattr(index_decks, "CATALOG_PATH", catalog_path)
    monkeypatch.setattr(index_decks, "CONFIG_PATH", tmp_path / "config.json")
    index_decks.save_config(str(deck_folder), port=8765)
    catalog = index_decks.reindex()
    saved = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert saved["deck_count"] == catalog["deck_count"] == 3
    assert saved["slide_count"] == 6
