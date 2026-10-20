"""Security regression checks for login, headers and authenticated endpoints."""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase, override_settings
from django.utils import timezone
from axes.models import AccessAttempt
from .security import client_ip
from .models import TeamMember
from inventory.models import Site

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class LoginProtectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user=get_user_model().objects.create_user('field-user',password='Unique-field-password-2026')
        cls.other=get_user_model().objects.create_user('other-user',password='Unique-other-password-2026')
        TeamMember.objects.create(user=cls.user,role='member')
        TeamMember.objects.create(user=cls.other,role='viewer')
    def attempt(self,client=None,password='wrong',username='field-user',path='/accounts/login/',**headers):
        return (client or self.client).post(path,{'username':username,'password':password},**headers)
    def test_team_login_blocks_after_five_failures_even_with_correct_password(self):
        for index in range(5):
            response=self.attempt()
        self.assertEqual(response.status_code,429)
        response=self.attempt(password='Unique-field-password-2026')
        self.assertEqual(response.status_code,429);self.assertEqual(response['Retry-After'],'900')
        self.assertNotIn('_auth_user_id',self.client.session)
        self.assertContains(response,'Sign-in temporarily paused',status_code=429)
    def test_admin_login_cannot_bypass_team_lockout(self):
        for index in range(5):self.attempt()
        response=self.attempt(path='/admin/login/',password='Unique-field-password-2026')
        self.assertEqual(response.status_code,429)
    def test_spoofed_forwarded_headers_do_not_bypass_lockout(self):
        for index in range(5):
            self.attempt(HTTP_X_REAL_IP=f'198.51.100.{index+1}',HTTP_X_FORWARDED_FOR=f'198.51.100.{index+1}')
        self.assertEqual(self.attempt(HTTP_X_REAL_IP='203.0.113.99').status_code,429)
    def test_distinct_account_is_not_locked_out_by_another_users_failures(self):
        for index in range(5):self.attempt()
        response=self.attempt(username='other-user',password='Unique-other-password-2026')
        self.assertEqual(response.status_code,302)
        self.assertEqual(int(self.client.session['_auth_user_id']),self.other.pk)
    def test_separate_client_cannot_reset_persistent_failures(self):
        for index in range(4):self.attempt(client=Client())
        self.assertEqual(self.attempt(client=Client()).status_code,429)
    def test_successful_login_resets_prior_failures(self):
        for index in range(4):self.attempt()
        self.assertEqual(self.attempt(password='Unique-field-password-2026').status_code,302)
        self.client.logout()
        self.assertEqual(self.attempt().status_code,200)
    def test_cooldown_expires_and_blocked_requests_do_not_extend_it(self):
        for index in range(5):self.attempt()
        before=AccessAttempt.objects.get().attempt_time
        self.attempt();self.assertEqual(AccessAttempt.objects.get().attempt_time,before)
        AccessAttempt.objects.update(attempt_time=timezone.now()-timedelta(minutes=16))
        self.assertEqual(self.attempt(password='Unique-field-password-2026').status_code,302)
    def test_credentials_are_not_written_to_attempt_records(self):
        self.attempt(password='never-write-this-password')
        attempt=AccessAttempt.objects.get()
        self.assertNotIn('never-write-this-password',attempt.post_data)
    def test_login_requires_csrf_and_rejects_external_redirects(self):
        client=Client(enforce_csrf_checks=True)
        response=client.post('/accounts/login/',{'username':'field-user','password':'Unique-field-password-2026'})
        self.assertEqual(response.status_code,403);self.assertFalse(AccessAttempt.objects.exists())
        response=self.client.post('/accounts/login/',{'username':'field-user','password':'Unique-field-password-2026','next':'https://attacker.example/collect'})
        self.assertEqual(response.status_code,302);self.assertEqual(response['Location'],'/')
    def test_password_change_requires_twelve_characters(self):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):validate_password('aB7xQ2nR9k',self.user)

