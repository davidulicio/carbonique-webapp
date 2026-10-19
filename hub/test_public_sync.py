"""Changes saved through team APIs must reach the public projection and timeline."""
import uuid
from html.parser import HTMLParser
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from inventory.models import Site
from .models import DataCaveat, Visit


class MarkerParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.markers = []
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'marker' in attrs.get('class', '').split():
            self.markers.append(attrs)


class PublicSynchronizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser('public-sync-review', password='test-sync-password')
        cls.site = Site.objects.create(code='SYNC_1', name='Sync marsh', amp='CA-Sy1', location='Quebec', description='Site description', date_activated='2025-01-01')
        cls.other = Site.objects.create(code='SYNC_2', name='Other marsh', amp='CA-Sy2', location='Quebec', description='Other description', date_activated='2025-01-01')
    def setUp(self):
        self.team = APIClient()
        self.team.force_authenticate(self.admin)
        self.public = Client()
    def markers(self, response=None):
        response = response or self.public.get('/fieldnotes/content/')
        self.assertEqual(response.status_code, 200)
        return MarkerParser(response.content.decode()).markers
    def new_caveat(self, **overrides):
        values = {'title': 'New sensor caveat', 'description': 'Review this measurement.', 'sites': [self.site.pk], 'period_label': 'Exact affected period is unknown.'}
        values.update(overrides)
        response = self.team.post('/api/caveats/', values, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data
    def edit_caveat(self, caveat, **values):
        response = self.team.patch('/api/caveats/'+caveat['id']+'/', {'base_version': caveat['version'], **values}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        return response.data
    def operation(self, kind, entity, payload, version=None):
        operation = {'id': str(uuid.uuid4()), 'entity_id': str(entity), 'kind': kind, 'site_id': self.site.pk, 'payload': payload, 'occurred_at': timezone.now().isoformat()}
        if version is not None:
            operation['base_version'] = version
        response = self.team.post('/api/sync/', {'operations': [operation]}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['results'][0]['ok'], response.data)

    def test_added_caveat_and_status_changes_update_timeline_and_export(self):
        caveat = self.new_caveat()
        marker, = self.markers()
        self.assertEqual(marker['href'], '#caveat-'+caveat['id'])
        self.assertEqual(marker['data-date'], '')
        self.assertEqual(marker['data-status'], 'draft')
        caveat = self.edit_caveat(caveat, status='resolved', title='Datum correction complete')
        marker, = self.markers()
        self.assertEqual(marker['data-status'], 'resolved')
        self.assertEqual(marker['data-title'], 'Datum correction complete')
        marker, = self.markers(self.public.get('/fieldnotes/download/'))
        self.assertEqual(marker['data-status'], 'resolved')
        self.edit_caveat(caveat, status='reviewed')
        marker, = self.markers()
        self.assertEqual(marker['data-status'], 'reviewed')

    def test_shared_caveat_uses_fixed_est_and_links_to_one_public_entry(self):
        caveat = self.new_caveat(sites=[self.site.pk, self.other.pk], affected_from='2026-07-01T02:00:00Z')
        response = self.public.get('/fieldnotes/content/')
        markers = self.markers(response)
        self.assertEqual(len(markers), 2)
        self.assertEqual({m['data-site'] for m in markers}, {'SYNC_1', 'SYNC_2'})
        self.assertEqual({m['data-date'] for m in markers}, {'2026-06-30'})
        self.assertTrue(all('Affected start (fixed EST)' in m['data-detail'] for m in markers))
        self.assertEqual(response.content.decode().count('id="caveat-'+caveat['id']+'"'), 1)

    def test_only_end_date_is_labeled_and_clearing_it_leaves_an_undated_marker(self):
        caveat = self.new_caveat(affected_to='2026-04-02T02:00:00Z')
        marker, = self.markers()
        self.assertEqual(marker['data-date'], '2026-04-01')
        self.assertIn('Affected end (fixed EST)', marker['data-detail'])
        self.edit_caveat(caveat, affected_to=None)
        marker, = self.markers()
        self.assertEqual(marker['data-date'], '')
        self.assertIn('Affected dates not recorded', marker['data-detail'])
        self.assertNotIn(timezone.now().strftime('%Y-%m-%d'), marker['data-detail'])

    def test_changing_caveat_dates_and_sites_replaces_the_current_markers(self):
        caveat = self.new_caveat(affected_from='2026-03-01T05:00:00Z')
        self.edit_caveat(caveat, affected_from='2026-06-01T05:00:00Z', sites=[self.other.pk])
        marker, = self.markers()
        self.assertEqual(marker['data-site'], 'SYNC_2')
        self.assertEqual(marker['data-date'], '2026-06-01')
        self.assertEqual(DataCaveat.objects.count(), 1)

    def test_synced_visits_observations_and_draft_issues_reach_the_public_report(self):
        visit = uuid.uuid4()
        self.operation('visit.create', visit, {'date': '2026-06-01', 'crew': 'Field crew', 'title': 'Initial visit'})
        self.operation('visit.edit', visit, {'date': '2026-06-02', 'title': 'Updated visit', 'classification': 'fault'}, version=1)
        self.operation('observation.create', uuid.uuid4(), {'visit_id': str(visit), 'text': 'New water level observation'})
        self.operation('caveat.draft', uuid.uuid4(), {'visit_id': str(visit), 'title': 'Issue from field visit'})
        response = self.public.get('/fieldnotes/content/')
        self.assertContains(response, 'New water level observation')
        markers = self.markers(response)
        self.assertEqual(len(markers), 2)
        marker = next(m for m in markers if m['data-record-kind'] == 'visit')
        self.assertEqual(marker['data-date'], '2026-06-02')
        self.assertEqual(marker['data-title'], 'Updated visit')
        self.assertEqual(marker['data-kind'], 'fault')
        caveat = next(m for m in markers if m['data-record-kind'] == 'caveat')
        self.assertEqual(caveat['data-date'], '')  # A report date is not a measurement start date.

    def test_site_information_reference_and_conditions_are_current_and_read_only(self):
        response = self.team.patch(f'/api/sites/{self.site.pk}/', {'base_version': 1, 'name': 'Updated marsh', 'description': 'Updated public description', 'metadata': {'reference': {'sections': [{'h': 'Site info', 'items': [{'k': 'Site name', 'v': 'Obsolete source name'}]}]}}}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        response = self.team.patch(f'/api/sites/{self.site.pk}/condition/', {'base_version': 0, 'status': 'closed', 'statement': 'Flooded; no access until reviewed.', 'valid_until': '2020-01-01'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        public = self.public.get('/fieldnotes/content/')
        for text in ['Updated marsh', 'Updated public description', 'Flooded; no access until reviewed.', 'Inaccessible', '2020-01-01', 'Review overdue']:
            self.assertContains(public, text)
        self.assertNotContains(public, 'Obsolete source name')
        self.assertNotContains(public, 'public-sync-review')
        self.assertEqual(self.public.post(f'/api/sites/{self.site.pk}/condition/', {'status': 'open'}).status_code, 403)
        response = self.team.patch(f'/api/sites/{self.site.pk}/condition/', {'base_version': 1, 'status': 'open', 'statement': 'Access inspected and restored.', 'valid_until': None}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertContains(self.public.get('/fieldnotes/content/'), 'Access inspected and restored.')
        self.assertNotContains(self.public.get('/fieldnotes/content/'), 'Flooded; no access')

    def test_live_refresh_controls_do_not_promise_to_update_exported_snapshots(self):
        self.assertContains(self.public.get('/fieldnotes/'), 'Refresh public site')
        self.assertContains(self.public.get('/fieldnotes/content/'), 'id="refresh-public"')
        exported = self.public.get('/fieldnotes/download/')
        self.assertNotContains(exported, 'id="refresh-public"')
        self.assertContains(exported, 'Saved snapshot; download a new copy')
