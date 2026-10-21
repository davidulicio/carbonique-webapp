import json
import re
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings, Client
from rest_framework.test import APIClient

from inventory.models import Site
from .models import DataCaveat, TeamMember, Visit, VisitObservation, Task, TaskActivity, ConfigurationVersion, Attachment


class CaveatReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.researcher = get_user_model().objects.create_user('reviewer', password='review-test-password')
        TeamMember.objects.create(user=cls.researcher, role='researcher')
        cls.site = Site.objects.create(code='TEST_1', name='Test marsh', amp='CA-Tst',
            location='Quebec', description='Marsh description', date_activated='2025-01-01', public_reference=True)
        cls.caveat = DataCaveat.objects.create(title='Imported water table issue',
            description='<p>Review the sensor datum.</p>', created_by=None, public_reference=True)
        cls.caveat.sites.add(cls.site)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.researcher)

    def test_imported_caveat_can_be_resolved_without_inventing_an_author(self):
        response = self.client.patch(f'/api/caveats/{self.caveat.pk}/', {
            'status': 'resolved', 'base_version': self.caveat.version,
            'sites': [self.site.pk], 'equipment': None, 'configurations': [],
            'affected_from': None, 'affected_to': None, 'variables': '',
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.caveat.refresh_from_db()
        self.assertEqual(self.caveat.status, 'resolved')
        self.assertIsNone(self.caveat.created_by)
        self.assertEqual(self.caveat.version, 2)

    def test_invalid_period_rolls_back_review_and_version(self):
        response = self.client.patch(f'/api/caveats/{self.caveat.pk}/', {
            'status': 'resolved', 'base_version': 1,
            'affected_from': '2026-01-02T00:00:00Z', 'affected_to': '2026-01-01T00:00:00Z',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.caveat.refresh_from_db()
        self.assertEqual(self.caveat.status, 'draft')
        self.assertEqual(self.caveat.version, 1)

    def test_review_resolve_reopen_and_return_to_draft_update_the_public_page(self):
        public=Client()
        for index,status in enumerate(['reviewed','resolved','reviewed','draft'],1):
            response=self.client.patch(f'/api/caveats/{self.caveat.pk}/',{'status':status,'base_version':index},format='json')
            self.assertEqual(response.status_code,200,response.data)
            self.caveat.refresh_from_db()
            html=public.get('/fieldnotes/content/').content.decode()
            self.assertIn(f'class="card record caveat {status}"',html)
            self.assertEqual(self.caveat.resolved_at is not None,status=='resolved')
            self.assertEqual(self.caveat.reviewed_at is not None,status!='draft')

    def test_stale_review_does_not_overwrite_or_republish(self):
        self.client.patch(f'/api/caveats/{self.caveat.pk}/',{'status':'resolved','base_version':1},format='json')
        response=self.client.patch(f'/api/caveats/{self.caveat.pk}/',{'status':'draft','base_version':1},format='json')
        self.assertEqual(response.status_code,409)
        self.caveat.refresh_from_db();self.assertEqual(self.caveat.status,'resolved')

    def test_site_and_caveat_edits_are_live_without_rebuilding_a_file(self):
        self.caveat.title='Corrected public caveat';self.caveat.save()
        self.site.name='Updated public marsh';self.site.description='<p>Current site description.</p>';self.site.save()
        html=Client().get('/fieldnotes/content/').content.decode()
        self.assertIn('Corrected public caveat',html);self.assertIn('Updated public marsh',html)
        self.assertIn('Current site description.',html)

    def test_shared_caveat_includes_configuration_choices_from_other_sites(self):
        other=Site.objects.create(code='OTHER',name='Other site',amp='CA-Alt',location='Quebec',description='Other',date_activated='2025-01-01')
        config=ConfigurationVersion.objects.create(site=other,label='Other site configuration',effective_from='2026-01-01T00:00:00Z')
        self.caveat.sites.add(other);self.caveat.configurations.add(config)
        response=self.client.get(f'/api/caveats/{self.caveat.pk}/')
        self.assertEqual(response.data['configuration_details'][0]['id'],str(config.pk))
        response=self.client.patch(f'/api/caveats/{self.caveat.pk}/',{'status':'resolved','base_version':1,'configurations':[str(config.pk)]},format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(self.caveat.configurations.count(),1)

    def test_viewer_and_anonymous_cannot_review(self):
        viewer=get_user_model().objects.create_user('read-only')
        TeamMember.objects.create(user=viewer,role='viewer')
        for user in [viewer,None]:
            self.client.force_authenticate(user)
            response=self.client.patch(f'/api/caveats/{self.caveat.pk}/',{'status':'resolved','base_version':1},format='json')
            self.assertEqual(response.status_code,403)


class PublicReportTests(TestCase):
    def setUp(self):
        self.site=Site.objects.create(code='LIVE_1',name='Live marsh',amp='CA-Liv',location='Quebec',description='Site facts',date_activated='2025-01-01')
        self.visit=Visit.objects.create(site=self.site,title='Public field visit',crew='Field team',narrative='<p>Visit narrative</p>',date='2026-01-01')
        self.client=Client()

    def test_all_visits_and_current_caveat_states_are_visible_without_publication_flags(self):
        VisitObservation.objects.create(visit=self.visit,text='Water level observation')
        task=Task.objects.create(site=self.site,title='Private future task')
        TaskActivity.objects.create(task=task,visit=self.visit,action='completed',task_title='Sensor cleaned')
        for status in ['draft','reviewed','resolved']:
            caveat=DataCaveat.objects.create(title=f'{status} caveat',status=status,public_reference=False)
            caveat.sites.add(self.site)
        html=self.client.get('/fieldnotes/content/').content.decode()
        for text in ['Public field visit','Visit narrative','Water level observation','Sensor cleaned','draft caveat','reviewed caveat','resolved caveat','Draft · awaiting review']:
            self.assertIn(text,html)
        self.assertNotIn('Private future task',html)

    def test_empty_database_and_site_without_visits_render(self):
        Visit.objects.all().delete()
        self.assertContains(self.client.get('/fieldnotes/content/'),'No field visits recorded yet.')
        self.site.delete()
        self.assertContains(self.client.get('/fieldnotes/content/'),'No sites recorded yet.')

    def test_shared_caveat_is_rendered_once_and_archived_sites_keep_history(self):
        other=Site.objects.create(code='OLD',name='Archived site',amp='CA-Old',location='Quebec',description='Historic facts',date_activated='2024-01-01',is_archived=True)
        caveat=DataCaveat.objects.create(title='Shared issue');caveat.sites.add(self.site,other)
        html=self.client.get('/fieldnotes/content/').content.decode()
        self.assertEqual(html.count(f'id="caveat-{caveat.pk}"'),1)
        self.assertIn('Archived site',html)

    def test_public_views_are_read_only_and_disable_together(self):
        for route in ['/fieldnotes/','/fieldnotes/content/','/fieldnotes/download/','/reference/']:
            self.assertEqual(self.client.post(route,{'title':'changed'}).status_code,405)
            with override_settings(PUBLIC_FIELDNOTES_ENABLED=False):
                self.assertEqual(self.client.get(route).status_code,404)

    def test_export_is_self_contained_and_sandbox_does_not_get_app_origin(self):
        response=self.client.get('/fieldnotes/content/')
        self.assertEqual(response['Cache-Control'],'no-store')
        self.assertIn('sandbox allow-scripts',response['Content-Security-Policy'])
        self.assertIn('allow-popups-to-escape-sandbox',response['Content-Security-Policy'])
        self.assertIn("form-action 'none'",response['Content-Security-Policy'])
        self.assertNotIn('allow-same-origin',response['Content-Security-Policy'])
        download=self.client.get('/fieldnotes/download/')
        self.assertIn('attachment;',download['Content-Disposition'])
        self.assertIn(b'data:font/ttf;base64,',download.content)
        self.assertNotIn(b'<link rel="stylesheet"',download.content)
        self.assertNotIn(b'<script src=',download.content)

    def test_plain_fields_are_escaped_and_rich_text_is_sanitized(self):
        self.visit.title='<img src=x onerror=alert(1)>'
        self.visit.narrative='<p onclick="alert(1)">Safe</p><script>alert(2)</script>'
        self.visit.save()
        caveat=DataCaveat.objects.create(title='Bad link',evidence={'links':[{'u':'javascript:alert(3)','t':'bad'}]})
        caveat.sites.add(self.site)
        html=self.client.get('/fieldnotes/content/').content.decode()
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;',html)
        self.assertNotIn('<img src=x',html);self.assertNotIn('onclick=',html)
        self.assertNotIn('<script>alert(2)</script>',html);self.assertNotIn('javascript:alert(3)',html)

    def test_logger_periods_render_in_fixed_est(self):
        caveat=DataCaveat.objects.create(title='Timed issue',affected_from='2026-07-01T05:00:00Z')
        caveat.sites.add(self.site)
        self.assertContains(self.client.get('/fieldnotes/content/'),'2026-07-01 00:00')

    def test_private_accounts_protocols_and_arbitrary_metadata_are_not_serialized(self):
        self.site.metadata={'private_password':'not-for-the-public','reference':{'sections':[]}}
        self.site.save()
        html=self.client.get('/fieldnotes/content/').content.decode()
        for text in ['not-for-the-public','password_hash','/api/sync/','/api/team/','/api/protocols/']:
            self.assertNotIn(text,html)

    def test_sensor_diagram_preserves_tall_heights_and_separates_labels(self):
        from .public_report import geometry
        diagram=geometry({'deployments':[],'sections':[{'groups':[{'heading':'Sonic anemometer','items':[{'key':'Sonic height','value':'24 m'}]},
            {'heading':'Temperature and humidity','items':[{'key':'TA_1_1_1 height','value':'22 m'},{'key':'TA_1_2_1 height','value':'21.9 m'}]}]}]})
        self.assertEqual([point['height'] for point in diagram['points']],[24,22,21.9])
        labels=[point['label_y'] for point in diagram['points']]
        self.assertTrue(all(right-left>=18 for left,right in zip(labels,labels[1:])))

    def test_public_ini_link_uses_github_without_publishing_legacy_copies(self):
        from django.db import transaction
        from .processing_files import store_version
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            with transaction.atomic():
                store_version('Shared_include.ini', b'legacy_private_setting=1;')
            for route in ['/fieldnotes/content/', '/fieldnotes/download/']:
                response = self.client.get(route)
                self.assertContains(response, 'https://github.com/CARBONI-QUE/UQAM_Software_and_Settings/tree/main/Database/Calculation_Procedures/TraceAnalysis_ini')
                self.assertNotContains(response, 'legacy_private_setting=1;')
                self.assertNotContains(response, 'Download INI')