class ProxyAddressTests(TestCase):
    def setUp(self):self.factory=RequestFactory()
    def request(self,peer,real='198.51.100.20'):
        return self.factory.get('/',REMOTE_ADDR=peer,HTTP_X_REAL_IP=real,HTTP_X_FORWARDED_FOR='203.0.113.99')
    @override_settings(SECURE_PROXY_SSL_HEADER=None)
    def test_forwarded_addresses_ignored_without_proxy_mode(self):
        self.assertEqual(client_ip(self.request('127.0.0.1')),'127.0.0.1')
    @override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https'),TRUSTED_PROXY_NETWORKS=['127.0.0.1/32'])
    def test_only_trusted_proxy_can_supply_valid_client_address(self):
        self.assertEqual(client_ip(self.request('127.0.0.1')),'198.51.100.20')
        self.assertEqual(client_ip(self.request('203.0.113.10')),'203.0.113.10')
        self.assertEqual(client_ip(self.request('127.0.0.1','198.51.100.20, 203.0.113.99')),'127.0.0.1')
        self.assertEqual(client_ip(self.request('127.0.0.1','invalid')),'127.0.0.1')
    @override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https'),TRUSTED_PROXY_NETWORKS=['not-a-network'])
    def test_invalid_proxy_config_does_not_trust_headers(self):
        self.assertEqual(client_ip(self.request('127.0.0.1')),'127.0.0.1')

class SecurityBoundaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.site=Site.objects.create(code='SECURITY',name='Security test site',date_activated='2026-01-01')
        cls.user=get_user_model().objects.create_user('reader',password='Unique-reader-password-2026')
        TeamMember.objects.create(user=cls.user,role='viewer')
    def test_security_headers_and_no_private_response_caching(self):
        self.client.force_login(self.user)
        for path in ['/', '/api/bootstrap/', f'/api/snapshot/?site={self.site.pk}', '/accounts/login/']:
            response=self.client.get(path)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response['Cache-Control'],'private, no-store')
            self.assertIn("script-src 'self';",response['Content-Security-Policy'])
            self.assertIn("object-src 'none'",response['Content-Security-Policy'])
            self.assertIn('camera=()',response['Permissions-Policy'])
            self.assertEqual(response['X-Content-Type-Options'],'nosniff')
    def test_public_report_keeps_its_origin_isolating_sandbox(self):
        response=self.client.get('/fieldnotes/content/')
        self.assertEqual(response.status_code,200)
        policy=response['Content-Security-Policy']
        self.assertIn('sandbox allow-scripts',policy);self.assertNotIn('allow-same-origin',policy)
        self.assertIn("form-action 'none'",policy)
    def test_unauthenticated_requests_cannot_read_internal_resources(self):
        for path in ['/api/bootstrap/',f'/api/snapshot/?site={self.site.pk}','/api/team/','/api/monitor/?refresh=1','/api/knowledge/','/api/processing-files/',f'/api/sites/{self.site.pk}/calibrations/']:
            with self.subTest(path=path):self.assertEqual(self.client.get(path).status_code,403)
    def test_sensitive_files_have_no_public_http_routes(self):
        for path in ['/.env','/.git/config','/db.sqlite3','/backups/example.zip','/credentials/monitor-stations.json','/private-media/test.pdf','/media/test.pdf','/seed/protocols/Data_download.pdf']:
            with self.subTest(path=path):self.assertEqual(self.client.get(path).status_code,404)
    def test_unknown_host_header_is_rejected(self):
        self.assertEqual(self.client.get('/health/',HTTP_HOST='attacker.example').status_code,400)
    def test_no_permissive_cors_for_untrusted_origin(self):
        self.client.force_login(self.user)
        response=self.client.get('/api/bootstrap/',HTTP_ORIGIN='https://attacker.example')
        self.assertNotIn('Access-Control-Allow-Origin',response)
    def test_public_routes_do_not_accept_mutations(self):
        for path in ['/fieldnotes/','/fieldnotes/content/','/fieldnotes/download/']:
            self.assertEqual(self.client.post(path,{'title':'Injected'}).status_code,405)
    def test_viewer_cannot_write_even_with_valid_session_and_csrf(self):
        from rest_framework.test import APIClient
        client=APIClient();client.force_login(self.user)
        response=client.post('/api/knowledge/',{'title':'not permitted'},format='json')
        self.assertEqual(response.status_code,403)
