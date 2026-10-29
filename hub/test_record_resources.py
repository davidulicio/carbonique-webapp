"""Calibration workflows and scoped technical reference files."""
import io
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient
from inventory.models import Site, Equipment
from .models import TeamMember, Visit, CalibrationLog, KnowledgeEntry, KnowledgeFile, Attachment, AuditEvent, Deployment

class RecordResourcesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.writer=User.objects.create_user('writer',password='test-password-long')
        cls.viewer=User.objects.create_user('reader',password='test-password-long')
        cls.limited=User.objects.create_user('limited',password='test-password-long')
        for user,role in [(cls.writer,'member'),(cls.viewer,'viewer'),(cls.limited,'member')]:
            TeamMember.objects.create(user=user,role=role)
        cls.site=Site.objects.create(code='QA1',name='First tower',date_activated='2025-01-01')
        cls.other=Site.objects.create(code='QA2',name='Other tower',date_activated='2025-01-01')
        cls.limited.team_member.sites.add(cls.site)
        cls.sensor=Equipment.objects.create(instrument='Water sensor',serial_number='old',site=cls.site,date_purchased='2025-01-01')
        cls.replacement=Equipment.objects.create(instrument='Prepared water sensor',serial_number='new',date_purchased='2025-01-01')
    def setUp(self):
        self.client=APIClient();self.client.force_authenticate(self.writer)
        self.media=tempfile.TemporaryDirectory();self.addCleanup(self.media.cleanup)
        setting=override_settings(MEDIA_ROOT=Path(self.media.name));setting.enable();self.addCleanup(setting.disable)
    def payload(self,**extra):
        return dict(event_type='swap',event_date='2026-10-20',sensor_name='Water table sensor',sensor_model='CS456',serial_number='old',replacement_serial_number='new',replacement_description='Cleaned CS456',preparation='cleaned_calibrated',lab_calibrated_on='2026-10-12',notes='Checked against reference head.',**extra)
    def calibration(self,site=None,**extra):
        return CalibrationLog.objects.create(site=site or self.site,**self.payload(**extra))
    def op(self,kind='calibration.create',pk=None,payload=None,version=None,opid=None):
        data=dict(id=str(opid or uuid.uuid4()),entity_id=str(pk or uuid.uuid4()),kind=kind,site_id=self.site.pk,payload=payload if payload is not None else self.payload(),occurred_at=timezone.now().isoformat())
        if version is not None:data['base_version']=version
        return data
    def send(self,op):
        result=self.client.post('/api/sync/',{'operations':[op]},format='json')
        self.assertEqual(result.status_code,200,result.data)
        return result.data['results'][0]
    def reference(self,site=None):
        return KnowledgeEntry.objects.create(site=site,title='Tower wiring',category='wiring',body='Cable and repair notes')
    def upload(self,entry,name='wiring.txt',data=b'Wiring revision A'):
        return self.client.post(f'/api/knowledge/{entry.pk}/files/',{'files':[SimpleUploadedFile(name,data)]},format='multipart')
    def test_calibration_swap_preserves_inventory_and_deployments(self):
        data=self.payload();data.update(equipment=self.sensor.pk,replacement_equipment=self.replacement.pk)
        response=self.client.post(f'/api/sites/{self.site.pk}/calibrations/',data,format='json')
        self.assertEqual(response.status_code,201,response.data)
        record=CalibrationLog.objects.get();self.assertEqual(record.created_by,self.writer)
        self.sensor.refresh_from_db();self.replacement.refresh_from_db()
        self.assertEqual(self.sensor.site,self.site);self.assertIsNone(self.replacement.site)
        self.assertEqual(Deployment.objects.count(),0)
        snapshot=self.client.get(f'/api/snapshot/?site={self.site.pk}').data
        self.assertEqual(snapshot['calibrations'][0]['id'],str(record.pk))
        self.assertEqual(len(self.client.get(f'/api/sites/{self.other.pk}/calibrations/').data['calibrations']),0)
    def test_calibration_on_site_and_lab_allow_unknown_serials(self):
        for kind in ['onsite','lab']:
            response=self.client.post(f'/api/sites/{self.site.pk}/calibrations/',dict(event_date='2026-10-20',event_type=kind,sensor_name='Temperature probe',notes='Historical record; serial unknown'),format='json')
            self.assertEqual(response.status_code,201,response.data)
    def test_calibration_invalid_fields_roll_back(self):
        scenarios=[{'replacement_serial_number':'','replacement_description':''},{'preparation':''},{'replacement_serial_number':' OLD '},{'equipment':self.sensor.pk,'replacement_equipment':self.sensor.pk},{'lab_calibrated_on':'2026-10-21'},{'next_due_on':'2026-10-01'},{'event_type':'onsite'},{'sensor_name':''},{'event_date':'invalid'}]
        for fields in scenarios:
            data=self.payload();data.update(fields)
            with self.subTest(fields=fields):
                result=self.client.post(f'/api/sites/{self.site.pk}/calibrations/',data,format='json')
                self.assertEqual(result.status_code,400,result.data)
                self.assertEqual(CalibrationLog.objects.count(),0)
    def test_calibration_visit_must_belong_to_same_site(self):
        visit=Visit.objects.create(site=self.other,date='2026-10-20')
        data=self.payload();data['source_visit']=str(visit.pk)
        result=self.client.post(f'/api/sites/{self.site.pk}/calibrations/',data,format='json')
        self.assertEqual(result.status_code,400);self.assertEqual(CalibrationLog.objects.count(),0)
    def test_calibration_edit_requires_version_and_archives_without_delete(self):
        record=self.calibration();url=f'/api/sites/{self.site.pk}/calibrations/{record.pk}/'
        self.assertEqual(self.client.patch(url,{'notes':'new'},format='json').status_code,400)
        self.assertEqual(self.client.patch(url,{'notes':'new','base_version':1},format='json').status_code,200)
        self.assertEqual(self.client.patch(url,{'notes':'stale','base_version':1},format='json').status_code,409)
        result=self.client.patch(url,{'is_archived':True,'base_version':2},format='json');self.assertEqual(result.status_code,200)
        self.assertEqual(self.client.delete(url).status_code,405)
        self.assertEqual(self.client.patch(url,{'is_archived':False,'base_version':3},format='json').status_code,200)
        record.refresh_from_db();self.assertEqual(record.notes,'new');self.assertEqual(record.version,4)
    def test_offline_calibration_receipt_retry_and_edit(self):
        operation=self.op();first=self.send(operation);self.assertTrue(first['ok'],first)
        self.assertEqual(self.send(operation),first);self.assertEqual(CalibrationLog.objects.count(),1)
        edit=self.op('calibration.edit',operation['entity_id'],{'notes':'Rechecked'},1)
        self.assertTrue(self.send(edit)['ok']);self.assertTrue(self.send(edit)['ok'])
        record=CalibrationLog.objects.get();self.assertEqual(record.notes,'Rechecked');self.assertEqual(record.version,2)
        self.assertEqual(self.send(self.op('calibration.edit',record.pk,{'notes':'old'},1))['status'],409)
        self.assertEqual(AuditEvent.objects.filter(action='calibration.created').count(),1)
    def test_calibration_invalid_sync_does_not_create_receipt(self):
        data=self.payload();data['event_date']='invalid'
        operation=self.op(payload=data);self.assertEqual(self.send(operation)['status'],400)
        operation['payload']=self.payload();self.assertTrue(self.send(operation)['ok'])
    def test_calibration_files_retry_download_and_scope(self):
        record=self.calibration();identifier=str(uuid.uuid4())
        def upload(**extra):
            return self.client.post('/api/attachments/',dict(id=identifier,site=self.site.pk,calibration=str(record.pk),file=SimpleUploadedFile('calibration.csv',b'head,offset\n1,0.01'),**extra),format='multipart')
        first=upload();self.assertEqual(first.status_code,201,first.data)
        self.assertEqual(upload().status_code,200);self.assertEqual(Attachment.objects.count(),1)
        self.assertEqual(str(first.data['calibration']),str(record.pk))
        self.client.force_login(self.writer)
        download=self.client.get(first.data['url']);self.assertEqual(b''.join(download.streaming_content),b'head,offset\n1,0.01')
        self.assertEqual(download['Cache-Control'],'private, no-store')
        other=self.calibration(site=self.other)
        result=self.client.post('/api/attachments/',{'id':str(uuid.uuid4()),'site':self.site.pk,'calibration':str(other.pk),'file':SimpleUploadedFile('x.txt',b'x')},format='multipart')
        self.assertEqual(result.status_code,403)
    def test_calibration_file_cannot_attach_to_unrelated_visit_or_archived_record(self):
        record=self.calibration();visit=Visit.objects.create(site=self.site,date='2026-10-20')
        def upload(**extra):
            return self.client.post('/api/attachments/',dict(id=str(uuid.uuid4()),site=self.site.pk,calibration=str(record.pk),file=SimpleUploadedFile('calibration.txt',b'Checked'),**extra),format='multipart')
        self.assertEqual(upload(visit=str(visit.pk)).status_code,400)
        record.is_archived=True;record.save();self.assertEqual(upload().status_code,400)
        self.assertFalse(Attachment.objects.exists())
    def test_calibration_role_and_site_scope(self):
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get(f'/api/sites/{self.site.pk}/calibrations/').status_code,200)
        self.assertEqual(self.send(self.op())['status'],403)
        self.client.force_authenticate(self.limited)
        self.assertEqual(self.client.post(f'/api/sites/{self.other.pk}/calibrations/',self.payload(),format='json').status_code,403)
        hidden=Equipment.objects.create(site=self.other,instrument='Hidden',date_purchased='2025-01-01')
        data=self.payload();data['equipment']=hidden.pk
        self.assertEqual(self.client.post(f'/api/sites/{self.site.pk}/calibrations/',data,format='json').status_code,403)
        self.site.is_archived=True;self.site.save()
        self.assertEqual(self.send(self.op())['status'],403)
    def test_historical_calibration_can_be_edited_after_equipment_moves_out_of_scope(self):
        record=self.calibration();record.equipment=self.sensor;record.save()
        self.sensor.site=self.other;self.sensor.save()
        self.client.force_authenticate(self.limited)
        response=self.client.patch(f'/api/sites/{self.site.pk}/calibrations/{record.pk}/',{'equipment':self.sensor.pk,'notes':'Historical correction','base_version':1},format='json')
        self.assertEqual(response.status_code,200,response.data)
        record.refresh_from_db();self.assertEqual(record.equipment,self.sensor)

    def test_library_create_edit_and_version_conflict(self):
        response=self.client.post('/api/knowledge/',{'title':'Notebook','category':'notes','body':'Repair history','external_url':'https://www.onenote.com/notebooks/share-example'},format='json')
        self.assertEqual(response.status_code,201,response.data)
        url=f"/api/knowledge/{response.data['id']}/"
        self.assertEqual(self.client.patch(url,{'body':'new'},format='json').status_code,400)
        self.assertEqual(self.client.patch(url,{'body':'new','base_version':1},format='json').status_code,200)
        self.assertEqual(self.client.patch(url,{'body':'stale','base_version':1},format='json').status_code,409)
        self.assertEqual(self.client.delete(url).status_code,405)
        self.assertEqual(KnowledgeEntry.objects.get().body,'new')
    def test_library_rejects_unsafe_and_credential_links(self):
        for link in ['javascript:alert(1)','onenote:https://example.test/book','https://user:secret@example.test/file','file:///C:/private','https://[invalid']:
            with self.subTest(link=link):
                result=self.client.post('/api/knowledge/',{'title':'Unsafe link','external_url':link},format='json')
                self.assertEqual(result.status_code,400,result.data)
        self.assertFalse(KnowledgeEntry.objects.exists())
    def test_library_scope_shared_read_and_write_restrictions(self):
        shared=self.reference();own=self.reference(self.site);hidden=self.reference(self.other)
        self.client.force_authenticate(self.limited)
        result=self.client.get('/api/knowledge/');ids={row['id'] for row in result.data['entries']}
        self.assertEqual(ids,{str(shared.pk),str(own.pk)})
        self.assertEqual(self.client.get(f'/api/knowledge/{hidden.pk}/').status_code,404)
        self.assertEqual(self.client.post('/api/knowledge/',{'title':'Shared'},format='json').status_code,403)
        self.assertEqual(self.client.patch(f'/api/knowledge/{shared.pk}/',{'body':'no','base_version':1},format='json').status_code,403)
        self.assertEqual(self.client.patch(f'/api/knowledge/{own.pk}/',{'site':self.other.pk,'base_version':1},format='json').status_code,403)
        self.assertEqual(self.client.patch(f'/api/knowledge/{own.pk}/',{'site':None,'base_version':1},format='json').status_code,403)
        self.assertEqual(self.client.patch(f'/api/knowledge/{own.pk}/',{'body':'yes','base_version':1},format='json').status_code,200)
        self.assertFalse(self.client.get('/api/bootstrap/').data['me']['can_edit_shared_references'])
    def test_viewer_can_download_library_but_cannot_modify(self):
        record=self.reference(self.site);upload=self.upload(record);self.assertEqual(upload.status_code,200)
        file=KnowledgeFile.objects.get();self.client.force_authenticate(self.viewer)
        response=self.client.get(f'/knowledge-files/{file.pk}/');self.assertEqual(response.status_code,200)
        # Consume the test client iterator so cleanup preserves the test transaction.
        self.assertEqual(b''.join(response.streaming_content),b'Wiring revision A')
        self.assertTrue(response.closed)
        self.assertEqual(self.client.post('/api/knowledge/',{'title':'No'},format='json').status_code,403)
        self.assertEqual(self.upload(record).status_code,403)
    def test_library_files_bytes_duplicate_retry_and_private_download(self):
        record=self.reference(self.site)
        self.assertEqual(self.upload(record).data['added'],1)
        self.assertEqual(self.upload(record).data['unchanged'],1)
        self.assertEqual(record.files.count(),1)
        file=record.files.get();response=self.client.get(f'/knowledge-files/{file.pk}/')
        self.assertEqual(b''.join(response.streaming_content),b'Wiring revision A')
        self.assertIn('attachment',response['Content-Disposition']);self.assertIn('sandbox',response['Content-Security-Policy'])
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f'/knowledge-files/{file.pk}/').status_code,403)
    def test_library_cross_site_file_read_and_mutation_denied(self):
        record=self.reference(self.other);self.upload(record);file=record.files.get()
        self.client.force_authenticate(self.limited)
        self.assertEqual(self.client.get(f'/knowledge-files/{file.pk}/').status_code,404)
        self.assertEqual(self.upload(record).status_code,404)
        self.assertEqual(self.client.patch(f'/api/knowledge/{record.pk}/files/{file.pk}/',{'is_archived':True,'base_version':1},format='json').status_code,404)
    def test_library_file_validation_is_atomic(self):
        record=self.reference(self.site)
        response=self.client.post(f'/api/knowledge/{record.pk}/files/',{'files':[SimpleUploadedFile('good.txt',b'fine'),SimpleUploadedFile('bad.pdf',b'Not PDF')]},format='multipart')
        self.assertEqual(response.status_code,400);self.assertFalse(KnowledgeFile.objects.exists())
        self.assertEqual([p for p in Path(self.media.name).rglob('*') if p.is_file()],[])
        self.assertEqual(self.upload(record,'bad.png',b'not image').status_code,400)
    def test_library_storage_cleans_up_after_database_failure(self):
        record=self.reference(self.site)
        with patch.object(KnowledgeFile,'save',side_effect=RuntimeError('Database failed')):
            with self.assertRaises(RuntimeError):self.upload(record)
        self.assertEqual([p for p in Path(self.media.name).rglob('*') if p.is_file()],[])
        self.assertFalse(KnowledgeFile.objects.exists())
    @override_settings(MAX_UPLOAD_BYTES=8)
    def test_library_limits_total_batch_size_and_file_count(self):
        record=self.reference(self.site)
        self.assertEqual(self.upload(record,data=b'123456789').status_code,400)
        result=self.client.post(f'/api/knowledge/{record.pk}/files/',{'files':[SimpleUploadedFile('a.txt',b'12345'),SimpleUploadedFile('b.txt',b'12345')]},format='multipart')
        self.assertEqual(result.status_code,400);self.assertFalse(KnowledgeFile.objects.exists())
        result=self.client.post(f'/api/knowledge/{record.pk}/files/',{'files':[SimpleUploadedFile(f'{i}.txt',b'') for i in range(11)]},format='multipart')
        self.assertEqual(result.status_code,400)
    def test_library_image_pdf_and_notebook_types(self):
        record=self.reference();buffer=io.BytesIO();Image.new('RGB',(4,4),'green').save(buffer,format='PNG')
        self.assertEqual(self.upload(record,'photo.png',buffer.getvalue()).status_code,200)
        self.assertEqual(self.upload(record,'manual.pdf',b'%PDF-1.4\nexample').status_code,200)
        self.assertEqual(self.upload(record,'notebook.one',b'original notebook bytes').status_code,200)
        types=set(record.files.values_list('content_type',flat=True))
        self.assertEqual(types,{'image/png','application/pdf','application/octet-stream'})
        response=self.client.get(f"/knowledge-files/{record.files.get(content_type='image/png').pk}/")
        self.assertIn('inline',response['Content-Disposition'])
        self.assertEqual(b''.join(response.streaming_content),buffer.getvalue())
        self.assertTrue(response.closed)
    def test_library_archive_restore_retains_files(self):
        record=self.reference(self.site);self.upload(record);file=record.files.get()
        url=f'/api/knowledge/{record.pk}/files/{file.pk}/'
        self.assertEqual(self.client.patch(url,{'is_archived':True},format='json').status_code,400)
        self.assertEqual(self.client.patch(url,{'is_archived':'true','base_version':1},format='json').status_code,400)
        self.assertEqual(self.client.patch(url,{'is_archived':True,'base_version':1},format='json').status_code,200)
        self.assertEqual(self.client.patch(url,{'is_archived':False,'base_version':1},format='json').status_code,409)
        self.assertEqual(self.client.patch(url,{'is_archived':False,'base_version':2},format='json').status_code,200)
        self.assertEqual(self.client.patch(f'/api/knowledge/{record.pk}/',{'is_archived':True,'base_version':1},format='json').status_code,200)
        self.assertEqual(self.upload(record).status_code,400)
        response=self.client.get(f'/knowledge-files/{file.pk}/');self.assertEqual(response.status_code,200)
        self.assertEqual(b''.join(response.streaming_content),b'Wiring revision A')
        self.assertTrue(response.closed)
        self.assertEqual(self.client.patch(f'/api/knowledge/{record.pk}/',{'is_archived':False,'base_version':2},format='json').status_code,200)
        with self.assertRaises(ProtectedError):record.delete()
    def test_library_archived_site_is_read_only(self):
        record=self.reference(self.site);self.upload(record);file=record.files.get()
        self.site.is_archived=True;self.site.save()
        self.assertEqual(self.client.patch(f'/api/knowledge/{record.pk}/',{'body':'no','base_version':1},format='json').status_code,403)
        self.assertEqual(self.upload(record).status_code,403)
        self.assertEqual(self.client.get(f'/api/knowledge/{record.pk}/').status_code,200)
        self.assertEqual(self.client.patch(f'/api/knowledge/{record.pk}/files/{file.pk}/',{'is_archived':True,'base_version':1},format='json').status_code,403)
    def test_public_projection_excludes_calibrations_and_technical_uploads(self):
        self.calibration();record=self.reference(self.site);self.upload(record,'private-wiring.txt',b'Private troubleshooting details')
        self.client.force_authenticate(None)
        result=self.client.get('/fieldnotes/')
        self.assertEqual(result.status_code,200)
        content=result.content.decode()
        self.assertNotIn('Private troubleshooting details',content);self.assertNotIn('private-wiring.txt',content)
        self.assertNotIn('Checked against reference head.',content)
        self.assertEqual(self.client.get('/api/knowledge/').status_code,403)
        self.assertEqual(self.client.get(f'/api/sites/{self.site.pk}/calibrations/').status_code,403)

    def test_calibration_linked_visit_serializes_in_receipt_and_audit(self):
        visit=Visit.objects.create(site=self.site,date='2026-10-20')
        data=self.payload();data['source_visit']=str(visit.pk)
        operation=self.op(payload=data);result=self.send(operation);self.assertTrue(result['ok'],result)
        self.assertEqual(result['record']['source_visit'],str(visit.pk))
        self.assertEqual(self.send(operation),result)
        self.assertTrue(self.send(self.op('calibration.edit',operation['entity_id'],{'notes':'confirmed'},1))['ok'])


