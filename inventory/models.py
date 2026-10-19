# Can add 'help_text' to each field creation call, see
# https://docs.djangoproject.com/en/5.2/topics/db/models/, look for
# help_text

from django.db import models
from django.core.exceptions import ValidationError
from django.urls import NoReverseMatch
from django.urls import reverse
from django.utils.timezone import now
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType

from inventory.media_processing.media_paths import (
    site_photo_upload_path,
    document_upload_path,
    document_thumbnail_upload_path,
    image_thumbnail_upload_path,
)
from inventory.media_processing.thumbnails import (
    generate_image_thumbnail,
    generate_pdf_thumbnail,
    generate_thumbnail_name,
)


class GetDocumentMixin:
    """Mixin providing helper class for objects that can be related to
    Documents.

    It provides 2 equivalent ways to get related documents."""

    def get_documents(self):
        """Return all documents associated with an object of this class."""

        return Document.objects.filter(
            content_type=ContentType.objects.get_for_model(self.__class__),
            object_id=self.id,
        )

    @property
    def documents(self):

        return self.get_documents()


class ThumbnailMixin:
    """Mixin providing a save() method for classes that produce
    thumbnails for larger images or PDF files."""

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and not self.thumbnail:
            self.generate_thumbnail()
            super().save(update_fields=["thumbnail"])


class Site(models.Model, GetDocumentMixin):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=10)  # , help_text="Short code for internal use")
    amp = models.CharField(
        max_length=10
    )  # , help_text="AmeriFlux Management Project code")
    location = models.CharField(max_length=250)
    description = models.TextField()  # help_text="Full site description")
    date_activated = models.DateField()
    date_retired = models.DateField(blank=True, null=True)
    gps_coordinates = models.CharField(max_length=50, blank=True)
    is_archived = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    public_reference = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.code}: {self.name}"

    def clean(self):
        if self.date_retired and self.date_activated and self.date_retired < self.date_activated:
            raise ValidationError("Retirement cannot precede site activation.")


class Document(ThumbnailMixin, models.Model):
    # Generic relation fields
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    # Important: GenericForeignKey is not a database field! Only
    # content_type and object_id are actual database columns.
    content_object = GenericForeignKey("content_type", "object_id")
    object_description = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )
    date_uploaded = models.DateField(default=now)
    submitter = models.CharField(max_length=50, blank=True, null=True)
    date_received = models.DateField()
    summary = models.CharField(max_length=80)
    thumbnail = models.ImageField(
        verbose_name="thumbnail",
        upload_to=document_thumbnail_upload_path,
        blank=True,
        null=True,
    )
    file = models.FileField(
        verbose_name="document",
        upload_to=document_upload_path,
        blank=False,
        null=False,
    )

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def save(self, *args, **kwargs):
        self.object_description = f"{self.content_object}"
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Delete associated files along with the document."""

        self.file.delete(save=False)
        self.thumbnail.delete(save=False)
        super().delete(*args, **kwargs)

    def generate_thumbnail(self):
        if self.file and not self.thumbnail:
            thumb = generate_pdf_thumbnail(self.file)
            if thumb is None:
                return
            unique_name = generate_thumbnail_name(self.file.name)
            self.thumbnail.save(unique_name, thumb, save=False)

    def context_object_display(self):
        """Only needed by
        inventory/management/commands/0012_generate_object_description.py"""
        obj = self.content_object
        if not obj:
            return "-"
        return str(obj)

    @property
    def context_object_url(self):
        obj = self.content_object
        if not obj:
            return None
        try:
            return reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])
        except NoReverseMatch:
            return None


class FieldNote(models.Model, GetDocumentMixin):
    site = models.ForeignKey(Site, related_name="fieldnotes", on_delete=models.PROTECT)
    documents = GenericRelation(Document)
    note = models.TextField()
    date_visited = models.DateField(default=now)
    summary = models.CharField(max_length=80, blank=True)
    submitter = models.CharField(max_length=50, blank=True)
    site_visitors = models.CharField(max_length=250, blank=True, default="")

    def __str__(self):
        return f"Visit to {self.site} on {self.date_visited}"


class Photo(ThumbnailMixin, models.Model):
    photo = models.ImageField(upload_to=site_photo_upload_path, blank=False, null=False)
    date_taken = models.DateField(blank=True, null=True)
    taken_by = models.CharField(max_length=100, blank=True)
    fieldnote = models.ForeignKey(
        FieldNote, on_delete=models.CASCADE, related_name="photos"
    )
    thumbnail = models.ImageField(
        verbose_name="thumbnail",
        upload_to=image_thumbnail_upload_path,
        blank=True,
        null=True,
    )

    def delete(self, *args, **kwargs):
        """Delete associated files along with the photo entry."""

        self.photo.delete(save=False)
        self.thumbnail.delete(save=False)
        super().delete(*args, **kwargs)

    def generate_thumbnail(self):
        if self.photo and not self.thumbnail:
            thumb = generate_image_thumbnail(self.photo)
            unique_name = generate_thumbnail_name(self.photo.name)
            self.thumbnail.save(unique_name, thumb, save=False)


class DOI(models.Model):
    """Class for a Data Object Identifier to a Site"""

    label = models.CharField(max_length=20)
    doi_link = models.URLField()
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="doi_records")


class Equipment(models.Model, GetDocumentMixin):
    instrument = models.CharField(max_length=75)
    manufacturer = models.CharField(max_length=75, blank=True)
    model_number = models.CharField(max_length=75, blank=True)
    serial_number = models.CharField(max_length=50, blank=True)
    date_purchased = models.DateField()
    notes = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default="available")
    version = models.PositiveIntegerField(default=1)
    site = models.ForeignKey(
        Site, on_delete=models.SET_NULL, null=True, blank=True, related_name="equipment"
    )

    def __str__(self):
        return f"{self.instrument} - {self.serial_number}"


class History(models.Model):
    date = models.DateField(default=now)
    note = models.TextField()
    item = models.ForeignKey(
        Equipment, related_name="history", on_delete=models.CASCADE
    )
