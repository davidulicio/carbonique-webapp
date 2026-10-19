import uuid
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import datetime, time, timezone as datetime_timezone, timedelta
from inventory.models import FieldNote
from hub.models import Visit, VisitReport, ImportRecord
from hub.reports import render_visit_report

class Command(BaseCommand):
    help = "Link every existing EcoFlux FieldNote to one historical visit, preserving IDs, text and files."
    @transaction.atomic
    def handle(self, *args, **options):
        count = 0
        for note in FieldNote.objects.select_related("site").all():
            if Visit.objects.filter(legacy_note=note).exists():
                continue
            instant = datetime.combine(note.date_visited, time(12), tzinfo=datetime_timezone(timedelta(hours=-5)))
            visit = Visit.objects.create(id=uuid.uuid5(uuid.NAMESPACE_URL, f"ecoflux:fieldnote:{note.pk}"), site=note.site, legacy_note=note, date=note.date_visited, crew=note.site_visitors or note.submitter, title=note.summary, narrative=note.note, status="closed", started_at=instant, ended_at=instant)
            VisitReport.objects.create(visit=visit, revision=1, text=render_visit_report(visit), markdown=render_visit_report(visit, True))
            ImportRecord.objects.get_or_create(source="ecoflux", source_id=f"fieldnote:{note.pk}", defaults={"entity_type": "hub.visit", "entity_id": str(visit.pk), "payload": {"submitter": note.submitter, "original_note_id": note.pk, "time_precision": "date only; noon placeholder"}})
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Linked {count} historical EcoFlux notes. Original records and attachments were retained."))
