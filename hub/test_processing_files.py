import hashlib
import io
import json
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from inventory.models import Site
from .models import ProcessingFile, ProcessingFileVersion, TeamMember


class ProcessingFileTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        override=override_settings(MEDIA_ROOT=self.temp.name);override.enable();self.addCleanup(override.disable)
        self.site=Site.objects.create(code='UQAM_1',name='Marsh',amp='CA-Tst',location='Quebec',description='Site',date_activated='2025-01-01')
        self.user=get_user_model().objects.create_user('processor',password='processing-test-password')
        TeamMember.objects.create(user=self.user,role='researcher')
        self.client=APIClient();self.client.force_authenticate(self.user)

    def upload(self,data=b'trace = 1;\r\n',name='UQAM_1_FirstStage.ini',**extra):
        return self.client.post('/api/processing-files/',{'files':[SimpleUploadedFile(name,data)],**extra},format='multipart')

    def test_changed_versions_keep_original_bytes_and_identical_latest_is_skipped(self):
        first=b'% sensor \xb5\r\ntrace = 1;\r\n'
        result=self.upload(first);self.assertEqual(result.status_code,200,result.data)
        original=result.data['files'][0]['latest'];self.assertEqual(original['revision'],1)
        response=self.upload(first);self.assertEqual(response.data['created'],0)
        response=self.upload(b'trace = 2;\n',note='Updated calibration')
        self.assertEqual(response.data['files'][0]['latest']['revision'],2)
        self.assertEqual(ProcessingFileVersion.objects.count(),2)
        response=self.client.get(original['url'])
        self.assertEqual(b''.join(response.streaming_content),first)
        self.assertIn('sensor µ',self.client.get(original['url']+'?preview=1').data['text'])

    def test_bulk_batch_is_validated_before_any_file_is_saved(self):
        response=self.client.post('/api/processing-files/',{'files':[SimpleUploadedFile('valid.ini',b'trace=1;'),SimpleUploadedFile('bad.py',b'code')]},format='multipart')
        self.assertEqual(response.status_code,400)
        self.assertEqual(ProcessingFileVersion.objects.count(),0)

    def test_paths_cannot_escape_the_library(self):
        for name in ['../outside.ini','C:/private.ini','nested/../outside.ini']:
            response=self.upload(paths=json.dumps([name]))
            self.assertEqual(response.status_code,400,response.data)
        self.assertEqual(ProcessingFile.objects.count(),0)

    def test_anonymous_and_viewers_cannot_upload(self):
        self.user.team_member.role='viewer';self.user.team_member.save()
        self.assertEqual(self.upload().status_code,403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/processing-files/').status_code,403)

    def test_site_scope_applies_to_versions_and_shared_uploads(self):
        own=self.upload().data['files'][0]['latest']['url']
        other=Site.objects.create(code='UQAM_2',name='Other',amp='CA-Alt',location='Quebec',description='Other',date_activated='2025-01-01')
        other_url=self.upload(name='UQAM_2_FirstStage.ini').data['files'][1]['latest']['url']
        member=self.user.team_member;member.sites.add(self.site)
        response=self.client.get(own);self.assertEqual(response.status_code,200);response.close()
        self.assertEqual(self.client.get(other_url).status_code,404)
        self.assertEqual(self.upload(name='Common_include.ini').status_code,403)
        self.assertEqual(self.upload(name='UQAM_2_FirstStage.ini').status_code,403)

    def test_case_variants_update_the_same_file(self):
        self.upload()
        result=self.upload(b'updated',name='uqam_1_firststage.INI')
        self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(ProcessingFile.objects.count(),1)
        self.assertEqual(ProcessingFileVersion.objects.count(),2)

    def test_bundled_import_preserves_later_team_versions(self):
        call_command('import_processing_files',stdout=io.StringIO())
        self.assertEqual(ProcessingFile.objects.count(),20)
        document=ProcessingFile.objects.get(path='UQAM_1/UQAM_1_FirstStage.ini')
        self.upload(b'team revision')
        call_command('import_processing_files',stdout=io.StringIO())
        document.refresh_from_db()
        self.assertEqual(document.revisions.count(),2)
        self.assertEqual(document.revisions.first().sha256,hashlib.sha256(b'team revision').hexdigest())

    def test_import_directory_is_read_only_and_byte_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'Extra_include.ini';original=b'% original\r\nvalue=1;\r\n';path.write_bytes(original)
            before=path.stat().st_mtime_ns
            call_command('import_processing_files',directory=directory,stdout=io.StringIO())
            self.assertEqual(path.read_bytes(),original);self.assertEqual(path.stat().st_mtime_ns,before)
            version=ProcessingFileVersion.objects.get()
            with version.file.open('rb') as handle:self.assertEqual(handle.read(),original)
