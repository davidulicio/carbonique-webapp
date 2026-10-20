import uuid
from pathlib import Path
from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from inventory.models import Site, Equipment, FieldNote

class TeamMember(models.Model):
    ROLES = [(r, r.title()) for r in ("viewer", "member", "researcher", "manager", "admin")]
    user = models.OneToOneField(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="team_member")
    role = models.CharField(max_length=15, choices=ROLES, default="viewer")
    sites = models.ManyToManyField(Site, blank=True, help_text="Empty means access to all sites.")
    def __str__(self):
        return f"{self.user}: {self.role}"

class Visit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="visits")
    legacy_note = models.OneToOneField(FieldNote, null=True, blank=True, on_delete=models.PROTECT, related_name="hub_visit")
    date = models.DateField(default=timezone.localdate)
    crew = models.CharField(max_length=500, blank=True)
    title = models.CharField(max_length=250, blank=True)
    classification = models.CharField(max_length=15, choices=[("routine", "Routine"), ("major", "Major work"), ("fault", "Fault")], default="routine")
    status = models.CharField(max_length=10, choices=[("open", "Open"), ("closed", "Closed")], default="open")
    narrative = models.TextField(blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-date", "-started_at"]
        indexes = [models.Index(fields=["site", "date"])]
    def __str__(self):
        return f"{self.site.code} · {self.date} · {self.title or 'Field visit'}"

class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="tasks")
    equipment = models.ForeignKey(Equipment, null=True, blank=True, on_delete=models.PROTECT)
    title = models.CharField(max_length=250)
    details = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=[("normal", "Normal"), ("high", "High")], default="normal")
    status = models.CharField(max_length=10, choices=[("pending", "Pending"), ("done", "Done"), ("archived", "Archived")], default="pending")
    due_date = models.DateField(null=True, blank=True)
    created_visit = models.ForeignKey(Visit, null=True, blank=True, on_delete=models.PROTECT)
    created_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)
    class Meta:
        ordering = ["created_at"]
    def __str__(self):
        return self.title

class TaskActivity(models.Model):
    """Append-only event; never inferred from a task's current state."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="activities")
    visit = models.ForeignKey(Visit, null=True, blank=True, on_delete=models.PROTECT, related_name="task_activities")
    action = models.CharField(max_length=20)
    task_title = models.CharField(max_length=250)
    text = models.TextField(blank=True)
    author = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    author_name = models.CharField(max_length=200, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    recorded_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["occurred_at", "recorded_at"]

class VisitObservation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.ForeignKey(Visit, on_delete=models.PROTECT, related_name="observations")
    text = models.TextField()
    author = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    author_name = models.CharField(max_length=200, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    recorded_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["occurred_at"]

class VisitReport(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.PROTECT, related_name="reports")
    revision = models.PositiveIntegerField()
    text = models.TextField()
    markdown = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    class Meta:
        ordering = ["-revision"]
        constraints = [models.UniqueConstraint(fields=["visit", "revision"], name="unique_visit_report_revision")]

class Deployment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name="deployments")
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="deployments")
    installed_at = models.DateTimeField()
    removed_at = models.DateTimeField(null=True, blank=True)
    height_m = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    depth_m = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    variables = models.CharField(max_length=500, blank=True)
    position = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    def clean(self):
        if self.removed_at and self.removed_at <= self.installed_at:
            raise ValidationError("Removal must be after installation.")
        if self.depth_m is not None and self.depth_m < 0:
            raise ValidationError("Depth must be positive downward.")
        qs = Deployment.objects.filter(equipment=self.equipment).exclude(pk=self.pk)
        if self.removed_at:
            qs = qs.filter(installed_at__lt=self.removed_at)
        qs = qs.filter(models.Q(removed_at__isnull=True) | models.Q(removed_at__gt=self.installed_at))
        if qs.exists():
            raise ValidationError("This instrument already has a deployment overlapping this period.")

class ConfigurationVersion(models.Model):
    """Immutable settings with explicit start/end; corrections create a replacement."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="configurations")
    deployment = models.ForeignKey(Deployment, null=True, blank=True, on_delete=models.PROTECT, related_name="configurations")
    label = models.CharField(max_length=200)
    effective_from = models.DateTimeField()
    effective_to = models.DateTimeField(null=True, blank=True)
    time_basis = models.CharField(max_length=30, default="EST_FIXED_UTC_MINUS_05")
    settings = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    supersedes = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT)
    created_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    def clean(self):
        if self.effective_to and self.effective_to <= self.effective_from:
            raise ValidationError("Effective end must follow the start.")
        if self.deployment and self.deployment.site_id != self.site_id:
            raise ValidationError("Configuration and deployment must belong to the same site.")