class CalibrationImportTests(TestCase):
    def setUp(self):
        import json
        from django.conf import settings
        self.rows=json.loads((settings.BASE_DIR/'seed/calibration_swaps.json').read_text(encoding='utf-8'))
        self.row=self.rows[0]
        self.site=Site.objects.create(code=self.row['site'],name='Source site',date_activated='2025-01-01')
        self.visit=Visit.objects.create(pk=self.row['source_visit'],site=self.site,date=self.row['event_date'],title=self.row['source_title'],crew='Original crew',narrative='Original narrative, unchanged.')
    def run_import(self,*args):
        from django.core.management import call_command
        call_command('import_calibrations',*args,stdout=io.StringIO())
    def test_import_confirmed_swaps_preserves_originals_and_manager_edits(self):
        self.run_import();self.assertEqual(CalibrationLog.objects.count(),2)
        record=CalibrationLog.objects.order_by('sensor_name').first()
        self.assertEqual(record.preparation,'cleaned_calibrated');self.assertEqual(record.source_visit_id,uuid.UUID(str(self.visit.pk)))
        self.assertIsNone(record.lab_calibrated_on);self.assertEqual(record.serial_number,'')
        record.notes='Reviewed correction';record.is_archived=True;record.save()
        self.run_import();record.refresh_from_db()
        self.assertEqual(CalibrationLog.objects.count(),2);self.assertEqual(record.notes,'Reviewed correction');self.assertTrue(record.is_archived)
        self.visit.refresh_from_db();self.assertEqual(self.visit.narrative,'Original narrative, unchanged.')
    def test_import_dry_run_and_missing_source_visits_do_not_write(self):
        self.run_import('--dry-run');self.assertEqual(CalibrationLog.objects.count(),0)
        self.visit.delete();self.run_import();self.assertEqual(CalibrationLog.objects.count(),0)
    def test_reviewed_manifest_excludes_planned_and_cancelled_swaps(self):
        keys={(row['site'],row['event_date']) for row in self.rows}
        self.assertEqual(len(self.rows),18)
        for key in [('MCGILL_1','2026-07-15'),('MCGILL_1','2025-08-19'),('UQAM_3','2025-07-16'),('UQAM_4','2026-09-17')]:self.assertNotIn(key,keys)
