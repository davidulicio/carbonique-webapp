import io
import tempfile
import uuid
import wave

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from inventory.models import Site
from .models import Attachment, Task, TaskActivity, TeamMember, Visit, VisitObservation


class NoteAttachmentTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        override=override_settings(MEDIA_ROOT=self.temp.name);override.enable();self.addCleanup(override.disable)
        self.site=Site.objects.create(code='NOTE_A',name='Note site',amp='CA-Nta',location='Quebec',description='Site',date_activated='2025-01-01')
        self.other=Site.objects.create(code='NOTE_B',name='Other site',amp='CA-Ntb',location='Quebec',description='Other',date_activated='2025-01-01')
        self.user=get_user_model().objects.create_user('field-member',password='field-test-password')
        member=TeamMember.objects.create(user=self.user,role='member');member.sites.add(self.site)
        self.client=APIClient();self.client.force_login(self.user);self.client.force_authenticate(self.user)
        self.visit=Visit.objects.create(site=self.site,title='Field visit')
        self.note=VisitObservation.objects.create(visit=self.visit,text='Individual observation')
        self.task=Task.objects.create(site=self.site,title='Inspect sensor')
        self.activity=TaskActivity.objects.create(task=self.task,visit=self.visit,action='commented',task_title=self.task.title,text='Individual task note')

    def upload(self,**fields):
        payload={'id':str(uuid.uuid4()),'site':self.site.pk,'file':SimpleUploadedFile('notes.txt',b'field document')}
        payload.update(fields)
        return self.client.post('/api/attachments/',payload,format='multipart')

    def test_observation_upload_retains_note_and_visit_links(self):
        response=self.upload(observation=str(self.note.pk))
        self.assertEqual(response.status_code,201,response.data)
        self.assertEqual(response.data['observation'],self.note.pk)
        self.assertEqual(response.data['visit'],self.visit.pk)
        snapshot=self.client.get(f'/api/snapshot/?site={self.site.pk}')
        self.assertEqual(snapshot.data['attachments'][0]['observation'],self.note.pk)

    def test_activity_upload_retains_task_and_visit_links(self):
        response=self.upload(activity=str(self.activity.pk))
        self.assertEqual(response.status_code,201,response.data)
        self.assertEqual(response.data['task'],self.task.pk)
        self.assertEqual(response.data['visit'],self.visit.pk)

    def test_cross_site_note_is_rejected(self):
        visit=Visit.objects.create(site=self.other)
        note=VisitObservation.objects.create(visit=visit,text='Other site observation')
        self.assertEqual(self.upload(observation=str(note.pk)).status_code,403)
        self.assertEqual(Attachment.objects.count(),0)

    def test_inconsistent_task_or_visit_is_rejected(self):
        other=Task.objects.create(site=self.site,title='Different task')
        response=self.upload(activity=str(self.activity.pk),task=str(other.pk))
        self.assertEqual(response.status_code,400)
        visit=Visit.objects.create(site=self.site,title='Different visit')
        self.assertEqual(self.upload(activity=str(self.activity.pk),visit=str(visit.pk)).status_code,400)

    def test_offsite_activity_cannot_be_reassigned_to_a_visit(self):
        self.activity.visit=None;self.activity.save()
        self.assertEqual(self.upload(activity=str(self.activity.pk),visit=str(self.visit.pk)).status_code,400)

    def test_retry_is_idempotent_but_dropping_a_note_link_is_a_conflict(self):
        ident=str(uuid.uuid4())
        for expected in [201,200]:
            response=self.upload(id=ident,observation=str(self.note.pk))
            self.assertEqual(response.status_code,expected,response.data)
        self.assertEqual(self.upload(id=ident).status_code,409)
        self.assertEqual(Attachment.objects.count(),1)

    def test_offline_activity_identifier_is_preserved_on_retry(self):
        activity_id=str(uuid.uuid4())
        operation={'id':str(uuid.uuid4()),'entity_id':str(self.task.pk),'site_id':self.site.pk,
            'kind':'task.comment','payload':{'text':'Offline note','activity_id':activity_id}}
        for _ in range(2):
            response=self.client.post('/api/sync/',{'operations':[operation]},format='json')
            self.assertTrue(response.data['results'][0]['ok'],response.data)
        self.assertEqual(TaskActivity.objects.filter(pk=activity_id).count(),1)
        self.assertEqual(self.upload(activity=activity_id).status_code,201)

    def test_audio_download_supports_seeking_and_site_permissions(self):
        buffer=io.BytesIO()
        with wave.open(buffer,'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(8000);stream.writeframes(b'\x00\x00'*100)
        response=self.upload(observation=str(self.note.pk),file=SimpleUploadedFile('field.wav',buffer.getvalue()))
        self.assertEqual(response.status_code,201,response.data)
        url=response.data['url']
        response=self.client.get(url,HTTP_RANGE='bytes=0-3')
        self.assertEqual(response.status_code,206);self.assertEqual(b''.join(response.streaming_content),b'RIFF')
        self.assertEqual(self.client.head(url).status_code,200)
        self.client.force_authenticate(None);self.client.logout()
        self.assertEqual(self.client.get(url).status_code,302)

    def test_files_can_be_added_to_historical_notes_without_changing_frozen_text(self):
        self.visit.status='closed';self.visit.save()
        self.assertEqual(self.upload(observation=str(self.note.pk)).status_code,201)
        self.note.refresh_from_db();self.assertEqual(self.note.text,'Individual observation')

    def test_viewer_cannot_upload(self):
        self.user.team_member.role='viewer';self.user.team_member.save()
        self.assertEqual(self.upload(task=str(self.task.pk)).status_code,403)
