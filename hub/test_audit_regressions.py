"""Regression coverage for the 29 October application audit."""
import uuid
from datetime import timedelta
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from inventory.models import Site, Equipment
from .models import TeamMember, Visit, Task, TaskActivity, VisitReport, ConfigurationVersion, DataCaveat, Deployment, Attachment, OperationReceipt, ChecklistTemplate


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class AuditRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a=Site.objects.create(code='AUDIT_A',name='Allowed',date_activated='2025-01-01')
        cls.b=Site.objects.create(code='AUDIT_B',name='Restricted',date_activated='2025-01-01')
        User=get_user_model()
        cls.limited=User.objects.create_user('limited-admin',password='Local-review-password-2026')
        cls.member=User.objects.create_user('limited-member',password='Local-review-password-2026')
        cls.network=User.objects.create_user('network-admin',password='Local-review-password-2026')
        for user,role in [(cls.limited,'admin'),(cls.member,'member'),(cls.network,'admin')]:TeamMember.objects.create(user=user,role=role)
        cls.limited.team_member.sites.add(cls.a);cls.member.team_member.sites.add(cls.a)
    def setUp(self):
        self.client=APIClient();self.client.force_authenticate(self.limited)
    def operation(self,kind,entity=None,payload=None,version=None,at=None):
        result=dict(id=str(uuid.uuid4()),kind=kind,entity_id=str(entity or uuid.uuid4()),site_id=self.a.pk,payload=payload or {},occurred_at=(at or timezone.now()).isoformat())
        if version is not None:result['base_version']=version
        return result
    def send(self,operation):
        response=self.client.post('/api/sync/',{'operations':[operation]},format='json')
        self.assertEqual(response.status_code,200,response.data)
        return response.data['results'][0]
    def test_restricted_admin_cannot_list_or_create_network_accounts(self):
        self.assertEqual(self.client.get('/api/team/').status_code,403)
        for sites in [[],[self.a.pk],[self.b.pk]]:
            with self.subTest(sites=sites):
                response=self.client.post('/api/team/',dict(username='escalated',password='Local-new-password-2026',role='admin',sites=sites),format='json')
                self.assertEqual(response.status_code,403)
        self.assertFalse(get_user_model().objects.filter(username='escalated').exists())
        self.assertFalse(self.client.get('/api/bootstrap/').data['me']['can_manage_team'])
    def test_restricted_admin_cannot_reset_disable_or_reassign_broader_accounts(self):
        for change in [{'password':'Local-replacement-2026'},{'is_active':False},{'role':'viewer','sites':[self.a.pk]}]:
            response=self.client.patch('/api/team/',dict(id=self.network.pk,**change),format='json')
            self.assertEqual(response.status_code,403)
        self.network.refresh_from_db();self.assertTrue(self.network.is_active)
        self.assertTrue(self.network.check_password('Local-review-password-2026'))
        self.assertEqual(self.network.team_member.role,'admin')
    def test_network_admin_can_still_manage_accounts(self):
        self.client.force_authenticate(self.network)
        response=self.client.post('/api/team/',dict(username='new-member',password='Local-new-password-2026',role='member',sites=[self.a.pk]),format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.assertTrue(self.client.get('/api/bootstrap/').data['me']['can_manage_team'])
    def test_scoped_admin_cannot_create_network_sites_or_checklists(self):
        self.assertEqual(self.client.post('/api/sites/',{'code':'BLOCKED','name':'Blocked','amp':'CA-XX1','location':'test','description':'test','date_activated':'2025-01-01'},format='json').status_code,403)
        self.assertEqual(self.client.post('/api/checklists/',{'name':'Shared','tasks':[]},format='json').status_code,403)
    def test_receipt_replay_requires_current_access_but_allows_archived_retry(self):
        self.client.force_authenticate(self.member)
        task=Task.objects.create(site=self.a,title='Task',details='Private detail')
        operation=self.operation('task.comment',task.pk,{'text':'Checked'})
        first=self.send(operation);self.assertTrue(first['ok'])
        self.a.is_archived=True;self.a.save()
        self.assertEqual(self.send(operation),first)
        self.member.team_member.sites.set([self.b])
        replay=self.send(operation);self.assertFalse(replay['ok']);self.assertEqual(replay['status'],403)
        self.assertNotIn('record',replay);self.assertEqual(TaskActivity.objects.count(),1)
    def test_shared_caveat_filters_configuration_ids_and_details_in_both_routes(self):
        visible=ConfigurationVersion.objects.create(site=self.a,label='Visible',effective_from=timezone.now())
        hidden=ConfigurationVersion.objects.create(site=self.b,label='Private configuration',effective_from=timezone.now())
        caveat=DataCaveat.objects.create(title='Shared');caveat.sites.add(self.a,self.b);caveat.configurations.add(visible,hidden)
        self.client.force_authenticate(self.member)
        direct=self.client.get(f'/api/caveats/{caveat.pk}/').data
        snapshot=self.client.get(f'/api/snapshot/?site={self.a.pk}').data['caveats'][0]
        for value in [direct,snapshot]:
            self.assertEqual(value['configurations'],[str(visible.pk)])
            self.assertEqual([row['id'] for row in value['configuration_details']],[str(visible.pk)])
            self.assertNotIn('Private configuration',str(value))
    def test_nonobject_json_is_a_validation_error(self):
        self.client.raise_request_exception=False
        for value in [[],None,1,'text']:
            with self.subTest(value=value):self.assertEqual(self.client.post('/api/sync/',value,content_type='application/json').status_code,400)
    def test_malformed_checklists_are_validation_errors(self):
        self.client.force_authenticate(self.network);self.client.raise_request_exception=False
        for task in [{'title':12},{'title':[]},{'title':{}},{'title':'  '},{'title':'ok','details':12},{'title':'ok','priority':{}}]:
            response=self.client.post('/api/checklists/',{'name':'Invalid','tasks':[task]},format='json')
            self.assertEqual(response.status_code,400,response.data)
        self.assertFalse(ChecklistTemplate.objects.exists())
    def test_visit_end_must_follow_start_and_does_not_freeze_invalid_report(self):
        visit=Visit.objects.create(site=self.a,started_at=timezone.now())
        result=self.send(self.operation('visit.close',visit.pk,version=1,at=visit.started_at-timedelta(days=1)))
        self.assertFalse(result['ok']);self.assertEqual(result['status'],400)
        visit.refresh_from_db();self.assertEqual(visit.status,'open');self.assertIsNone(visit.ended_at)
        self.assertFalse(VisitReport.objects.exists());self.assertFalse(OperationReceipt.objects.exists())
    def test_device_clock_start_can_be_corrected_then_visit_closed(self):
        visit=Visit.objects.create(site=self.a,started_at=timezone.now()+timedelta(days=1))
        corrected=timezone.now()-timedelta(hours=1)
        self.assertTrue(self.send(self.operation('visit.edit',visit.pk,{'started_at':corrected.isoformat()},1))['ok'])
        self.assertTrue(self.send(self.operation('visit.close',visit.pk,version=2))['ok'])
        visit.refresh_from_db();self.assertGreaterEqual(visit.ended_at,visit.started_at)
    def test_future_installation_and_removal_are_explicitly_rejected(self):
        self.client.force_authenticate(self.network)
        gear=Equipment.objects.create(instrument='Sensor',date_purchased='2025-01-01')
        response=self.client.post('/api/deployments/',{'site':self.a.pk,'equipment':gear.pk,'installed_at':(timezone.now()+timedelta(days=1)).isoformat()},format='json')
        self.assertEqual(response.status_code,400)
        response=self.client.post('/api/deployments/',{'site':self.a.pk,'equipment':gear.pk,'installed_at':(timezone.now()-timedelta(days=1)).isoformat()},format='json')
        self.assertEqual(response.status_code,201,response.data)
        response=self.client.patch(f"/api/deployments/{response.data['id']}/",{'removed_at':(timezone.now()+timedelta(days=1)).isoformat(),'base_version':1},format='json')
        self.assertEqual(response.status_code,400)
        gear.refresh_from_db();self.assertEqual(gear.site_id,self.a.pk)
    def test_archived_source_blocks_equipment_moves_and_deployments(self):
        self.client.force_authenticate(self.network)
        gear=Equipment.objects.create(instrument='Sensor',date_purchased='2025-01-01',site=self.a)
        self.a.is_archived=True;self.a.save()
        for site in [None,self.b.pk]:
            self.assertEqual(self.client.patch(f'/api/equipment/{gear.pk}/',{'site':site,'base_version':1},format='json').status_code,403)
        self.assertEqual(self.client.post('/api/deployments/',{'site':self.b.pk,'equipment':gear.pk,'installed_at':timezone.now().isoformat()},format='json').status_code,403)
        gear.refresh_from_db();self.assertEqual(gear.site_id,self.a.pk)
    def test_changed_account_or_session_is_rejected_before_any_write(self):
        client=APIClient();client.force_login(self.network)
        response=client.get('/api/bootstrap/')
        headers={'HTTP_X_WORKSPACE_ACCOUNT':response['X-Workspace-Account'],'HTTP_X_WORKSPACE_SESSION':response['X-Workspace-Session']}
        for user in [self.member,self.network]:
            client.force_login(user)
            response=client.post('/api/knowledge/',{'title':'Wrong identity','category':'general'},format='json',**headers)
            self.assertEqual(response.status_code,409,response.data if hasattr(response,'data') else response.content)
        from .models import KnowledgeEntry
        self.assertFalse(KnowledgeEntry.objects.exists())
    def test_matching_identity_allows_reads_and_logout(self):
        client=APIClient();client.force_login(self.member);response=client.get('/api/bootstrap/')
        headers={'HTTP_X_WORKSPACE_ACCOUNT':response['X-Workspace-Account'],'HTTP_X_WORKSPACE_SESSION':response['X-Workspace-Session']}
        self.assertEqual(client.get(f'/api/snapshot/?site={self.a.pk}',**headers).status_code,200)
        self.assertEqual(client.post('/api/logout/',{},format='json',**headers).status_code,200)
        self.assertEqual(client.get('/api/bootstrap/',**headers).status_code,409)
    def test_admin_cannot_bypass_domain_writes(self):
        user=get_user_model().objects.create_superuser('operator','operator@example.invalid','Local-super-password-2026')
        request=RequestFactory().get('/admin/');request.user=user
        for model in [Deployment,DataCaveat,Attachment,ChecklistTemplate,Site,Equipment]:
            model_admin=admin.site._registry[model]
            self.assertFalse(model_admin.has_add_permission(request));self.assertFalse(model_admin.has_change_permission(request));self.assertFalse(model_admin.has_delete_permission(request))
        request.user=self.limited
        for model in [Deployment,DataCaveat,Attachment,ChecklistTemplate,Site,Equipment]:
            self.assertFalse(admin.site._registry[model].has_view_permission(request))

    def test_older_browser_fetches_require_reload_before_private_reads_or_writes(self):
        client=APIClient();client.force_login(self.network)
        browser={'HTTP_SEC_FETCH_DEST':'empty','HTTP_SEC_FETCH_MODE':'cors'}
        self.assertEqual(client.get('/api/bootstrap/',**browser).status_code,200)
        self.assertEqual(client.get('/api/csrf/',**browser).status_code,200)
        self.assertEqual(client.get(f'/api/snapshot/?site={self.a.pk}',**browser).status_code,409)
        self.assertEqual(client.post('/api/knowledge/',{'title':'Old tab','category':'general'},format='json',**browser).status_code,409)
        from .models import KnowledgeEntry
        self.assertFalse(KnowledgeEntry.objects.exists())
