"""Offline checks for the Power BI PBIP report-shell linkage."""

import json

import pytest

from src.phase5 import build_report_shell as shell
from src.phase5.build_report_shell import OUT, PREFIX


def test_pbip_shell_is_safe_to_bootstrap(tmp_path, monkeypatch):
    monkeypatch.setattr(shell, "OUT", tmp_path)
    shell.build_report_shell()
    before = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*.json")
    }
    with pytest.raises(FileExistsError):
        shell.build_report_shell()
    after = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*.json")
    }
    assert before == after


def test_pbip_links_report_and_semantic_model():
    project = json.loads((OUT / f"{PREFIX}.pbip").read_text(encoding="utf-8"))
    assert project["artifacts"][0]["report"]["path"] == f"{PREFIX}.Report"
    report = OUT / f"{PREFIX}.Report"
    definition = json.loads((report / "definition.pbir").read_text(encoding="utf-8"))
    ref = definition["datasetReference"]["byPath"]["path"]
    model = (report / ref).resolve()
    assert model == (OUT / f"{PREFIX}.SemanticModel").resolve()
    assert (model / "definition.pbism").is_file()
    assert (model / "definition" / "relationships.tmdl").is_file()


def test_fresh_bootstrap_has_one_blank_executive_page(tmp_path, monkeypatch):
    monkeypatch.setattr(shell, "OUT", tmp_path)
    shell.build_report_shell()
    folder = tmp_path / f"{PREFIX}.Report" / "definition"
    page_config = json.loads(
        (folder / "pages" / "ExecutiveOverview" / "page.json").read_text(encoding="utf-8")
    )
    pages = json.loads((folder / "pages" / "pages.json").read_text(encoding="utf-8"))
    assert pages["pageOrder"] == ["ExecutiveOverview"]
    assert page_config["width"] == 1280 and page_config["height"] == 720
    assert not list((folder / "pages").rglob("visual.json"))
    for f in folder.rglob("*.json"):
        assert isinstance(json.loads(f.read_text(encoding="utf-8")), dict)
