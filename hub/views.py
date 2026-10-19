import csv
import io
from pathlib import Path
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework.exceptions import PermissionDenied
from inventory.models import Photo, Document, Site
from .models import Attachment, Task, Visit, DataCaveat
from .permissions import require_site, role_for
from .serializers import clean_html

@login_required
@ensure_csrf_cookie
def home(request):
    if not role_for(request.user):
        return render(request, "no_access.html", status=403)
    return render(request, "app.html")

@require_GET
@ensure_csrf_cookie
def csrf_token(request):
    from django.middleware.csrf import get_token
    return JsonResponse({"csrfToken": get_token(request), "authenticated": request.user.is_authenticated})

def file_response(field, filename, content_type="application/octet-stream", inline=False):
    try:
        response = FileResponse(field.open("rb"), as_attachment=not inline, filename=filename, content_type=content_type)
    except (FileNotFoundError, ValueError, OSError):
        raise Http404("The attachment file is missing from storage.")
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "sandbox; default-src 'none'"
    return response

@login_required
@require_http_methods(["GET", "HEAD"])
def attachment_download(request, pk):
    obj = get_object_or_404(Attachment, pk=pk)
    try:
        require_site(request.user, obj.site_id)
    except PermissionDenied:
        return HttpResponse("Access denied", status=403)
    if obj.content_type.startswith(("video/", "audio/")):
        from .media import stream_file
        return stream_file(request, obj.file, obj.filename, obj.content_type, download=request.GET.get("download") == "1")
    inline = obj.content_type in {"image/jpeg", "image/png", "image/webp", "image/gif"}
    return file_response(obj.file, obj.filename, obj.content_type, inline)

@login_required
def legacy_download(request, kind, pk):
    if kind == "photo":
        obj = get_object_or_404(Photo, pk=pk)
        site_id = obj.fieldnote.site_id
        field = obj.photo
    elif kind == "document":
        obj = get_object_or_404(Document, pk=pk)
        parent = obj.content_object
        if parent is None:
            raise Http404()
        site_id = parent.pk if isinstance(parent, Site) else getattr(parent, "site_id", None)
        field = obj.file
    else:
        raise Http404()
    try:
        if site_id is None:
            if not role_for(request.user):
                raise PermissionDenied()
        else:
            require_site(request.user, site_id)
    except PermissionDenied:
        return HttpResponse("Access denied", status=403)
    # Legacy files may have unknown MIME types; download rather than trusting filenames.
    return file_response(field, Path(field.name).name)

@require_GET
def service_worker(request):
    response = HttpResponse((settings.BASE_DIR / "static/hub/sw.js").read_text(encoding="utf-8"), content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response

@require_GET
def manifest(request):
    return JsonResponse({
        "name": "Carbonique Hub", "short_name": "Carbonique", "start_url": "/",
        "scope": "/", "display": "standalone", "background_color": "#f5f7f2",
        "theme_color": "#77633c", "icons": [
            {"src": f"/static/hub/carbonique-icon-{size}.png", "sizes": f"{size}x{size}",
             "type": "image/png", "purpose": "any"}
            for size in (192, 512)
        ],
    })

@login_required
def export_csv(request):
    try:
        site = require_site(request.user, request.GET.get("site"))
    except PermissionDenied:
        return HttpResponse("Access denied", status=403)
    kind = request.GET.get("kind", "tasks")
    if kind == "visits":
        fields = ["id", "date", "title", "crew", "classification", "status", "started_at", "ended_at"]
        rows = Visit.objects.filter(site=site).values_list(*fields)
    else:
        fields = ["id", "title", "details", "priority", "status", "due_date", "created_at", "version"]
        rows = Task.objects.filter(site=site).values_list(*fields)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{site.code}-{kind}.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(fields)
    for row in rows:
        writer.writerow(["'" + str(v) if str(v).lstrip().startswith(("=", "+", "-", "@")) else v for v in row])
    return response

@require_GET
def public_reference(request):
    # Keep old bookmarks pointing to the one current public report.
    if not settings.PUBLIC_FIELDNOTES_ENABLED:
        raise Http404()
    return redirect("public_fieldnotes")

@require_GET
def health(request):
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})

@require_GET
def public_fieldnotes(request):
    if not settings.PUBLIC_FIELDNOTES_ENABLED:
        raise Http404()
    from django.utils import timezone
    response = render(request, "public_fieldnotes.html", {"revision": timezone.now().timestamp()})
    response["Cache-Control"] = "no-store"
    return response


@require_GET
@xframe_options_exempt
def fieldnotes_content(request):
    if not settings.PUBLIC_FIELDNOTES_ENABLED:
        raise Http404()
    from .public_report import render_report
    response = HttpResponse(render_report(), content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-store"
    response["Content-Security-Policy"] = "sandbox allow-scripts allow-popups allow-downloads; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
    return response


@require_GET
def fieldnotes_download(request):
    if not settings.PUBLIC_FIELDNOTES_ENABLED:
        raise Http404()
    from .public_report import render_report
    response = HttpResponse(render_report(snapshot=True), content_type="text/html; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="carbonique-fieldnotes.html"'
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
