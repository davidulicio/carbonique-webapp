"""Build the offline schema from downloaded, unmodified ICOS XLSX templates.

Usage: python scripts/build_badm_schema.py DIRECTORY
Requires openpyxl only when rebuilding; the deployed app uses the generated JSON.
Download each catalogue share as icos-SHARE_ID.xlsx first.
"""
import hashlib
import json
import re
import sys
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
schema = {"source": "https://www.icos-etc.eu/icos/documents/templates", "retrieved": "2026-10-16", "templates": {}}
for path in sorted(Path(sys.argv[1]).glob("icos-*.xlsx")):
    if path.stem == "icos-station":
        continue
    book = openpyxl.load_workbook(path, data_only=True)
    versions = [str(row[0]).strip() for row in book["Versioning"].values if row[0] and re.match(r"(?:ASS)?ICOSBADM_.*_\d{8}$", str(row[0]).strip())]
    fallback = {"79WySPL6mW5THjD": "ICOSBADM_Allometric_20180626", "j84Wg2fi5FyeciN": "ICOSBADM_EC_Raw_Processing_20260727"}
    name = versions[-1] if versions else fallback[path.stem.removeprefix("icos-")]
    vocabulary = {}
    for sheet in book:
        if "vocabulary" in sheet.title.lower():
            for row in list(sheet.values)[1:]:
                if row[0] and row[1] is not None:
                    vocabulary.setdefault(str(row[0]).strip(), []).append({"value": str(row[1]).strip(), "description": str(row[2] or "")})
    units = {}
    for sheet in book:
        if sheet.title in {"Explanations", "Versioning"} or "vocabulary" in sheet.title.lower():
            continue
        for row in sheet.values:
            if row[0] and len(row) >= 3:
                units[str(row[0]).strip()] = str(row[2] or "")
    groups = {}
    for row in list(book["Explanations"].values)[1:]:
        if not row[0] or not row[1] or not str(row[0]).startswith("GRP_") or row[0] == "GRP_HEADER":
            continue
        group = str(row[0]).strip()
        variable = str(row[1]).strip()
        unit = units.get(variable, "")
        groups.setdefault(group, []).append({"name": variable, "description": str(row[4] or ""), "explanation": str(row[5] or ""), "requirement": str(row[2] or "").strip(), "multiple": str(row[3] or "").strip(), "units": unit, "choices": vocabulary.get(unit, [])})
    schema["templates"][name] = {"name": name, "source": f"https://fileshare.icos-cp.eu/s/{path.stem.removeprefix('icos-')}", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "classes": ["associated"] if name.startswith("ASS") else (["associated", "class1", "class2"] if any(g in groups for g in ("GRP_INST", "GRP_TEAM", "GRP_DISTURB", "GRP_PROC")) else ["class1", "class2"]), "groups": groups}
target = ROOT / "seed/badm/schema.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Generated {len(schema['templates'])} template definitions.")
