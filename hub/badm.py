"""Versioned ICOS definitions and conservative local validation.

Conditional requirements remain visible until explicitly reviewed. ETC performs
the authoritative checks, including cross-submission history and current LISTs.
"""
import json
import math
import re
from datetime import datetime
from functools import lru_cache
from django.conf import settings


@lru_cache(maxsize=1)
def schema():
    return json.loads((settings.BASE_DIR / "seed/badm/schema.json").read_text(encoding="utf-8"))


def templates(station_class):
    return {k: v for k, v in schema()["templates"].items() if station_class in v["classes"]}


def baseline(station_class):
    groups = ["GRP_LOCATION", "GRP_UTC_OFFSET", "GRP_TOWER", "GRP_TEAM", "GRP_INST"]
    return groups + (["GRP_IGBP", "GRP_INSTMAN"] if station_class == "associated" else ["GRP_EC", "GRP_ECSYS", "GRP_BM", "GRP_LOGGER", "GRP_FILE"])


def present(value):
    return value is not None and str(value).strip() != ""


def record_issues(record):
    definition = schema()["templates"].get(record.template, {})
    fields = definition.get("groups", {}).get(record.group)
    if not fields:
        return ["Unknown template or group."], []
    values, errors, review = record.values, [], []
    alternatives = {}
    known = {f["name"] for f in fields}
    for key in values.keys() - known:
        errors.append(f"{key}: variable is not in this template group.")
    for field in fields:
        name, rule = field["name"], field["requirement"]
        value = values.get(name)
        # TOWER_DATE explicitly allows omission for the initial tower description.
        if rule == "r" and name != "TOWER_DATE" and not present(value):
            errors.append(f"{name}: required.")
        for option in re.findall(r"[ra]\((\d+)\)", rule):
            alternatives.setdefault(option, []).append(name)
        if rule.startswith("c") or (rule and rule not in {"r"} and not re.fullmatch(r"[ra]\(\d+\)", rule)):
            review.append(f"{name}: {rule}; check the official explanation.")
        if not present(value):
            continue
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            errors.append(f"{name}: use one text or numeric value.")
            continue
        text, units = str(value).strip(), field["units"]
        if field["choices"] and text not in {c["value"] for c in field["choices"]}:
            errors.append(f"{name}: select a value from {units}.")
        if "YYYY" in units:
            # ICOS dates permit reduced precision only where the template says so.
            precisions = sorted({len(v) for v in re.findall(r"Y{4}(?:MM)?(?:DD)?(?:HH)?(?:MM)?", units)})
            if not precisions:
                precisions = [12]
            length = len(text)
            date_formats = {4: "%Y", 6: "%Y%m", 8: "%Y%m%d", 10: "%Y%m%d%H", 12: "%Y%m%d%H%M"}
            try:
                if length not in precisions or length not in date_formats or not text.isdigit():
                    raise ValueError()
                datetime.strptime(text, date_formats[length])
            except ValueError:
                errors.append(f"{name}: use a valid date in {units} format.")
        elif units and not any(t in units.lower() for t in ("text", "list", "cc-", "string", "doi", "url", "email")):
            try:
                number = float(text)
                if not re.fullmatch(r"-?\d+(?:\.\d+)?", text) or not math.isfinite(number):
                    raise ValueError()
                if name == "LOCATION_LAT" and not -90 <= number <= 90:
                    raise ValueError()
                if name == "LOCATION_LONG" and not -180 <= number <= 180:
                    raise ValueError()
                if name in {"LOCATION_LAT", "LOCATION_LONG"} and not re.fullmatch(r"-?\d+\.\d{4,}", text):
                    raise ValueError()
                if name == "UTC_OFFSET" and not -12 <= number <= 14:
                    raise ValueError()
            except ValueError:
                errors.append(f"{name}: expected a valid numeric value ({units}).")
    if alternatives:
        complete = [key for key, names in alternatives.items() if all(present(values.get(n)) for n in names)]
        used = [key for key, names in alternatives.items() if any(present(values.get(n)) for n in names)]
        if not complete or len(used) > 1:
            errors.append("Complete exactly one alternative set: " + " OR ".join(", ".join(names) for names in alternatives.values()))
    for name, value in values.items():
        if name.endswith("DATE_START") and present(value):
            end = values.get(name.removesuffix("START") + "END")
            if present(end) and str(end) < str(value):
                errors.append(f"{name}: end date precedes start date.")
    event = next((values.get(f["name"]) for f in fields if f["name"].endswith("_TYPE")), None)
    if event in {"Installation", "Removal"} and any(present(v) for k, v in values.items() if k.endswith(("DATE_START", "DATE_END"))):
        errors.append("Installation and removal need an event DATE, not a date range.")
    # Complex conditional tables and explanatory constraints need human review.
    if any(f["requirement"] not in {"", "r"} for f in fields) and not record.conditions_reviewed:
        review.append("Manager review of the conditional and alternative rules is pending.")
    return errors, review if not record.conditions_reviewed else []


def completeness(profile, records):
    required = list(dict.fromkeys(baseline(profile.station_class) + profile.applicable_groups))
    active = [r for r in records if not r.is_archived]
    available = templates(profile.station_class)
    issues = []
    if not re.fullmatch(r"[A-Z]{2}-[A-Za-z0-9]{3}", profile.station_id):
        issues.append("Enter the official six-character ICOS station identifier (CC-Xxx).")
    missing = [g for g in required if not any(r.group == g for r in active)]
    checked = []
    for record in active:
        errors, review = record_issues(record)
        if record.template not in available:
            errors.append("Template does not match the selected station class.")
        checked.append({"id": str(record.pk), "group": record.group, "errors": errors, "review": review, "ok": not errors and not review})
    # These are local station-setup checks in addition to per-entry ICOS rules.
    essentials = {"GRP_LOCATION": ["LOCATION_LAT", "LOCATION_LONG"], "GRP_UTC_OFFSET": ["UTC_OFFSET"], "GRP_TOWER": ["TOWER_HEIGHT"]}
    for group, names in essentials.items():
        if group not in missing:
            for name in names:
                if not any(r.group == group and present(r.values.get(name)) for r in active):
                    issues.append(f"{name}: missing from the station setup.")
    ok = not issues and not missing and all(r["ok"] for r in checked)
    return {"ok": ok, "label": "Local checks passed; ETC review required" if ok else "Information or review missing", "issues": issues, "missing_groups": missing, "required_groups": required, "records": checked, "scope": "Local station setup checklist and template checks. This is not ICOS certification or submission acceptance. Confirm station applicability, current controlled vocabularies and conditional requirements with ICOS ETC."}
