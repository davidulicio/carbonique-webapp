"""Browser security policy and conservative reverse-proxy address handling."""
from ipaddress import ip_address, ip_network
from django.conf import settings


def client_ip(request):
    """Use a proxy's overwritten X-Real-IP only for a configured trusted peer."""
    try:
        peer = ip_address(request.META.get("REMOTE_ADDR", ""))
    except ValueError:
        return None
    if getattr(settings, "SECURE_PROXY_SSL_HEADER", None):
        networks = getattr(settings, "TRUSTED_PROXY_NETWORKS", [])
        try:
            trusted = any(peer in ip_network(value) for value in networks)
        except ValueError:
            trusted = False
        if trusted:
            try:
                return str(ip_address(request.META.get("HTTP_X_REAL_IP", "")))
            except ValueError:
                pass
    return str(peer)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 429 and request.path.startswith(("/accounts/", "/admin/login/")):
            response.setdefault("Retry-After", "900")
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.setdefault("Referrer-Policy", "same-origin")
        response.setdefault("X-Content-Type-Options", "nosniff")
        # The sandboxed public report and downloads can supply stricter policies.
        response.setdefault("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; media-src 'self' blob:; connect-src 'self'; worker-src 'self' blob:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-src 'self'; frame-ancestors 'none'")
        if request.path.startswith(("/api/", "/accounts/", "/admin/", "/attachments/", "/legacy-attachments/", "/knowledge-files/", "/processing-files/", "/protocols/", "/site-media/", "/sites/")) or request.path in {"/", "/export.csv", "/inventory-source.zip"}:
            response["Cache-Control"] = "private, no-store"
        return response


class WorkspaceIdentityMiddleware:
    """Reject a stale tab before private views run; expose no session credential."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.http import JsonResponse
        from django.utils.crypto import salted_hmac
        private = request.path.startswith(("/api/", "/attachments/", "/legacy-attachments/", "/knowledge-files/", "/processing-files/", "/protocols/", "/site-media/", "/sites/"))
        if not private:
            return self.get_response(request)
        account = str(request.user.pk) if request.user.is_authenticated else ""
        session = salted_hmac("workspace-session", request.session.session_key).hexdigest() if account and request.session.session_key else ""
        expected_account = request.headers.get("X-Workspace-Account")
        expected_session = request.headers.get("X-Workspace-Session")
        browser_fetch = request.headers.get("Sec-Fetch-Dest") == "empty" and request.headers.get("Sec-Fetch-Mode") in {"cors", "same-origin"}
        initial_read = request.method == "GET" and request.path in {"/api/bootstrap/", "/api/csrf/"}
        unbound_browser = browser_fetch and expected_account is None and not initial_read
        if unbound_browser or (expected_account is not None and expected_account != account) or (expected_session is not None and expected_session != session):
            response = JsonResponse({"detail": "The signed-in session changed. Reload and sign in with the account that owns this work. Pending records remain on this device.", "code": "workspace_identity_changed"}, status=409)
        else:
            response = self.get_response(request)
        response["X-Workspace-Account"] = account
        response["X-Workspace-Session"] = session
        return response
