"""Install the supplied resource snapshot without replacing team edits."""
import hashlib
import json
import tempfile
import uuid
from copy import deepcopy
from pathlib import Path
from datetime import datetime, timezone
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from inventory.models import Site
from hub.models import Protocol, ConfigurationVersion, Attachment, ImportRecord, BADMProfile, BADMRecord


class Command(BaseCommand):
    help = "Import all bundled inventory-export information, INI files and eight protocols; safe to rerun."

    def add_arguments(self, parser):
        parser.add_argument("--protocol-directory", help="Private source directory for credential-bearing protocol PDFs; files are copied into protected media storage.")

    @transaction.atomic
    def handle(self, *args, **options):
        root = settings.BASE_DIR / "seed/ecoflux_inventory_export"
        read = lambda name: json.loads((root / "data" / name).read_text(encoding="utf-8-sig"))
        sites, notes, caveats, ini_files = read("sites.json"), read("field_notes.json"), read("data_caveats.json"), read("ini_files.json")
        source_sites = deepcopy(sites)
        plots = {}
        for site in sites["sites"]:
            for photo in site.get("photos", []):
                photo["path"] = str(root / photo["file"])
        for caveat in caveats:
            for plot in caveat.get("plots", []):
                if plot.get("file"):
                    plots[plot["k"]] = str(root / plot["file"])
        call_command("backfill_visits", stdout=self.stdout)
        with tempfile.TemporaryDirectory(prefix="carbonique-import-") as temp:
            path = Path(temp) / "fieldnotes.json"
            path.write_text(json.dumps({"NOTES": notes, "SITEINFO": sites, "PIPE": caveats, "plots": plots}), encoding="utf-8")
            call_command("import_fieldnotes", file=str(path), match_legacy_ids=True, stdout=self.stdout)
        for ref in source_sites["sites"]:
            site = Site.objects.get(code__iexact=ref["code"])
            if "inventory_export" not in site.metadata:
                site.metadata["inventory_export"] = {"site": ref, "site_summaries": source_sites.get("site_summaries"), "source": source_sites["source"], "parsed": source_sites["parsed"]}
                site.save(update_fields=["metadata", "updated_at"])
            # Only seed explicitly documented facts, never station codes, serial
            # numbers or inferred tower heights. Managers finish station setup.
            BADMProfile.objects.get_or_create(site=site, defaults={"notes": "Station class and ICOS identifier need manager confirmation. Coordinates and logger offset were copied from the supplied inventory reference."})
            for group, values in [("GRP_LOCATION", {"LOCATION_LAT": f"{ref['lat']:.4f}", "LOCATION_LONG": f"{ref['lon']:.4f}"}), ("GRP_UTC_OFFSET", {"UTC_OFFSET": "-5"})]:
                source_id = f"badm:{site.code}:{group}"
                if not ImportRecord.objects.filter(source="inventory-export", source_id=source_id).exists():
                    obj = BADMRecord.objects.filter(site=site, group=group).first()
                    if not obj:
                        obj = BADMRecord.objects.create(site=site, template="ASSICOSBADM_SiteDescr_20210429", group=group, values=values, notes="Copied from the supplied site reference; confirm before ICOS submission.")
                    ImportRecord.objects.create(source="inventory-export", source_id=source_id, entity_type="hub.badmrecord", entity_id=str(obj.pk), payload=values)
        for entry in ini_files:
            source_id = "ini:" + entry["f"]
            if ImportRecord.objects.filter(source="inventory-export", source_id=source_id).exists():
                continue
            site = Site.objects.get(code__iexact=entry["s"])
            file = root / "ini" / entry["f"]
            if not file.is_file():
                raise CommandError(f"Missing supplied INI file: {entry['f']}")
            data = file.read_bytes()
            config = ConfigurationVersion.objects.create(id=uuid.uuid5(uuid.NAMESPACE_URL, "ecoflux-export:" + source_id), site=site, label=f"Recommended {entry['st']} · {entry['f']}", effective_from=datetime(2026, 9, 29, tzinfo=timezone.utc), settings={"source": "EcoFlux inventory export 2026-10-16", "file": entry["f"], "stage": entry["st"], "summary": entry["sum"], "caveat_ids": entry.get("adds", []), "changed_excerpt": entry.get("ex", "")}, notes="Reference snapshot date only; verify the historical effective period before use. " + entry["sum"])
            attachment = Attachment(site=site, configuration=config, filename=entry["f"], caption=entry["sum"][:500], content_type="text/plain", size=len(data), sha256=hashlib.sha256(data).hexdigest())
            attachment.file.save(entry["f"], ContentFile(data), save=True)
            for caveat_id in entry.get("adds", []):
                mapping = ImportRecord.objects.filter(source="fieldnotes", source_id="caveat:" + caveat_id).first()
                if mapping:
                    from hub.models import DataCaveat
                    DataCaveat.objects.get(pk=mapping.entity_id).configurations.add(config)
            ImportRecord.objects.create(source="inventory-export", source_id=source_id, entity_type="hub.configurationversion", entity_id=str(config.pk), payload=entry)
        titles = {
            "Biomet_Maintenance_Protocol.pdf": ("Biomet sensor maintenance", "maintenance"),
            "Data_download.pdf": ("Data download procedure", "data"),
            "Field Work Safety Plan.pdf": ("Field work safety plan", "safety"),
            "Fieldwork_maintenance_and_procedures.pdf": ("Fieldwork maintenance and procedures", "general"),
            "Maintenance_LI7200RS.pdf": ("LI-7200RS maintenance", "maintenance"),
            "Maintenance_LI7700.pdf": ("LI-7700 maintenance", "maintenance"),
            "Maintenance_OTT_Pluvio2.pdf": ("OTT Pluvio² maintenance", "maintenance"),
            "Methanol Handling Procedure and Protocol.pdf": ("Methanol handling procedure and protocol", "safety"),
        }
        catalogue = json.loads((settings.BASE_DIR / "seed/protocols/catalogue.json").read_text(encoding="utf-8"))
        private_dir = options.get("protocol_directory") or settings.PRIVATE_PROTOCOLS_DIR
        for filename, (title, category) in titles.items():
            path = settings.BASE_DIR / "seed/protocols" / filename
            info = catalogue[filename]
            if info["private_source"] and private_dir:
                path = Path(private_dir) / filename
            if not path.is_file() and not info["private_source"]:
                raise CommandError(f"Missing supplied protocol: {filename}")
            obj, _ = Protocol.objects.get_or_create(pk=uuid.uuid5(uuid.NAMESPACE_URL, "carbonique-protocol:" + filename), defaults={"title": title, "category": category, "bundled_file": "" if info["private_source"] else filename, "filename": filename, "sha256": info["sha256"], "size": info["size"], "revision": info["revision"], "summary": "Original supplied protocol. Open the PDF for the complete instructions, figures and revision details."})
            if info["private_source"] and path.is_file() and not obj.file:
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != info["sha256"]:
                    raise CommandError("Private source PDF differs from the supplied version. Upload a revised protocol through the app instead.")
                obj.bundled_file = ""
                obj.file.save(filename, ContentFile(data), save=True)
            elif info["private_source"] and not path.is_file() and not obj.file:
                self.stdout.write("Data download protocol needs private installation or an administrator upload; its source contains login details and is excluded from Git.")
        self.stdout.write(self.style.SUCCESS(f"Resource snapshot installed: {len(sites['sites'])} sites, {len(notes)} source notes, {len(caveats)} caveats, {len(ini_files)} INI files and {len(titles)} protocols. Existing edits preserved."))
