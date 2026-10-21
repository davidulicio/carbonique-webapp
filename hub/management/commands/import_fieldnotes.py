import hashlib
import json
import re
import uuid
from copy import deepcopy
from pathlib import Path
from datetime import datetime, time, timedelta, timezone as datetime_timezone
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from inventory.models import Site, FieldNote
from inventory.site_names import SITE_NAMES
from hub.models import Visit, VisitReport, DataCaveat, Attachment, ConfigurationVersion, ImportRecord
from hub.reports import render_visit_report
from hub.serializers import clean_html

def instant(date):
    return datetime.combine(date, time(12), tzinfo=datetime_timezone(timedelta(hours=-5)))

def stable(value):
    return uuid.uuid5(uuid.NAMESPACE_URL, "carbonique-fieldnotes:" + value)

class Command(BaseCommand):
    help = "Import Field Notes JSON extracted from its HTML, with provenance and idempotent identifiers."
    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(settings.BASE_DIR / "seed/fieldnotes.json"))
        parser.add_argument("--notes", action="store_true", help="Import classified visit summaries even when legacy notes exist.")
        parser.add_argument("--skip-notes", action="store_true")
        parser.add_argument("--match-legacy-ids", action="store_true", help="Attach classifications to legacy notes only when ID, site and date all agree.")
    def attach(self, path, source, site, **links):
        source_id = source + ":" + site.code
        if ImportRecord.objects.filter(source="fieldnotes-media", source_id=source_id).exists():
            return
        if not path.is_file():
            self.stderr.write(f"Missing bundled attachment: {path.name}")
            return
        data = path.read_bytes()
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        obj = Attachment(id=stable(source_id), site=site, filename=path.name, caption=links.pop("caption", ""), content_type=mime, sha256=hashlib.sha256(data).hexdigest(), size=len(data), **links)
        obj.file.save(path.name, ContentFile(data), save=True)
        ImportRecord.objects.create(source="fieldnotes-media", source_id=source_id, entity_type="hub.attachment", entity_id=str(obj.pk))
    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["file"]).resolve()
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        sites = {}
        notes = data["NOTES"]
        for ref in data["SITEINFO"]["sites"]:
            code = ref["code"].upper()
            matches = Site.objects.filter(code__iexact=code)
            if matches.count() > 1:
                raise CommandError(f"Multiple EcoFlux sites match {code}; reconcile them before importing.")
            fields = {i.get("k", ""): i.get("v", "") for section in ref["sections"] for i in section.get("items", [])}
            active_label = fields.get("Station active since", "")
            date_match = re.search(r"\d{4}-\d{2}-\d{2}", active_label)
            dates = [n["d"] for n in notes if n["s"].upper() == code]
            date = date_match.group(0) if date_match else min(dates) if dates else "2026-09-29"
            site = matches.first()
            reference = deepcopy(ref)
            photos = reference.pop("photos", [])
            metadata = {"reference": reference, "common": data["SITEINFO"].get("common", []), "source": data["SITEINFO"]["source"], "source_edition": data["SITEINFO"]["parsed"], "activation_date_basis": active_label if date_match else "Earliest documented visit used as placeholder; verify activation date."}
            if not site:
                site = Site.objects.create(code=code, name=SITE_NAMES.get(code, fields.get("Site name", ref["title"]))[:150], amp=fields.get("AmeriFlux ID", "")[:10], location=fields.get("Location", ref.get("place", "")), description="\n".join(ref.get("desc", [])), date_activated=date, gps_coordinates=f"{ref.get('lat', '')}, {ref.get('lon', '')}", metadata=metadata)
            elif not site.metadata.get("reference"):
                site.metadata = {**site.metadata, **metadata}
                site.save(update_fields=["metadata", "updated_at"])
            sites[code] = site
            for i, photo in enumerate(photos):
                self.attach(path.parent / photo["path"], f"site-photo:{code}:{i}", site, caption=photo.get("alt") or f"{code} site reference photograph")
            config_id = f"reference-configuration:{code}"
            if not ImportRecord.objects.filter(source="fieldnotes", source_id=config_id).exists():
                settings_data = {s["h"]: {i.get("k", f"item_{j}"): i.get("v", "") for j, i in enumerate(s.get("items", []))} for s in ref["sections"] if s["h"] == "Processing settings"}
                settings_data["instrument_reference"] = [s for s in ref["sections"] if s["h"] == "Instruments info"]
                config = ConfigurationVersion.objects.create(id=stable(config_id), site=site, label="Imported reference snapshot · 2026-09-29", effective_from=datetime(2026, 9, 29, tzinfo=datetime_timezone(timedelta(hours=-5))), settings=settings_data, notes="Document snapshot date. Historical effective periods were not established by this import; verify before applying to earlier measurements.")
                ImportRecord.objects.create(source="fieldnotes", source_id=config_id, entity_type="hub.configurationversion", entity_id=str(config.pk))
        import_notes = not options["skip_notes"] and (options["notes"] or not FieldNote.objects.exists())
        imported = 0
        if import_notes or options["match_legacy_ids"]:
            for note in notes:
                source_id = "note:" + str(note["id"])
                if ImportRecord.objects.filter(source="fieldnotes", source_id=source_id).exists():
                    continue
                site = sites[note["s"].upper()]
                legacy = FieldNote.objects.filter(pk=note["id"], site=site, date_visited=note["d"]).first() if options["match_legacy_ids"] else None
                classification = {"major": "major", "issue": "fault", "routine": "routine"}.get(note["t"], "routine")
                if legacy:
                    visit = Visit.objects.get(legacy_note=legacy)
                    visit.classification = classification
                    visit.save(update_fields=["classification", "updated_at"])
                elif import_notes:
                    visit = Visit.objects.create(id=stable(source_id), site=site, date=note["d"], crew=note["w"], title=note["ti"], narrative=clean_html(note["b"]), status="closed", classification=classification, started_at=instant(datetime.fromisoformat(note["d"]).date()), ended_at=instant(datetime.fromisoformat(note["d"]).date()))
                    VisitReport.objects.create(visit=visit, revision=1, text=render_visit_report(visit), markdown=render_visit_report(visit, True))
                else:
                    continue
                ImportRecord.objects.create(source="fieldnotes", source_id=source_id, entity_type="hub.visit", entity_id=str(visit.pk), payload=note)
                imported += 1
        for caveat in data["PIPE"]:
            source_id = "caveat:" + caveat["id"]
            mapping = ImportRecord.objects.filter(source="fieldnotes", source_id=source_id).first()
            selected = list(sites.values()) if caveat["s"] == "ALL" else [sites[caveat["s"].upper()]]
            if mapping:
                obj = DataCaveat.objects.get(pk=mapping.entity_id)
            else:
                obj = DataCaveat.objects.create(id=stable(source_id), title=caveat["ti"], description=clean_html(caveat["b"]), treatment=clean_html(caveat.get("fix", "")), period_label=caveat.get("period", ""), status="draft", evidence={k:v for k,v in caveat.items() if k not in {"b", "fix"}})
                obj.sites.set(selected)
                ImportRecord.objects.create(source="fieldnotes", source_id=source_id, entity_type="hub.datacaveat", entity_id=str(obj.pk), payload=caveat)
            for plot in caveat.get("plots", []):
                if plot["k"] in data.get("plots", {}):
                    for site in selected:
                        self.attach(path.parent / data["plots"][plot["k"]], f"plot:{caveat['id']}:{plot['k']}", site, caveat=obj, caption=plot.get("c", ""))
        self.stdout.write(self.style.SUCCESS(f"Imported reference for {len(sites)} sites, {imported} visit summaries and {len(data['PIPE'])} caveats. Rerunning preserves existing edits."))
        if not import_notes and not options["match_legacy_ids"]:
            self.stdout.write("Legacy EcoFlux notes exist: copied summaries were skipped to prevent duplicates. Use --match-legacy-ids after backfill_visits to add matching classifications.")
