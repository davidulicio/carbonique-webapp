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
