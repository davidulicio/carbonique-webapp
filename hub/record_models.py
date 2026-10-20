"""Calibration history and the team's technical reference library."""
import uuid
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class CalibrationLog(models.Model):
    EVENTS = [('swap', 'Sensor swap'), ('onsite', 'On-site calibration'), ('lab', 'Lab calibration')]
    PREPARATIONS = [('', 'Not applicable'), ('cleaned_calibrated', 'Cleaned and lab calibrated'), ('cleaned', 'Cleaned only'), ('unknown', 'Not confirmed')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey('inventory.Site', on_delete=models.PROTECT, related_name='calibrations')
    event_date = models.DateField()
    event_type = models.CharField(max_length=10, choices=EVENTS)
    sensor_name = models.CharField(max_length=200)
    sensor_model = models.CharField(max_length=150, blank=True)
    equipment = models.ForeignKey('inventory.Equipment', null=True, blank=True, on_delete=models.PROTECT, related_name='calibrations')
    serial_number = models.CharField(max_length=150, blank=True)
    replacement_equipment = models.ForeignKey('inventory.Equipment', null=True, blank=True, on_delete=models.PROTECT, related_name='replacement_calibrations')
    replacement_serial_number = models.CharField(max_length=150, blank=True)
    replacement_description = models.CharField(max_length=250, blank=True)
    preparation = models.CharField(max_length=25, choices=PREPARATIONS, blank=True)
    lab_calibrated_on = models.DateField(null=True, blank=True)
    next_due_on = models.DateField(null=True, blank=True)
    performed_by = models.CharField(max_length=200, blank=True)
    laboratory = models.CharField(max_length=200, blank=True)
    reference = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    source_visit = models.ForeignKey('hub.Visit', null=True, blank=True, on_delete=models.PROTECT, related_name='calibrations')
    is_archived = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)
    class Meta:
        ordering = ['-event_date', '-created_at']
        indexes = [models.Index(fields=['site', 'event_date'])]
    def clean(self):
        if self.event_type == 'swap':
            if not (self.replacement_equipment_id or self.replacement_serial_number.strip() or self.replacement_description.strip()):
                raise ValidationError({'replacement_description': 'Identify the installed sensor using an inventory item, serial number or description.'})
            if not self.preparation:
                raise ValidationError({'preparation': 'Record the replacement preparation, or select Not confirmed.'})
            if self.equipment_id and self.equipment_id == self.replacement_equipment_id:
                raise ValidationError({'replacement_equipment': 'The removed and installed sensors must be different instruments.'})
            if self.serial_number and self.serial_number.strip().casefold() == self.replacement_serial_number.strip().casefold():
                raise ValidationError({'replacement_serial_number': 'A sensor swap needs different removed and installed serial numbers.'})
        elif self.replacement_equipment_id or self.replacement_serial_number or self.replacement_description or self.preparation:
            raise ValidationError('Replacement sensor details apply only to sensor swaps.')
        if self.lab_calibrated_on and self.event_date and self.lab_calibrated_on > self.event_date:
            raise ValidationError({'lab_calibrated_on': 'The lab calibration date cannot follow the recorded work date.'})
        if self.next_due_on and self.event_date and self.next_due_on < self.event_date:
            raise ValidationError({'next_due_on': 'The next calibration date cannot precede the work date.'})
        if self.source_visit_id and self.source_visit.site_id != self.site_id:
            raise ValidationError({'source_visit': 'The linked visit must belong to this site.'})
    def __str__(self):
        return f'{self.site.code} · {self.event_date} · {self.sensor_name}'


class KnowledgeEntry(models.Model):
    CATEGORIES = [('general', 'General information'), ('hardware', 'Hardware and manuals'), ('wiring', 'Wiring and installation'), ('troubleshooting', 'Troubleshooting'), ('repairs', 'Repairs and service'), ('notes', 'Notebook / OneNote')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey('inventory.Site', null=True, blank=True, on_delete=models.PROTECT, related_name='knowledge_entries')
    title = models.CharField(max_length=250)
    category = models.CharField(max_length=25, choices=CATEGORIES, default='general')
    body = models.TextField(blank=True)
    external_url = models.URLField(max_length=2000, blank=True)
    is_archived = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)
    class Meta:
        ordering = ['-updated_at', 'title']
    def __str__(self):
        return self.title


def knowledge_file_path(instance, filename):
    return f'knowledge/{instance.entry_id}/{instance.id}{Path(filename).suffix.lower()[:12]}'


class KnowledgeFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry = models.ForeignKey(KnowledgeEntry, on_delete=models.PROTECT, related_name='files')
    file = models.FileField(upload_to=knowledge_file_path)
    filename = models.CharField(max_length=250)
    content_type = models.CharField(max_length=100)
    size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    is_archived = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)
    class Meta:
        ordering = ['created_at']
