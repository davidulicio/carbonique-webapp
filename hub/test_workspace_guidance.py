from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from inventory.models import Equipment, Site

from .models import Attachment, PasskeyChallenge


class BrowserSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser("browser-admin", password="browser-test-password")

    def test_workspace_policy_and_neutral_shell(self):
        self.client.force_login(self.admin)
        home = self.client.get("/")
        self.assertIn("connect-src 'self'", home["Content-Security-Policy"])
        self.assertIn("camera=()", home["Permissions-Policy"])
        self.assertIn("require-trusted-types-for", home["Content-Security-Policy-Report-Only"])
        self.assertContains(home, 'name="csrf-token"')

        shell = Client().get(reverse("offline_shell"))
        self.assertEqual(shell["Cache-Control"], "private, no-store")
        self.assertNotContains(shell, 'name="csrf-token"')
        self.assertNotContains(shell, "Manage passkeys")

    @override_settings(TRUSTED_TYPES_ENFORCE=True)
    def test_trusted_types_enforcement_is_configurable(self):
        response = self.client.get(reverse("offline_shell"))
        self.assertIn("require-trusted-types-for 'script'", response["Content-Security-Policy"])
        self.assertNotIn("Content-Security-Policy-Report-Only", response)

    def test_account_and_admin_logout_use_same_device_cleanup(self):
        for url in (reverse("logout"), reverse("admin:logout")):
            self.client.force_login(self.admin)
            response = self.client.post(url, secure=True)
            self.assertRedirects(response, reverse("signed_out"))
            self.assertEqual(response["Clear-Site-Data"], '"cache"')
            self.assertNotIn("_auth_user_id", self.client.session)

    def test_offline_snapshot_is_scoped_to_its_site(self):
        prepared = Site.objects.create(code="PREPARED", name="Prepared site", date_activated="2025-01-01")
        other = Site.objects.create(code="OTHER", name="Other site", date_activated="2025-01-01")
        instruments = [
            Equipment.objects.create(site=site, instrument=site.code, serial_number=site.code, date_purchased="2025-01-01")
            for site in (prepared, other)
        ]
        files = [
            Attachment.objects.create(site=item.site, equipment=item, file=f"{item.serial_number}.txt", filename=f"{item.serial_number}.txt")
            for item in instruments
        ]
        self.client.force_login(self.admin)
        route = "/api/snapshot/"
        live = self.client.get(route, {"site": prepared.pk}).json()
        self.assertIn(instruments[1].pk, {item["id"] for item in live["equipment"]})
        self.assertIn(str(files[1].pk), {item["id"] for item in live["attachments"]})
        scoped = self.client.get(route, {"site": prepared.pk, "offline": "1"}).json()
        self.assertEqual({item["id"] for item in scoped["equipment"]}, {instruments[0].pk})
        self.assertEqual({item["id"] for item in scoped["attachments"]}, {str(files[0].pk)})


@override_settings(WEBAUTHN_ORIGIN="https://testserver", AXES_ENABLED=False)
class PasskeyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model().objects
        cls.admin = users.create_superuser("passkey-admin", password="passkey-test-password")
        cls.standard = users.create_user("standard", password="standard-test-password")

    def test_passkey_options_require_configured_origin_and_csrf(self):
        url = reverse("passkey_authentication_options")
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertEqual(Client(enforce_csrf_checks=True).post(url, secure=True).status_code, 403)
        response = self.client.post(url, secure=True)
        self.assertEqual(response.json()["options"]["userVerification"], "required")

    def test_registration_is_limited_to_admins_with_their_current_password(self):
        url = reverse("passkey_registration_options")
        self.client.force_login(self.standard)
        self.assertEqual(self.client.post(url, {"password": "standard-test-password"}, secure=True).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(url, {"password": "wrong"}, secure=True).status_code, 400)
        response = self.client.post(url, {"password": "passkey-test-password"}, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["options"]["authenticatorSelection"]["residentKey"], "required")

    def test_challenge_is_session_bound_and_consumed_once(self):
        response = self.client.post(reverse("passkey_authentication_options"), secure=True)
        flow_id = response.json()["id"]
        url = reverse("passkey_sign_in")
        payload = {"id": flow_id, "credential": {}}
        unrelated = Client()
        self.assertEqual(unrelated.post(url, payload, content_type="application/json", secure=True).status_code, 400)
        self.assertTrue(PasskeyChallenge.objects.filter(pk=flow_id).exists())
        for _ in range(2):
            self.assertEqual(self.client.post(url, payload, content_type="application/json", secure=True).status_code, 400)
            self.assertFalse(PasskeyChallenge.objects.filter(pk=flow_id).exists())
