"""Module with functions for getting pathnames for images and documents."""

import os
import uuid

from django.conf import settings


def site_photo_upload_path(instance, filename):
    # Get the extension
    ext = filename.split(".")[-1].lower()
    # Generate a unique filename
    unique_name = f"{uuid.uuid4()}.{ext}"
    # Organize by site ID
    site_id = instance.fieldnote.site.id
    return os.path.join(settings.PHOTO_UPLOAD_SUBDIR, f"site_{site_id}", unique_name)


def document_upload_path(instance, filename):
    # Get the extension
    ext = filename.split(".")[-1].lower()
    # Generate a unique filename
    unique_name = f"{uuid.uuid4()}.{ext}"
    return os.path.join(settings.DOCUMENT_UPLOAD_SUBDIR, unique_name)


def document_thumbnail_upload_path(instance, filename):
    return os.path.join(settings.MEDIA_THUMBNAIL_SUBDIR, "documents", filename)


def image_thumbnail_upload_path(instance, filename):
    return os.path.join(settings.MEDIA_THUMBNAIL_SUBDIR, "images", filename)
