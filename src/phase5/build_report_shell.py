"""Create an editable PBIP/PBIR report shell pointing at the M5.2 TMDL model.

The report page is intentionally blank; the approved Flight Network Atlas
x Ops Risk Intel theme and DAX will be applied after data refresh.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "powerbi"
PREFIX = "FlightOperations"
TEMPLATES = ROOT / "src" / "phase5" / "report_templates"


def dump_json(relative: str, value: dict) -> None:
    path = OUT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def build_report_shell() -> None:
    # Metadata and base theme come from Microsoft's CLI scaffold, not guessed schema.
    report_root = f"{PREFIX}.Report"
    # Never clobber a developed report when someone reruns the shell bootstrap.
    if (OUT / report_root).exists() or (OUT / f"{PREFIX}.pbip").exists():
        raise FileExistsError("Existing Power BI project must not be overwritten")
    dump_json(f"{report_root}/.platform", json.loads(
        (TEMPLATES / ".platform").read_text(encoding="utf-8")
    ))
    resource = OUT / report_root / "StaticResources" / "SharedResources" / "BaseThemes" / "Fluent2-CY26SU10.json"
    resource.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEMPLATES / "Fluent2-CY26SU10.json", resource)
    dump_json(
        f"{PREFIX}.pbip",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{PREFIX}.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )
    dump_json(
        f"{PREFIX}.Report/definition.pbir",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {
                "byPath": {"path": f"../{PREFIX}.SemanticModel"}
            },
        },
    )
    definition = f"{PREFIX}.Report/definition"
    dump_json(
        f"{definition}/version.json",
        json.loads((TEMPLATES / "version.json").read_text(encoding="utf-8")),
    )
    dump_json(
        f"{definition}/report.json",
        json.loads((TEMPLATES / "report.json").read_text(encoding="utf-8")),
    )
    dump_json(
        f"{definition}/pages/pages.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
            "pageOrder": ["ExecutiveOverview"],
            "activePageName": "ExecutiveOverview",
        },
    )
    dump_json(
        f"{definition}/pages/ExecutiveOverview/page.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
            "name": "ExecutiveOverview",
            "displayName": "Executive Overview",
            "displayOption": "FitToPage",
            "height": 720,
            "width": 1280,
        },
    )


if __name__ == "__main__":
    build_report_shell()
    print("Created PBIP/PBIR report shell. Desktop import and refresh not verified.")
