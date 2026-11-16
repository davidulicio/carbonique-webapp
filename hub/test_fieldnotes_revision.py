import io
import tempfile

from django.core.management import call_command
from django.test import TestCase, override_settings

from hub.models import DataCaveat, ImportRecord, Visit


class FieldNotesRevisionTests(TestCase):
    def test_preview_apply_and_preserve_local_edits(self):
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            output = io.StringIO()
            call_command("import_resources", stdout=output)
            mapping = ImportRecord.objects.get(source="fieldnotes", source_id="note:135")
            visit = Visit.objects.get(pk=mapping.entity_id)
            visit.narrative = "Team edit to preserve."
            visit.save(update_fields=["narrative"])

            preview = io.StringIO()
            call_command("sync_fieldnotes", stdout=preview)
            self.assertIn("kept app edits: narrative", preview.getvalue())
            self.assertEqual(Visit.objects.count(), 127)
            self.assertEqual(DataCaveat.objects.count(), 19)

            call_command("sync_fieldnotes", apply=True, stdout=output)
            visit.refresh_from_db()
            self.assertEqual(visit.title, "Reconnection of 4 solar panels")
            self.assertEqual(visit.narrative, "Team edit to preserve.")
            self.assertEqual(Visit.objects.count(), 141)
            self.assertEqual(DataCaveat.objects.count(), 27)

            public = self.client.get("/fieldnotes/content/")
            self.assertContains(public, "Third-stage wake filter")
            self.assertContains(public, "2025-12-01 03:30")
            self.assertContains(public, "Field Notes resolution")
            self.assertContains(public, "data:image/jpeg;base64,")

            visit.title = "Four solar panels reconnected after the wind damage"
            visit.save(update_fields=["title"])
            rerun = io.StringIO()
            call_command("sync_fieldnotes", apply=True, stdout=rerun)
            self.assertIn("Applied 0 records", rerun.getvalue())
            visit.refresh_from_db()
            self.assertEqual(visit.title, "Four solar panels reconnected after the wind damage")

