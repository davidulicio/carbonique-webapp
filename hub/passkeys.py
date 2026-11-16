from datetime import timedelta
from hashlib import sha256
import json
from urllib.parse import urlsplit
from uuid import UUID

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.crypto import constant_time_compare, get_random_string, salted_hmac
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import parse_authentication_credential_json
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from .models import Passkey, PasskeyAccount, PasskeyChallenge
from .permissions import role_for


def available(request):
    return bool(settings.WEBAUTHN_ORIGIN and
                request.build_absolute_uri("/") == f"{settings.WEBAUTHN_ORIGIN}/")


class PasskeyLoginView(LoginView):
    def get_context_data(self, **kwargs):
        return super().get_context_data(passkeys_available=available(self.request), **kwargs)


def require_passkeys(request, *, admin=False):
    if not available(request) or (admin and role_for(request.user) != "admin"):
        raise Http404
    return urlsplit(settings.WEBAUTHN_ORIGIN).hostname


def session_binding(request):
    nonce = request.session.get("passkey_nonce")
    if nonce:
        return salted_hmac("carbonique.passkey-session", f"{nonce}:{request.user.pk}", algorithm="sha256").hexdigest()
    return None


def options_response(request, purpose, options):
    if not request.session.get("passkey_nonce"):
        request.session["passkey_nonce"] = get_random_string(48)
    binding = session_binding(request)
    now = timezone.now()
    PasskeyChallenge.objects.filter(expires_at__lte=now).delete()
    PasskeyChallenge.objects.filter(session_binding=binding, purpose=purpose).delete()
    flow = PasskeyChallenge.objects.create(
        session_binding=binding, purpose=purpose, challenge=options.challenge,
        expires_at=now + timedelta(minutes=3),
    )
    return JsonResponse({"id": flow.id, "options": json.loads(options_to_json(options))})


def consume_challenge(request, purpose, flow_id):
    try:
        flow_id = UUID(str(flow_id))
    except ValueError:
        return None
    binding = session_binding(request)
    if not binding:
        return None
    flows = PasskeyChallenge.objects.filter(
        pk=flow_id, session_binding=binding, purpose=purpose, expires_at__gt=timezone.now(),
    )
    flow = flows.first()
    if flow and flows.delete()[0]:
        return bytes(flow.challenge)
    return None


def read_credential(request, purpose):
    try:
        payload = json.loads(request.body)
        if isinstance(payload, dict) and isinstance(payload.get("credential"), dict):
            challenge = consume_challenge(request, purpose, payload.get("id"))
            if challenge:
                return challenge, payload
    except (UnicodeError, ValueError):
        pass
    return None, None


@never_cache
@require_POST
def authentication_options(request):
    rp_id = require_passkeys(request)
    if request.user.is_authenticated:
        return JsonResponse({"detail": "Sign out before signing in with a passkey."}, status=409)
    options = generate_authentication_options(
        rp_id=rp_id, user_verification=UserVerificationRequirement.REQUIRED,
    )
    return options_response(request, "authenticate", options)


@never_cache
@require_POST
def sign_in(request):
    rp_id = require_passkeys(request)
    challenge, payload = read_credential(request, "authenticate")
    failure = JsonResponse({"detail": "This passkey could not sign you in. Try again or use your password."}, status=400)
    if request.user.is_authenticated or not challenge:
        return failure
    try:
        assertion = parse_authentication_credential_json(payload["credential"])
        credential_hash = sha256(assertion.raw_id).hexdigest()
        with transaction.atomic():
            key = Passkey.objects.select_for_update().select_related("account__user").get(credential_hash=credential_hash)
            user = key.account.user
            if role_for(user) != "admin" or not constant_time_compare(
                assertion.response.user_handle or b"", key.account.handle.bytes,
            ):
                return failure
            verified = verify_authentication_response(
                credential=assertion, expected_challenge=challenge, expected_rp_id=rp_id,
                expected_origin=settings.WEBAUTHN_ORIGIN, credential_public_key=bytes(key.public_key),
                credential_current_sign_count=key.sign_count, require_user_verification=True,
            )
            key.sign_count = verified.new_sign_count
            key.last_used_at = timezone.now()
            key.save(update_fields=["sign_count", "last_used_at"])
    except (Passkey.DoesNotExist, WebAuthnException, ValueError):
        return failure
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session.pop("passkey_nonce", None)
    return JsonResponse({"redirect": "/"})


def confirmed_password(request):
    user = authenticate(request, username=request.user.get_username(), password=request.POST.get("password", ""))
    return user is not None and user.pk == request.user.pk


@never_cache
@require_http_methods(["GET", "HEAD"])
def manage(request):
    require_passkeys(request, admin=True)
    keys = Passkey.objects.filter(account__user=request.user).order_by("created_at")
    return render(request, "registration/passkeys.html", {"keys": keys})


@never_cache
@require_POST
def registration_options(request):
    rp_id = require_passkeys(request, admin=True)
    if not confirmed_password(request):
        return JsonResponse({"detail": "Enter your current password to add a passkey."}, status=400)
    account, _ = PasskeyAccount.objects.get_or_create(user=request.user)
    options = generate_registration_options(
        rp_id=rp_id, rp_name="Carbonique Hub", user_id=account.handle.bytes,
        user_name=request.user.get_username(),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=bytes(key.credential_id)) for key in account.keys.all()],
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED, user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )
    return options_response(request, "register", options)


@never_cache
@require_POST
def register(request):
    rp_id = require_passkeys(request, admin=True)
    challenge, payload = read_credential(request, "register")
    if not challenge:
        return JsonResponse({"detail": "Passkey setup expired. Start again."}, status=400)
    label = payload.get("label")
    if not isinstance(label, str) or not label.strip() or len(label) > 80:
        return JsonResponse({"detail": "Enter a passkey name of up to 80 characters."}, status=400)
    try:
        verified = verify_registration_response(
            credential=payload["credential"], expected_challenge=challenge, expected_rp_id=rp_id,
            expected_origin=settings.WEBAUTHN_ORIGIN, require_user_verification=True,
        )
    except (WebAuthnException, ValueError):
        return JsonResponse({"detail": "The passkey could not be registered."}, status=400)
    account = get_object_or_404(PasskeyAccount, user=request.user)
    _, created = Passkey.objects.get_or_create(
        credential_hash=sha256(verified.credential_id).hexdigest(),
        defaults={
            "account": account, "credential_id": verified.credential_id,
            "public_key": verified.credential_public_key, "sign_count": verified.sign_count,
            "label": label.strip(),
        },
    )
    if not created:
        return JsonResponse({"detail": "This passkey is already registered."}, status=409)
    return JsonResponse({"redirect": "/accounts/passkeys/"}, status=201)


@never_cache
@require_POST
def remove(request, pk):
    require_passkeys(request, admin=True)
    key = get_object_or_404(Passkey, pk=pk, account__user=request.user)
    if not confirmed_password(request):
        keys = Passkey.objects.filter(account__user=request.user).order_by("created_at")
        return render(request, "registration/passkeys.html", {
            "keys": keys, "error": "Enter your current password to remove a passkey.",
        }, status=400)
    key.delete()
    return redirect("manage_passkeys")
