import io
import json
import tempfile
import uuid
from pathlib import Path
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from django.db.models.deletion import ProtectedError
from rest_framework.test import APIClient
from inventory.models import Site, Equipment, FieldNote, Photo, Document
from django.contrib.contenttypes.models import ContentType
from .models import TeamMember, Visit, Task, TaskActivity, VisitReport, Deployment, ConfigurationVersion, DataCaveat, Attachment

class HubTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.admin=User.objects.create_superuser("admin", "admin@example.test", "sufficient-test-password")
        cls.member=User.objects.create_user("member", "member@example.test", "sufficient-test-password")
        cls.researcher=User.objects.create_user("researcher", "researcher@example.test", "sufficient-test-password")
        cls.viewer=User.objects.create_user("viewer", "viewer@example.test", "sufficient-test-password")
        for user,role in [(cls.member,"member"),(cls.researcher,"researcher"),(cls.viewer,"viewer")]:
            TeamMember.objects.create(user=user,role=role)
        cls.site=Site.objects.create(code="UQAM_3",name="Forested bog",amp="CA-CQ3",location="Québec",description="Site",date_activated="2025-04-10")
        cls.other=Site.objects.create(code="UQAM_2",name="Open bog",amp="CA-CQ2",location="Québec",description="Site",date_activated="2025-04-15")
        cls.equipment=Equipment.objects.create(instrument="LI-7200RS",serial_number="test-1",date_purchased="2025-01-01",site=cls.site)
    def setUp(self):
        self.client=APIClient();self.client.force_authenticate(self.admin)
        self.media=tempfile.TemporaryDirectory()
        self.setting=override_settings(MEDIA_ROOT=Path(self.media.name))
        self.setting.enable()
        self.addCleanup(self.setting.disable);self.addCleanup(self.media.cleanup)
    def operation(self,kind,entity_id=None,payload=None,version=None,site=None,opid=None):
        op={"id":str(opid or uuid.uuid4()),"kind":kind,"entity_id":str(entity_id or uuid.uuid4()),"site_id":(site or self.site).pk,"payload":payload or {},"occurred_at":timezone.now().isoformat()}
        if version is not None:op["base_version"]=version
        return op
    def send(self,op):
        response=self.client.post("/api/sync/",{"operations":[op]},format="json")
        self.assertEqual(response.status_code,200,response.data)
        return response.data["results"][0]
    def visit(self):
        op=self.operation("visit.create",payload={"date":"2026-10-06","crew":"David","title":"Maintenance"})
        self.assertTrue(self.send(op)["ok"])
        return Visit.objects.get(pk=op["entity_id"])
    def task(self):
        op=self.operation("task.create",payload={"title":"Clean analyzer"})
        self.assertTrue(self.send(op)["ok"])
        return Task.objects.get(pk=op["entity_id"])
    def test_site_edit_preserves_legacy_notes_photos_documents(self):
        note=FieldNote.objects.create(site=self.site,note="Original note",date_visited="2026-01-01")
        photo=Photo.objects.create(fieldnote=note,photo="existing.jpg",thumbnail="thumb.jpg")
        doc=Document.objects.create(content_type=ContentType.objects.get_for_model(Site),object_id=self.site.pk,date_received="2026-01-01",summary="Protocol",file="protocol.pdf")
        response=self.client.patch(f"/api/sites/{self.site.pk}/",{"name":"Updated name","base_version":1},format="json")
        self.assertEqual(response.status_code,200,response.data)
        self.assertTrue(FieldNote.objects.filter(pk=note.pk).exists())
        self.assertTrue(Photo.objects.filter(pk=photo.pk).exists())
        self.assertTrue(Document.objects.filter(pk=doc.pk).exists())
    def test_site_delete_protected(self):
        visit=self.visit()
        with self.assertRaises(ProtectedError):self.site.delete()
        self.assertEqual(self.client.delete(f"/api/sites/{self.site.pk}/").status_code,405)
    def test_site_edit_requires_version_and_rejects_stale(self):
        url=f"/api/sites/{self.site.pk}/"
        self.assertEqual(self.client.patch(url,{"name":"A"},format="json").status_code,400)
        self.assertEqual(self.client.patch(url,{"name":"A","base_version":1},format="json").status_code,200)
        self.assertEqual(self.client.patch(url,{"name":"B","base_version":1},format="json").status_code,409)
    def test_django_admin_cannot_bypass_app_site_edits(self):
        self.client.force_login(self.admin)
        r=self.client.post(f"/admin/inventory/site/{self.site.pk}/change/",{"name":"Admin correction","code":self.site.code,"amp":self.site.amp,"location":self.site.location,"description":self.site.description,"date_activated":"2025-04-10","gps_coordinates":"","metadata":"{}","_save":"Save"})
        self.assertEqual(r.status_code,403)
        self.site.refresh_from_db();self.assertEqual(self.site.version,1)
        self.assertNotEqual(self.site.name,"Admin correction")
        self.assertEqual(self.client.patch(f"/api/sites/{self.site.pk}/",{"name":"App correction","base_version":1},format="json").status_code,200)
    def test_operation_retries_do_not_duplicate(self):
        op=self.operation("task.create",payload={"title":"Check power"})
        first=self.send(op);second=self.send(op)
        self.assertEqual(first,second);self.assertEqual(Task.objects.count(),1);self.assertEqual(TaskActivity.objects.count(),1)
    def test_reused_operation_id_different_payload_rejected(self):
        op=self.operation("task.create",payload={"title":"Check power"});self.send(op)
        op["payload"]["title"]="Different"
        self.assertEqual(self.send(op)["status"],409)
    def test_frozen_report_survives_task_reopen(self):
        visit=self.visit();task=self.task()
        self.assertTrue(self.send(self.operation("task.complete",task.pk,{"visit_id":str(visit.pk)},1))["ok"])
        self.assertTrue(self.send(self.operation("visit.close",visit.pk,version=1))["ok"])
        report=VisitReport.objects.get(visit=visit);before=report.text
        self.assertIn("Clean analyzer",before)
        self.assertTrue(self.send(self.operation("task.reopen",task.pk,version=2))["ok"])
        report.refresh_from_db();self.assertEqual(report.text,before)
    def test_reclosed_visit_keeps_previous_revision(self):
        visit=self.visit();self.send(self.operation("visit.close",visit.pk,version=1))
        self.send(self.operation("visit.reopen",visit.pk,version=2))
        self.send(self.operation("observation.create",payload={"visit_id":str(visit.pk),"text":"Correction"}))
        self.send(self.operation("visit.close",visit.pk,version=3))
        self.assertEqual(visit.reports.count(),2)
        self.assertNotIn("Correction",visit.reports.get(revision=1).text)
        self.assertIn("Correction",visit.reports.get(revision=2).text)
    def test_cannot_add_observation_to_closed_visit(self):
        visit=self.visit();self.send(self.operation("visit.close",visit.pk,version=1))
        result=self.send(self.operation("observation.create",payload={"visit_id":str(visit.pk),"text":"Late note"}))
        self.assertEqual(result["status"],409)
    def test_cross_site_task_visit_rejected(self):
        task=self.task();visit=Visit.objects.create(site=self.other,date="2026-10-06",crew="Other")
        self.assertEqual(self.send(self.operation("task.complete",task.pk,{"visit_id":str(visit.pk)},1))["status"],400)
        task.refresh_from_db();self.assertEqual(task.status,"pending")
    def test_stale_task_version_conflicts(self):
        task=self.task();self.send(self.operation("task.edit",task.pk,{"title":"New"},1))
        self.assertEqual(self.send(self.operation("task.edit",task.pk,{"title":"Overwrite"},1))["status"],409)
        task.refresh_from_db();self.assertEqual(task.title,"New")
    def test_batch_stops_before_dependent_operations(self):
        first=self.operation("task.create",payload={"title":""});second=self.operation("task.create",payload={"title":"Should wait"})
        r=self.client.post("/api/sync/",{"operations":[first,second]},format="json")
        self.assertEqual(len(r.data["results"]),1);self.assertEqual(Task.objects.count(),0)
    def test_viewer_cannot_write(self):
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.send(self.operation("task.create",payload={"title":"Not allowed"}))["status"],403)
        self.assertEqual(self.client.get(f"/api/snapshot/?site={self.site.pk}").status_code,200)
    def test_member_can_flag_draft_but_not_review_caveat(self):
        self.client.force_authenticate(self.member)
        op=self.operation("caveat.draft",payload={"title":"Flow issue","description":"Check flow"})
        self.assertTrue(self.send(op)["ok"])
        caveat=DataCaveat.objects.get(pk=op["entity_id"]);self.assertEqual(caveat.status,"draft")
        self.assertEqual(self.client.patch(f"/api/caveats/{caveat.pk}/",{"status":"reviewed","base_version":1},format="json").status_code,403)
    def test_site_scope_enforced(self):
        self.member.team_member.sites.add(self.site)
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.get(f"/api/snapshot/?site={self.other.pk}").status_code,403)
        self.assertEqual(self.send(self.operation("task.create",payload={"title":"No"},site=self.other))["status"],403)
    def test_unassigned_account_has_no_app_access(self):
        user=get_user_model().objects.create_user("stranger",password="test")
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get("/api/bootstrap/").status_code,403)
    def test_archived_site_is_read_only(self):
        self.site.is_archived=True;self.site.save()
        self.assertEqual(self.send(self.operation("task.create",payload={"title":"No"}))["status"],403)
        self.assertEqual(self.client.get(f"/api/snapshot/?site={self.site.pk}").status_code,200)
    def test_sanitizes_imported_html(self):
        r=self.client.patch(f"/api/sites/{self.site.pk}/",{"description":'<p onclick="evil()">Safe</p><script>alert(1)</script><a href="javascript:evil()">Link</a>',"base_version":1},format="json")
        self.assertEqual(r.status_code,200)
        self.assertNotIn("<script",r.data["description"]);self.assertNotIn("onclick",r.data["description"]);self.assertNotIn("javascript:",r.data["description"])
    def test_configurations_immutable(self):
        config=ConfigurationVersion.objects.create(site=self.site,label="Settings",effective_from=timezone.now(),settings={"height":22})
        self.assertEqual(self.client.patch(f"/api/configurations/{config.pk}/",{"settings":{"height":10}},format="json").status_code,405)
    def test_configuration_site_deployment_mismatch_rejected(self):
        deployment=Deployment.objects.create(site=self.other,equipment=self.equipment,installed_at=timezone.now())
        r=self.client.post("/api/configurations/",{"site":self.site.pk,"deployment":str(deployment.pk),"label":"Bad","effective_from":timezone.now().isoformat(),"settings":{}},format="json")
        self.assertEqual(r.status_code,400);self.assertEqual(ConfigurationVersion.objects.count(),0)
    def test_deployment_overlap_rejected_and_current_site_preserved(self):
        now=timezone.now()
        Deployment.objects.create(site=self.site,equipment=self.equipment,installed_at=now-timedelta(days=1))
        r=self.client.post("/api/deployments/",{"site":self.other.pk,"equipment":self.equipment.pk,"installed_at":now.isoformat()},format="json")
        self.assertEqual(r.status_code,400,r.data);self.assertEqual(Deployment.objects.count(),1)
        self.equipment.refresh_from_db();self.assertEqual(self.equipment.site,self.site)
    def test_caveat_period_validation(self):
        now=timezone.now()
        r=self.client.post("/api/caveats/",{"sites":[self.site.pk],"title":"Bad window","affected_from":now.isoformat(),"affected_to":(now-timedelta(days=1)).isoformat()},format="json")
        self.assertEqual(r.status_code,400);self.assertEqual(DataCaveat.objects.count(),0)
    def test_deployment_removal_updates_equipment_location_and_version(self):
        now=timezone.now()
        r=self.client.post("/api/deployments/",{"site":self.site.pk,"equipment":self.equipment.pk,"installed_at":(now-timedelta(days=2)).isoformat()},format="json")
        self.assertEqual(r.status_code,201,r.data)
        self.equipment.refresh_from_db();self.assertEqual(self.equipment.status,"deployed");self.assertEqual(self.equipment.version,2)
        r=self.client.patch(f"/api/deployments/{r.data['id']}/",{"removed_at":(now-timedelta(days=1)).isoformat(),"base_version":1},format="json")
        self.assertEqual(r.status_code,200,r.data)
        self.equipment.refresh_from_db();self.assertIsNone(self.equipment.site);self.assertEqual(self.equipment.status,"available");self.assertEqual(self.equipment.version,3)
    def test_deployment_identity_cannot_be_changed(self):
        d=Deployment.objects.create(site=self.site,equipment=self.equipment,installed_at=timezone.now()-timedelta(days=2))
        r=self.client.patch(f"/api/deployments/{d.pk}/",{"site":self.other.pk,"base_version":1},format="json")
        self.assertEqual(r.status_code,400);d.refresh_from_db();self.assertEqual(d.site,self.site)
    def test_equipment_with_current_deployment_cannot_be_moved_directly(self):
        Deployment.objects.create(site=self.site,equipment=self.equipment,installed_at=timezone.now()-timedelta(days=1))
        r=self.client.patch(f"/api/equipment/{self.equipment.pk}/",{"site":self.other.pk,"base_version":1},format="json")
        self.assertEqual(r.status_code,400);self.equipment.refresh_from_db();self.assertEqual(self.equipment.site,self.site)
    def test_invalid_upload_link_returns_validation_error(self):
        r=self.client.post("/api/attachments/",{"id":str(uuid.uuid4()),"site":self.site.pk,"visit":"bad-uuid","file":SimpleUploadedFile("note.txt",b"text")},format="multipart")
        self.assertEqual(r.status_code,400);self.assertEqual(Attachment.objects.count(),0)
    def test_shared_caveat_ids_support_unique_network_total(self):
        c=DataCaveat.objects.create(title="Shared issue");c.sites.add(self.site,self.other)
        r=self.client.get("/api/overview/")
        self.assertEqual(r.status_code,200)
        self.assertEqual({pk for s in r.data for pk in s["caveat_ids"]},{c.pk})
    def test_malformed_operation_kind_returns_validation_error(self):
        op=self.operation(None)
        self.assertEqual(self.send(op)["status"],400)
    def test_invalid_due_date_does_not_create_task(self):
        op=self.operation("task.create",payload={"title":"Inspect","due_date":"not-a-date"})
        self.assertEqual(self.send(op)["status"],400);self.assertEqual(Task.objects.count(),0)
    def test_invalid_team_username_returns_validation_error(self):
        r=self.client.post("/api/team/",{"username":"invalid username","role":"viewer","password":"valid-long-test-password"},format="json")
        self.assertEqual(r.status_code,400);self.assertFalse(get_user_model().objects.filter(username="invalid username").exists())
    def test_retirement_before_activation_is_rejected(self):
        r=self.client.patch(f"/api/sites/{self.site.pk}/",{"date_retired":"2020-01-01","base_version":1},format="json")
        self.assertEqual(r.status_code,400);self.site.refresh_from_db();self.assertIsNone(self.site.date_retired)
    def test_upload_is_private_and_idempotent(self):
        ident=str(uuid.uuid4())
        for _ in range(2):
            r=self.client.post("/api/attachments/",{"id":ident,"site":self.site.pk,"file":SimpleUploadedFile("settings.ini",b"[settings]\nheight=22"),"caption":"Settings"},format="multipart")
            self.assertIn(r.status_code,[200,201],r.data)
        self.assertEqual(Attachment.objects.count(),1)
        self.client.force_authenticate(None)
        r=self.client.get(f"/attachments/{ident}/");self.assertEqual(r.status_code,302)
        self.assertEqual(self.client.get("/private-media/attachments/anything").status_code,404)
    def test_legacy_attachments_are_linked_to_their_visible_sections(self):
        note=FieldNote.objects.create(site=self.site,note="Original note",date_visited="2026-01-01")
        call_command("backfill_visits",stdout=io.StringIO())
        visit=Visit.objects.get(legacy_note=note)
        photo=Photo.objects.create(fieldnote=note,photo="existing.jpg",thumbnail="thumb.jpg")
        site_doc=Document.objects.create(content_type=ContentType.objects.get_for_model(Site),object_id=self.site.pk,date_received="2026-01-01",summary="Site protocol",file="protocol.pdf")
        note_doc=Document.objects.create(content_type=ContentType.objects.get_for_model(FieldNote),object_id=note.pk,date_received="2026-01-01",summary="Visit document",file="note.pdf")
        equipment_doc=Document.objects.create(content_type=ContentType.objects.get_for_model(Equipment),object_id=self.equipment.pk,date_received="2026-01-01",summary="Instrument manual",file="manual.pdf")
        r=self.client.get(f"/api/snapshot/?site={self.site.pk}")
        files={a["id"]:a for a in r.data["attachments"]}
        self.assertEqual(files[f"photo-{photo.pk}"]["visit"],str(visit.pk))
        self.assertEqual(files[f"document-{note_doc.pk}"]["visit"],str(visit.pk))
        self.assertEqual(files[f"document-{equipment_doc.pk}"]["equipment"],self.equipment.pk)
        self.assertTrue(all(files[f"document-{site_doc.pk}"][field] is None for field in ["visit","equipment","caveat","configuration"]))
    def test_equipment_in_storage_can_receive_a_document(self):
        self.equipment.site=None;self.equipment.save()
        r=self.client.post("/api/attachments/",{"id":str(uuid.uuid4()),"site":self.site.pk,"equipment":self.equipment.pk,"file":SimpleUploadedFile("manual.txt",b"text")},format="multipart")
        self.assertEqual(r.status_code,201,r.data)
    def test_equipment_snapshot_does_not_expose_inaccessible_attachments(self):
        self.equipment.site=None;self.equipment.save()
        private=Attachment.objects.create(site=self.other,equipment=self.equipment,file="private.txt",filename="private.txt",sha256="0"*64)
        self.member.team_member.sites.add(self.site);self.client.force_authenticate(self.member)
        r=self.client.get(f"/api/snapshot/?site={self.site.pk}")
        self.assertNotIn(str(private.pk),[a["id"] for a in r.data["attachments"]])
    def test_upload_wrong_site_visit_rejected(self):
        visit=Visit.objects.create(site=self.other,date="2026-10-06")
        r=self.client.post("/api/attachments/",{"id":str(uuid.uuid4()),"site":self.site.pk,"visit":str(visit.pk),"file":SimpleUploadedFile("note.txt",b"text")},format="multipart")
        self.assertEqual(r.status_code,403);self.assertEqual(Attachment.objects.count(),0)
    def test_fake_image_rejected(self):
        r=self.client.post("/api/attachments/",{"id":str(uuid.uuid4()),"site":self.site.pk,"file":SimpleUploadedFile("photo.jpg",b"not an image")},format="multipart")
        self.assertEqual(r.status_code,400)
    def test_export_blocks_spreadsheet_formula(self):
        Task.objects.create(site=self.site,title="=HYPERLINK(\"bad\")")
        self.client.force_login(self.admin)
        r=self.client.get(f"/export.csv?site={self.site.pk}")
        self.assertIn("'=HYPERLINK",r.content.decode())
    def test_public_reference_bookmark_opens_the_current_report(self):
        self.client.force_authenticate(None)
        self.assertRedirects(self.client.get("/reference/"),"/fieldnotes/",fetch_redirect_response=False)

    def test_legacy_note_backfill_is_idempotent(self):
        note=FieldNote.objects.create(site=self.site,date_visited="2026-01-01",note="Original",summary="Maintenance")
        for _ in range(2):call_command("backfill_visits",stdout=io.StringIO())
        self.assertEqual(Visit.objects.filter(legacy_note=note).count(),1);self.assertEqual(FieldNote.objects.count(),1)
    def test_reference_import_idempotent_and_preserves_edits(self):
        for _ in range(2):call_command("import_fieldnotes",stdout=io.StringIO())
        self.assertEqual(Visit.objects.count(),127);self.assertEqual(DataCaveat.objects.count(),19)
        caveat=DataCaveat.objects.first();caveat.treatment="Reviewed correction";caveat.save()
        call_command("import_fieldnotes",stdout=io.StringIO());caveat.refresh_from_db();self.assertEqual(caveat.treatment,"Reviewed correction")
    def test_firestore_import_idempotent(self):
        folder=Path(self.media.name)
        data={"sites":[{"id":"firebase123","name":"Bog","visits":[{"id":"v1","date":"2026-10-06","crew":"David","status":"closed","startedAt":1791288000000}],"tasks":[{"id":"t1","title":"Inspect power","status":"done","doneVisitId":"v1","createdAt":1791288000000,"doneAt":1791290000000}],"comments":[{"id":"c1","taskId":"t1","visitId":"v1","text":"All good","authorName":"David","createdAt":1791290000000}]}]}
        file=folder/"export.json";file.write_text(json.dumps(data));mapping=folder/"mapping.json";mapping.write_text(json.dumps({"firebase123":"UQAM_3"}))
        for _ in range(2):call_command("import_field_log",file=str(file),site_map=str(mapping),stdout=io.StringIO())
        self.assertEqual(Task.objects.count(),1);self.assertEqual(Visit.objects.count(),1);self.assertEqual(TaskActivity.objects.count(),3)
    def test_health_and_static_endpoints(self):
        self.assertEqual(self.client.get("/health/").status_code,200)
        self.assertEqual(self.client.get("/manifest.webmanifest").status_code,200)
        self.assertEqual(self.client.get("/sw.js")["Service-Worker-Allowed"],"/")

class CSRFTests(TestCase):
    def test_session_api_requires_csrf(self):
        user=get_user_model().objects.create_superuser("admin",password="secure-test-password")
        client=APIClient(enforce_csrf_checks=True);client.force_login(user)
        r=client.post("/api/sites/",{},format="json")
        self.assertEqual(r.status_code,403)
