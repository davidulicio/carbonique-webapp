"""Apply the reviewed November 2026 public Field Notes delta."""
import json
from datetime import date, datetime, timedelta, timezone

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hub.models import DataCaveat, ImportRecord, Visit, VisitReport
from hub.reports import render_visit_report
from hub.serializers import clean_html
from inventory.models import Site

from .import_fieldnotes import Command as ReferenceImporter, instant, stable


VISIT_FIELDS = {"ti": ("title", str), "b": ("narrative", clean_html)}
CAVEAT_FIELDS = {
    "ti": ("title", str), "b": ("description", clean_html),
    "fix": ("treatment", clean_html), "period": ("period_label", str),
}
EVIDENCE_KEYS = ("xref", "flag", "links", "resolved", "code", "codecap")
EST = timezone(timedelta(hours=-5))
# Only explicit timestamps for well-defined bounds. Multi-period and date-only
# bounds remain in the source period label rather than inventing precision.
TIMES = {
    "pn2": (None, "2026-05-07 11:30"),
    "pn3": (None, "2026-02-10 10:00"),
    "pn4": (None, "2026-09-28 10:30"),
    "pn6": ("2025-08-05 13:30", None),
    "pn8": ("2025-05-25 08:30", "2025-07-23 21:30"),
    "pn9": ("2025-12-01 03:30", "2025-12-17 14:30"),
    "pn10": (None, "2025-08-26 13:00"),
    "pn11": ("2026-03-17 02:00", "2026-03-27 12:30"),
    "pn22": ("2026-08-03 11:00", "2026-11-06 13:00"),
}


def projected(fields, source):
    return {field: convert(source.get(key, "")) for key, (field, convert) in fields.items()}


def merge(current, before, after, conflicts, prefix=""):
    updates = {}
    for key, value in after.items():
        if value == before[key] or current[key] == value:
            continue
        if current[key] == before[key]:
            updates[key] = value
        else:
            conflicts.append(prefix + key)
    return updates


