import csv
import io
import json
import tempfile
import zipfile
from unittest.mock import patch
from datetime import date, timedelta
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from inventory.models import Site
from hub.models import TeamMember, SiteCondition, BADMProfile, BADMRecord, Protocol, SiteMedia, Visit, DataCaveat, ConfigurationVersion, Attachment, AuditEvent
from hub import badm

STATION = "ASSICOSBADM_SiteDescr_20210429"


class ResourceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.site = Site.objects.create(code="UQAM_3", name="Test bog", amp="CA-CQ3", location="Quebec", description="Bog", date_activated="2025-04-10")
        cls.other = Site.objects.create(code="UQAM_2", name="Other", amp="CA-CQ2", location="Quebec", description="Bog", date_activated="2025-04-10")
        cls.users = {}
        for role in ["viewer", "member", "researcher", "manager", "admin"]:
            user = get_user_model().objects.create_user(role)
            TeamMember.objects.create(user=user, role=role)
            cls.users[role] = user

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.users["manager"])
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.temp.name)
        self.override.enable()
        self.addCleanup(self.override.disable)

    def record(self, **overrides):
        return BADMRecord.objects.create(site=self.site, template=STATION, group="GRP_LOCATION", values={"LOCATION_LAT":"46.5280", "LOCATION_LONG":"-72.6462"}, **overrides)

    def test_condition_is_unknown_until_assessed_and_does_not_reopen_on_expiry(self):
        state = self.client.get(f"/api/snapshot/?site={self.site.pk}").data["resources"]
        self.assertEqual(state["condition"]["status"], "unknown")
        url = f"/api/sites/{self.site.pk}/condition/"
        response = self.client.patch(url, {"status":"closed", "statement":"Flooded. Contact the manager.", "valid_until":str(date.today()-timedelta(days=1)), "base_version":0}, format="json")
        self.assertEqual(response.status_code,200,response.data)
        self.assertTrue(response.data["review_overdue"])
        self.assertEqual(response.data["status"],"closed")
        self.assertEqual(self.client.patch(url,{"status":"open","base_version":0},format="json").status_code,409)
        self.assertTrue(AuditEvent.objects.filter(action="site.condition_updated").exists())

    def test_only_admin_and_manager_can_change_resources(self):
        for role in ["viewer","member","researcher"]:
            self.client.force_authenticate(self.users[role])
            for url, data in [
                (f"/api/sites/{self.site.pk}/condition/",{"status":"open","base_version":0}),
                (f"/api/sites/{self.site.pk}/badm/profile/",{"station_id":"CA-CQ3","base_version":0}),
                (f"/api/sites/{self.site.pk}/badm/records/",{"template":STATION,"group":"GRP_LOCATION","values":{}}),
                (f"/api/sites/{self.site.pk}/media/",{"title":"Video"}),
                ("/api/protocols/",{"title":"Protocol"}),
            ]:
                method=self.client.patch if url.endswith(("condition/","profile/")) else self.client.post
                self.assertEqual(method(url,data,format="json").status_code,403,(role,url))

    def test_manager_site_scope_is_enforced_for_read_and_write(self):
        self.users["manager"].team_member.sites.add(self.site)
        self.assertEqual(self.client.patch(f"/api/sites/{self.other.pk}/condition/",{"status":"open","base_version":0},format="json").status_code,403)
        self.assertEqual(self.client.get(f"/sites/{self.other.pk}/badm.zip").status_code,403)
        media=SiteMedia.objects.create(site=self.other,title="Other tower",file="private.mp4",filename="tower.mp4",content_type="video/mp4",size=12,sha256="0"*64)
        self.assertEqual(self.client.get(f"/site-media/{media.pk}/file/").status_code,403)

    def test_archived_sites_reject_new_context(self):
        self.site.is_archived=True;self.site.save()
        self.assertEqual(self.client.patch(f"/api/sites/{self.site.pk}/condition/",{"status":"open","base_version":0},format="json").status_code,403)

    def test_profile_validates_code_and_applicable_groups(self):
        url=f"/api/sites/{self.site.pk}/badm/profile/"
        self.assertEqual(self.client.patch(url,{"station_id":"UQAM_3","base_version":0},format="json").status_code,400)
        self.assertEqual(self.client.patch(url,{"applicable_groups":["GRP_FAKE"],"base_version":0},format="json").status_code,400)
        response=self.client.patch(url,{"station_id":"CA-CQ3","applicable_groups":["GRP_SOIL_TEX"],"base_version":0},format="json")
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(self.client.patch(url,{"notes":"stale","base_version":0},format="json").status_code,409)

    def test_invalid_draft_values_are_saved_but_never_pass_checks(self):
        response=self.client.post(f"/api/sites/{self.site.pk}/badm/records/",{"template":STATION,"group":"GRP_LOCATION","values":{"LOCATION_LAT":"1000","LOCATION_LONG":"west"}},format="json")
        self.assertEqual(response.status_code,201,response.data)
        record=BADMRecord.objects.get(pk=response.data["id"])
        errors,_=badm.record_issues(record)
        self.assertEqual(len(errors),2)
        state=self.client.get(f"/api/snapshot/?site={self.site.pk}").data["resources"]["badm"]
        self.assertFalse(state["validation"]["ok"])
        self.assertIn("GRP_TEAM",state["validation"]["missing_groups"])

    def test_unknown_variables_and_wrong_station_templates_are_rejected(self):
        url=f"/api/sites/{self.site.pk}/badm/records/"
        for data in [
            {"template":STATION,"group":"GRP_LOCATION","values":{"FAKE":"value"}},
            {"template":"ICOSBADM_EC_20220805","group":"GRP_EC","values":{}},
        ]:
            self.assertEqual(self.client.post(url,data,format="json").status_code,400)

    def test_repeated_group_entries_are_independent_and_conflicts_do_not_overwrite(self):
        first=self.record()
        second=self.record()
        url=f"/api/sites/{self.site.pk}/badm/records/{first.pk}/"
        self.assertEqual(self.client.patch(url,{"notes":"Reviewed coordinates","base_version":1},format="json").status_code,200)
        self.assertEqual(self.client.patch(url,{"notes":"stale","base_version":1},format="json").status_code,409)
        first.refresh_from_db();second.refresh_from_db()
        self.assertEqual(first.notes,"Reviewed coordinates");self.assertEqual(second.notes,"")

    def test_badm_alternatives_dates_vocabulary_and_review_are_checked(self):
        record=BADMRecord(template="ASSICOSBADM_InstManag_20240119",group="GRP_INSTMAN",values={"INSTMAN_MODEL":"invalid","INSTMAN_SN":"123","INSTMAN_TYPE":"Installation","INSTMAN_DATE_START":"202602300000","INSTMAN_DATE_END":"202601010000"})
        errors,review=badm.record_issues(record)
        self.assertTrue(any("LIST" in e for e in errors))
        self.assertTrue(any("valid date" in e for e in errors))
        self.assertTrue(any("end date" in e for e in errors))
        self.assertTrue(any("Installation" in e for e in errors))
        self.assertTrue(review)
        record.conditions_reviewed=True
        self.assertFalse(badm.record_issues(record)[1])
        self.assertTrue(badm.record_issues(record)[0])

    def test_all_team_roles_can_export_complete_badm_with_negative_numbers_and_archived_records(self):
        active=self.record();old=self.record(is_archived=True)
        BADMProfile.objects.create(site=self.site,station_id="CA-CQ3")
        for role in self.users:
            self.client.force_authenticate(self.users[role])
            response=self.client.get(f"/sites/{self.site.pk}/badm.zip")
            self.assertEqual(response.status_code,200)
            archive=zipfile.ZipFile(io.BytesIO(response.content))
            data=json.loads(archive.read("all-records.json"))
            self.assertEqual(len(data["records"]),2)
            csv_path=next(name for name in archive.namelist() if name.endswith(".csv"))
            rows=list(csv.DictReader(io.StringIO(archive.read(csv_path).decode())))
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]["LOCATION_LONG"],"-72.6462")
            self.assertNotIn("SITE_ID",rows[0])
            self.assertRegex(Path(csv_path).name,r"CA-CQ3_\d{8}_BADM_\d{6}.csv")

    def test_anonymous_downloads_and_unassigned_accounts_are_denied(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f"/sites/{self.site.pk}/badm.zip").status_code,403)
        self.assertEqual(self.client.get("/api/protocols/").status_code,403)
        self.assertEqual(self.client.get("/inventory-source.zip").status_code,403)
        user=get_user_model().objects.create_user("no-role")
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get("/api/protocols/").status_code,403)

    def test_protocol_upload_pdf_preview_download_and_archive(self):
        response=self.client.post("/api/protocols/",{"title":"Calibration","file":SimpleUploadedFile("calibration.pdf",b"%PDF-1.4\nexample")},format="multipart")
        self.assertEqual(response.status_code,201,response.data)
        ident=response.data["id"]
        self.client.force_authenticate(self.users["viewer"])
        response=self.client.get(f"/protocols/{ident}/file/")
        self.assertEqual(response.status_code,200)
        self.assertIn("inline",response["Content-Disposition"])
        self.assertEqual(response["X-Frame-Options"],"SAMEORIGIN")
        self.assertIn(b"%PDF",b"".join(response.streaming_content))
        response=self.client.get(f"/protocols/{ident}/file/?download=1")
        self.assertIn("attachment",response["Content-Disposition"])
        response.close()
        self.client.force_authenticate(self.users["manager"])
        self.assertEqual(self.client.patch(f"/api/protocols/{ident}/",{"is_archived":True,"base_version":1},format="json").status_code,200)
        self.assertEqual(len(self.client.get("/api/protocols/").data),0)

    def test_invalid_pdf_and_oversized_media_rejected(self):
        response=self.client.post("/api/protocols/",{"title":"Fake","file":SimpleUploadedFile("fake.pdf",b"<script>bad</script>")},format="multipart")
        self.assertEqual(response.status_code,400)
        with override_settings(MAX_SITE_MEDIA_BYTES=5):
            response=self.client.post(f"/api/sites/{self.site.pk}/media/",{"title":"Too large","file":SimpleUploadedFile("large.webm",b"\x1aE\xdf\xa3"+b"a"*10)},format="multipart")
            self.assertEqual(response.status_code,400)

    def test_tower_mp4_can_be_viewed_by_viewers_and_archived_by_manager(self):
        response=self.client.post(f"/api/sites/{self.site.pk}/media/",{"title":"Tower tour","caption":"Boardwalk and sensors","file":SimpleUploadedFile("tower.mp4",b"\x00\x00\x00\x18ftypmp42"+b"x"*20)},format="multipart")
        self.assertEqual(response.status_code,201,response.data)
        self.assertEqual(response.data["content_type"],"video/mp4")
        self.client.force_authenticate(self.users["viewer"])
        url=response.data["url"]
        response=self.client.get(url)
        self.assertEqual(response.status_code,200);response.close()
        response=self.client.get(url,HTTP_RANGE="bytes=4-7")
        self.assertEqual(response.status_code,206)
        self.assertEqual(response["Content-Range"],"bytes 4-7/32")
        self.assertEqual(b"".join(response.streaming_content),b"ftyp")
        self.assertEqual(self.client.get(url,HTTP_RANGE="bytes=1000-2000").status_code,416)
        self.client.force_authenticate(self.users["manager"])
        obj=SiteMedia.objects.get()
        self.assertEqual(self.client.patch(f"/api/sites/{self.site.pk}/media/{obj.pk}/",{"is_archived":True,"base_version":1},format="json").status_code,200)
        self.assertEqual(self.client.get(f"/api/snapshot/?site={self.site.pk}").data["resources"]["media"],[])

    def test_import_resources_is_complete_idempotent_and_preserves_edits(self):
        call_command("import_resources",stdout=io.StringIO())
        self.assertEqual(Protocol.objects.count(),7)
        self.assertEqual(Visit.objects.count(),127)
        self.assertEqual(DataCaveat.objects.count(),19)
        self.assertEqual(ConfigurationVersion.objects.filter(settings__source="EcoFlux inventory export 2026-10-16").count(),8)
        self.assertEqual(Attachment.objects.filter(filename__endswith=".ini").count(),8)
        before=(Site.objects.count(),Visit.objects.count(),DataCaveat.objects.count(),Attachment.objects.count(),ConfigurationVersion.objects.count())
        protocol=Protocol.objects.exclude(bundled_file="").first();protocol.title="Team revision";protocol.save()
        call_command("import_resources",stdout=io.StringIO())
        self.assertEqual(before,(Site.objects.count(),Visit.objects.count(),DataCaveat.objects.count(),Attachment.objects.count(),ConfigurationVersion.objects.count()))
        protocol.refresh_from_db();self.assertEqual(protocol.title,"Team revision")
        self.client.force_authenticate(self.users["viewer"])
        response=self.client.get(f"/protocols/{protocol.pk}/file/")
        self.assertEqual(response.status_code,200);self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF-"))

    def test_removed_data_download_protocol_is_not_reimported(self):
        for _ in range(2):
            call_command("import_resources",stdout=io.StringIO())
        self.assertEqual(Protocol.objects.count(),7)
        self.assertFalse(Protocol.objects.filter(filename="Data_download.pdf").exists())

    def test_inventory_source_download_contains_every_supplied_file(self):
        response=self.client.get("/inventory-source.zip")
        archive=zipfile.ZipFile(io.BytesIO(response.content))
        root=settings.BASE_DIR/"seed/ecoflux_inventory_export"
        files=[p for p in root.rglob("*") if p.is_file()]
        self.assertEqual(set(archive.namelist()),{p.relative_to(root).as_posix() for p in files})
        for path in files:
            self.assertEqual(archive.read(path.relative_to(root).as_posix()),path.read_bytes())
