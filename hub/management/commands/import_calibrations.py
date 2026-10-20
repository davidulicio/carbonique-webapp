"""Install reviewed sensor swaps from the supplied historical field visits."""
import json
import uuid
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from hub.models import CalibrationLog, ImportRecord, Visit

class Command(BaseCommand):
    help = "Import reviewed historical sensor swaps, preserving existing calibration edits."
    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="List matching swaps without saving records.")
    @transaction.atomic
    def handle(self, *args, **options):
        rows=json.loads((settings.BASE_DIR/"seed/calibration_swaps.json").read_text(encoding="utf-8"))
        added=existing=missing=0
        for row in rows:
            key=f"{row['site']}:{row['event_date']}:{row['sensor_model']}"
            if ImportRecord.objects.filter(source="calibration-visits",source_id=key).exists():
                existing+=1;continue
            visit=Visit.objects.filter(pk=row['source_visit'],site__code__iexact=row['site'],date=row['event_date']).select_related('site').first()
            if not visit:
                missing+=1;continue
            if options['dry_run']:
                self.stdout.write(f"{key}: {row['serial_number'] or 'unknown'} -> {row['replacement_serial_number'] or 'unknown'}")
                added+=1;continue
            identifier=uuid.uuid5(uuid.NAMESPACE_URL,"carbonique-calibration-visit:"+key)
            if CalibrationLog.objects.filter(pk=identifier).exists():
                raise CommandError(f"Calibration identifier already exists without an import receipt: {key}")
            notes=(row['summary']+"\n\nReplacement recorded as cleaned and calibrated under the project's sensor-swap practice, following confirmed project practice. This also applies to malfunction replacements. The individual lab date and certificate were not supplied. "
                "See the linked source visit for the original work description.")
            obj=CalibrationLog(id=identifier,site=visit.site,event_type='swap',event_date=visit.date,
                sensor_name=row['sensor_model'],sensor_model=row['sensor_model'],serial_number=row['serial_number'],
                replacement_serial_number=row['replacement_serial_number'],replacement_description=row['sensor_model']+" prepared replacement",
                preparation='cleaned_calibrated',performed_by=visit.crew,source_visit=visit,reference='Historical field visit',notes=notes)
            obj.full_clean();obj.save()
            ImportRecord.objects.create(source='calibration-visits',source_id=key,entity_type='hub.calibrationlog',entity_id=str(obj.pk),payload=row)
            added+=1
        self.stdout.write(self.style.SUCCESS(f"Calibration swaps: {added} {'matched' if options['dry_run'] else 'added'}, {existing} already imported, {missing} source visits not installed. Existing records preserved."))