class DataCaveat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sites = models.ManyToManyField(Site, related_name="caveats")
    source_visit = models.ForeignKey(Visit, null=True, blank=True, on_delete=models.PROTECT)
    equipment = models.ForeignKey(Equipment, null=True, blank=True, on_delete=models.PROTECT)
    configurations = models.ManyToManyField(ConfigurationVersion, blank=True, related_name="caveats")
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    treatment = models.TextField(blank=True)
    variables = models.CharField(max_length=500, blank=True)
    affected_from = models.DateTimeField(null=True, blank=True)
    affected_to = models.DateTimeField(null=True, blank=True)
    period_label = models.CharField(max_length=500, blank=True)
    time_basis = models.CharField(max_length=30, default="EST_FIXED_UTC_MINUS_05")
    status = models.CharField(max_length=15, choices=[("draft", "Draft"), ("reviewed", "Reviewed"), ("resolved", "Resolved")], default="draft")
    public_reference = models.BooleanField(default=False)
    evidence = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)
    def clean(self):
        if self.affected_from and self.affected_to and self.affected_to <= self.affected_from:
            raise ValidationError("Affected end must follow the start.")
    def __str__(self):
        return self.title

def attachment_path(instance, filename):
    return f"attachments/{instance.id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()[:12]}"

class Attachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name="attachments")
    visit = models.ForeignKey(Visit, null=True, blank=True, on_delete=models.PROTECT, related_name="attachments")
    task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.PROTECT, related_name="attachments")
    activity = models.ForeignKey(TaskActivity, null=True, blank=True, on_delete=models.PROTECT, related_name="attachments")
    observation = models.ForeignKey(VisitObservation, null=True, blank=True, on_delete=models.PROTECT, related_name="attachments")
    equipment = models.ForeignKey(Equipment, null=True, blank=True, on_delete=models.PROTECT, related_name="attachments")
    caveat = models.ForeignKey(DataCaveat, null=True, blank=True, on_delete=models.PROTECT, related_name="attachments")
    calibration = models.ForeignKey("hub.CalibrationLog", null=True, blank=True, on_delete=models.PROTECT, related_name="attachments")
    configuration = models.ForeignKey(ConfigurationVersion, null=True, blank=True, on_delete=models.PROTECT, related_name="attachments")
    file = models.FileField(upload_to=attachment_path)
    filename = models.CharField(max_length=250)
    caption = models.CharField(max_length=500, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    sha256 = models.CharField(max_length=64)
    size = models.PositiveBigIntegerField(default=0)
    uploaded_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

class ChecklistTemplate(models.Model):
    name = models.CharField(max_length=200)
    tasks = models.JSONField(default=list, help_text="List of objects with title, details, priority.")
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.name

class AuditEvent(models.Model):
    actor = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    actor_name = models.CharField(max_length=200, blank=True)
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=100)
    site = models.ForeignKey(Site, null=True, on_delete=models.PROTECT)
    detail = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at"]

class OperationReceipt(models.Model):
    operation_id = models.UUIDField()
    actor = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    payload_hash = models.CharField(max_length=64)
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["operation_id", "actor"], name="unique_user_operation")]

class ImportRecord(models.Model):
    source = models.CharField(max_length=100)
    source_id = models.CharField(max_length=300)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    imported_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["source", "source_id"], name="unique_import_source")]

from .resources_models import SiteCondition, BADMProfile, BADMRecord, Protocol, SiteMedia, TowerStatus, TowerReading, ProcessingFile, ProcessingFileVersion

from .record_models import CalibrationLog, KnowledgeEntry, KnowledgeFile