class Command(BaseCommand):
    help = "Preview or apply the November 2026 public Field Notes update."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write the planned changes.")

    @transaction.atomic
    def handle(self, *args, **options):
        apply = options["apply"]
        root = settings.BASE_DIR / "seed/fieldnotes_2026_11"
        data = json.loads((root / "changes.json").read_text(encoding="utf-8"))
        source = "fieldnotes:" + data["revision"]
        plots = {key: root / name for key, name in data["plots"].items()}
        if any(not path.is_file() for path in plots.values()):
            raise CommandError("The revision is missing one or more bundled figures.")
        sites = {}
        # ALL refers to these six sites, not unrelated stations added to the app.
        for code in ("MCGILL_1", "UQAM_1", "UQAM_2", "UQAM_3", "UQAM_4", "UQAM_5"):
            try:
                sites[code] = Site.objects.get(code__iexact=code)
            except (Site.DoesNotExist, Site.MultipleObjectsReturned):
                raise CommandError(f"Expected one site for {code}; check the reference import.") from None

        importer = ReferenceImporter(stdout=self.stdout, stderr=self.stderr)
        pending = 0
        for key, model, prefix, fields in (
            ("visits", Visit, "note", VISIT_FIELDS),
            ("caveats", DataCaveat, "caveat", CAVEAT_FIELDS),
        ):
            for change in data[key]:
                before, after = change["before"], change["after"]
                source_id = f"{prefix}:{after['id']}"
                completed = ImportRecord.objects.filter(source=source, source_id=source_id).first()
                if completed:
                    continue
                mapping = ImportRecord.objects.filter(source="fieldnotes", source_id=source_id).first()
                rows = model.objects.select_for_update() if apply else model.objects
                obj = rows.filter(pk=mapping.entity_id).first() if mapping else None
                selected = list(sites.values()) if after["s"] == "ALL" else [sites[after["s"].upper()]]
                if (mapping and not obj) or (before and not mapping):
                    self.stdout.write(f"{source_id}: review missing mapped record")
                    continue
                if obj and before is None:
                    # A separate import already mapped this new upstream ID.
                    self.stdout.write(f"{source_id}: already mapped; leave its app record unchanged")
                    continue
                if obj is None:
                    if model is Visit:
                        day = date.fromisoformat(after["d"])
                        candidates = rows.filter(site=selected[0], date=day)
                        if candidates.filter(legacy_note_id=after["id"]).exists() or candidates.filter(
                            title__iexact=after["ti"]
                        ).exists():
                            self.stdout.write(f"{source_id}: review matching unmapped visit")
                            continue
                    elif rows.filter(title__iexact=after["ti"], sites__in=selected).exists():
                        self.stdout.write(f"{source_id}: review matching unmapped caveat")
                        continue

                values = projected(fields, after)
                conflicts = []
                evidence = {k: after[k] for k in EVIDENCE_KEYS if after.get(k)}
                if obj is not None:
                    values = merge({k: getattr(obj, k) for k in values},
                                   projected(fields, before), values, conflicts)
                if model is Visit and obj is None:
                    values.update(site=selected[0], date=day, crew=after["w"], status="closed",
                                  classification={"major": "major", "issue": "fault"}.get(after["t"], "routine"),
                                  started_at=instant(day), ended_at=instant(day))
                if model is DataCaveat:
                    if obj is None:
                        values["evidence"] = evidence
                        values["status"] = "resolved" if after.get("done") else "draft"
                    else:
                        old_evidence = obj.evidence or {}
                        changed_evidence = merge(
                            {k: old_evidence.get(k) for k in EVIDENCE_KEYS},
                            {k: before.get(k) for k in EVIDENCE_KEYS},
                            {k: after.get(k) for k in EVIDENCE_KEYS}, conflicts, "evidence.",
                        )
                        if changed_evidence:
                            values["evidence"] = {**old_evidence, **changed_evidence}
                        if after.get("done") and not before.get("done") and obj.status != "resolved":
                            if obj.status == "draft" and obj.reviewed_at is None and obj.resolved_at is None:
                                values["status"] = "resolved"
                            else:
                                conflicts.append("status")
                    if after["id"] in TIMES and (obj is None or "period_label" in values):
                        for field, raw in zip(("affected_from", "affected_to"), TIMES[after["id"]]):
                            if raw:
                                value = datetime.fromisoformat(raw).replace(tzinfo=EST)
                                if obj is None or getattr(obj, field) is None:
                                    values[field] = value
                                elif getattr(obj, field) != value:
                                    conflicts.append(field)
                        if obj is not None:
                            start = values.get("affected_from", obj.affected_from)
                            end = values.get("affected_to", obj.affected_to)
                            if start and end and start >= end:
                                for field in ("affected_from", "affected_to"):
                                    if field in values:
                                        del values[field]
                                        conflicts.append(field)

                figures = [p for p in after.get("plots", []) if p["k"] in plots]
                action = "add" if obj is None else "update" if values or figures else "keep"
                details = ", ".join(sorted(values)) if obj is not None else after["ti"]
                if figures:
                    details += f"; {len(figures)} figure(s)"
                if conflicts:
                    details += "; kept app edits: " + ", ".join(conflicts)
                self.stdout.write(f"{source_id}: {action} {details}".rstrip())
                pending += 1
                if not apply:
                    continue

                entity = f"hub.{model._meta.model_name}"
                if obj is None:
                    obj = rows.create(id=stable(source_id), **values)
                    if model is Visit:
                        VisitReport.objects.create(visit=obj, revision=1, text=render_visit_report(obj),
                                                   markdown=render_visit_report(obj, True))
                    else:
                        obj.sites.set(selected)
                    ImportRecord.objects.create(source="fieldnotes", source_id=source_id,
                                                entity_type=entity, entity_id=str(obj.pk), payload=after)
                elif values:
                    for field, value in values.items():
                        setattr(obj, field, value)
                    obj.version += 1
                    obj.save(update_fields=[*values, "version", "updated_at"])
                for plot in figures:
                    for site in obj.sites.all():
                        importer.attach(plots[plot["k"]], f"plot:{after['id']}:{plot['k']}", site,
                                        caveat=obj, caption=plot.get("c", ""))
                ImportRecord.objects.create(source=source, source_id=source_id, entity_type=entity,
                                            entity_id=str(obj.pk), payload={"kept_app_fields": conflicts})

        mode = "Applied" if apply else "Previewed"
        self.stdout.write(f"{mode} {pending} records from Field Notes {data['revision'][:7]}.")

