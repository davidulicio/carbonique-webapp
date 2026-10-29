"""Portable restore drill using only a disposable test database and files."""
import hashlib,tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TransactionTestCase,override_settings
from inventory.models import Site
from .models import TeamMember,Visit,Task,Attachment


class BackupRestoreTests(TransactionTestCase):
    def test_restore_preserves_accounts_record_links_and_private_file_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source';target=root/'restored';backup=root/'backup.zip'
            with override_settings(MEDIA_ROOT=source):
                user=get_user_model().objects.create_user('restore-fixture',password='Disposable-restore-password-2026')
                TeamMember.objects.create(user=user,role='member')
                site=Site.objects.create(code='RESTORE',name='Restore fixture',date_activated='2025-01-01');user.team_member.sites.add(site)
                visit=Visit.objects.create(site=site,title='Restored visit')
                task=Task.objects.create(site=site,title='Restored task',created_visit=visit,created_by=user)
                data=b'Private calibration bytes\x00\xff'
                item=Attachment.objects.create(site=site,visit=visit,task=task,uploaded_by=user,filename='calibration.dat',size=len(data),sha256=hashlib.sha256(data).hexdigest(),file=ContentFile(data,name='calibration.dat'))
                task_id,item_id=task.pk,item.pk
                call_command('backup_hub',output=str(backup),verbosity=0)
            call_command('flush',interactive=False,verbosity=0)
            with override_settings(MEDIA_ROOT=target):
                call_command('restore_hub',file=str(backup),verbosity=0)
                restored=get_user_model().objects.get(username='restore-fixture');self.assertTrue(restored.check_password('Disposable-restore-password-2026'))
                self.assertEqual(restored.team_member.sites.get().code,'RESTORE')
                task=Task.objects.get(pk=task_id);self.assertEqual(task.created_visit.title,'Restored visit');self.assertEqual(task.created_by_id,restored.pk)
                item=Attachment.objects.get(pk=item_id);self.assertEqual(item.task_id,task.pk)
                with item.file.open('rb') as handle:self.assertEqual(handle.read(),data)
                self.assertEqual(item.sha256,hashlib.sha256(data).hexdigest())
