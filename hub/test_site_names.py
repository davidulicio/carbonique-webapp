import io
import json
import tempfile
from importlib import import_module
from pathlib import Path

from django.apps import apps
from django.core.management import call_command
from django.test import TestCase

from inventory.models import Site
from inventory.site_names import SITE_NAMES
from .models import Visit


class ProjectSiteNameTests(TestCase):
    def test_migration_keeps_codes_links_and_metadata_and_updates_public_names(self):
        records = {}
        for code in SITE_NAMES:
            site = Site.objects.create(code=code.lower(), name="Earlier name", date_activated="2025-01-01", public_reference=True, metadata={"preserved": True})
            records[code] = (site.pk, site.version)
        visit = Visit.objects.create(site_id=records["UQAM_1"][0], date="2026-10-21", title="Existing visit")
        other = Site.objects.create(code="OTHER", name="Another project", date_activated="2025-01-01")
        rename = import_module("inventory.migrations.0015_update_project_site_names").rename_sites
        rename(apps, None)
        for code, name in SITE_NAMES.items():
            site = Site.objects.get(pk=records[code][0])
            self.assertEqual(site.name, name)
            self.assertEqual(site.code, code.lower())
            self.assertEqual(site.metadata, {"preserved": True})
            self.assertEqual(site.version, records[code][1] + 1)
        visit.refresh_from_db()
        self.assertEqual(visit.site_id, records["UQAM_1"][0])
        other.refresh_from_db()
        self.assertEqual(other.name, "Another project")
        rename(apps, None)
        self.assertEqual(Site.objects.get(pk=visit.site_id).version, records["UQAM_1"][1] + 1)
        response = self.client.get("/fieldnotes/content/")
        for name in SITE_NAMES.values():
            self.assertContains(response, name)

    def test_new_import_uses_current_names_and_rerun_keeps_team_edits(self):
        fixture = {"NOTES": [], "PIPE": [], "SITEINFO": {"source": "Reference", "parsed": "2026-10-21", "sites": [
            {"code": code, "title": "Earlier source title", "sections": []} for code in SITE_NAMES
        ]}}
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "reference.json"
            file.write_text(json.dumps(fixture), encoding="utf-8")
            call_command("import_fieldnotes", file=str(file), stdout=io.StringIO())
            self.assertEqual(dict(Site.objects.values_list("code", "name")), SITE_NAMES)
            Site.objects.filter(code="UQAM_1").update(name="Later team edit")
            call_command("import_fieldnotes", file=str(file), stdout=io.StringIO())
            self.assertEqual(Site.objects.get(code="UQAM_1").name, "Later team edit")
