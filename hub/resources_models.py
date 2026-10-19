"""Site context, approved protocols and repeatable ICOS BADM records."""
import uuid
from pathlib import Path
from django.conf import settings
from django.db import models
from inventory.models import Site


def resource_path(instance, filename):
    return f"resources/{instance.id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class SiteCondition(models.Model):
    site = models.OneToOneField(Site, on_delete=models.PROTECT, related_name="condition")
    status = models.CharField(max_length=20, default="unknown", choices=[("unknown", "Not assessed"), ("open", "Accessible"), ("caution", "Use caution"), ("restricted", "Restricted access"), ("closed", "Inaccessible")])
    statement = models.TextField(blank=True)
    valid_until = models.DateField(null=True, blank=True, help_text="Review date; access never reopens automatically.")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)


class BADMProfile(models.Model):
    site = models.OneToOneField(Site, on_delete=models.PROTECT, related_name="badm_profile")
    station_id = models.CharField(max_length=6, blank=True, help_text="Official assigned ICOS code; do not substitute an AmeriFlux code.")
    station_class = models.CharField(max_length=15, default="associated", choices=[("associated", "Associated"), ("class1", "Class 1"), ("class2", "Class 2")])
    applicable_groups = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)


class BADMRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="badm_records")
    template = models.CharField(max_length=100)
    group = models.CharField(max_length=60)
    values = models.JSONField(default=dict)
    notes = models.TextField(blank=True)
    conditions_reviewed = models.BooleanField(default=False, help_text="A manager has checked conditional rules in the official explanations.")
    is_archived = models.BooleanField(default=False)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)


class Protocol(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=250)
    category = models.CharField(max_length=30, default="maintenance", choices=[("maintenance", "Instrument maintenance"), ("data", "Data collection"), ("safety", "Field safety"), ("general", "General procedures")])
    summary = models.TextField(blank=True)
    revision = models.CharField(max_length=100, blank=True)
    file = models.FileField(upload_to=resource_path, blank=True)
    bundled_file = models.CharField(max_length=200, blank=True)
    filename = models.CharField(max_length=250)
    sha256 = models.CharField(max_length=64)
    size = models.PositiveBigIntegerField(default=0)
    is_archived = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.PositiveIntegerField(default=1)
    class Meta:
        ordering = ["category", "title", "-created_at"]


class SiteMedia(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="tower_media")
    title = models.CharField(max_length=250)
    caption = models.TextField(blank=True)
    file = models.FileField(upload_to=resource_path)
    filename = models.CharField(max_length=250)
    content_type = models.CharField(max_length=80)
    size = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    is_archived = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.PositiveIntegerField(default=1)
    class Meta:
        ordering = ["-created_at"]


class TowerStatus(models.Model):
    """Latest display-only telemetry; addresses and credentials never enter it."""
    site = models.OneToOneField(Site, on_delete=models.PROTECT, related_name="tower_status")
    status = models.CharField(max_length=20, default="not_checked")
    attempted_at = models.DateTimeField(null=True, blank=True)
    observed_at = models.DateTimeField(null=True, blank=True)
    payload = models.JSONField(default=dict)
    last_good = models.JSONField(default=dict)


class TowerReading(models.Model):
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="tower_readings")
    observed_at = models.DateTimeField()
    metrics = models.JSONField(default=dict)
    class Meta:
        indexes = [models.Index(fields=["site", "observed_at"])]
        ordering = ["-observed_at"]
