import importlib
import tempfile
import uuid
from types import SimpleNamespace

from django.apps import apps
from django.core.files.base import ContentFile
from django.db import connection
from django.test import TestCase, override_settings
from .models import Protocol


class ProtocolRemovalTests(TestCase):
    def test_only_the_retired_protocol_and_its_protected_copy_are_removed(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            retired=Protocol.objects.create(id=uuid.uuid5(uuid.NAMESPACE_URL,'carbonique-protocol:Data_download.pdf'),
                title='Data download procedure',filename='Data_download.pdf',sha256='0'*64)
            retired.file.save('Data_download.pdf',ContentFile(b'%PDF-1.4\nretired protocol'),save=True)
            name,storage=retired.file.name,retired.file.storage
            other=Protocol.objects.create(title='Keep this protocol',filename='keep.pdf',sha256='1'*64)
            migration=importlib.import_module('hub.migrations.0006_remove_data_download_protocol')
            with self.captureOnCommitCallbacks(execute=True):
                migration.remove_protocol(apps,SimpleNamespace(connection=connection))
            self.assertFalse(Protocol.objects.filter(pk=retired.pk).exists())
            self.assertFalse(storage.exists(name))
            self.assertTrue(Protocol.objects.filter(pk=other.pk).exists())
