import hashlib
import io
import json
import csv
import re
import zipfile
from pathlib import Path
from django.conf import settings
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse, StreamingHttpResponse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from .uploads import image_content_type
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from . import badm
from .models import SiteCondition, BADMProfile, BADMRecord, Protocol, SiteMedia
from .permissions import require_role, require_site, role_for
from .services import audit, check_version


def team_access(user):
    require_role(user, "viewer", "member", "researcher", "manager", "admin")


def manage(user):
    require_role(user, "manager", "admin")


class ConditionSerializer(serializers.ModelSerializer):
    review_overdue = serializers.SerializerMethodField()
    class Meta:
        model = SiteCondition
        exclude = ["id"]
        read_only_fields = ["site", "updated_by", "updated_at", "version"]
    def get_review_overdue(self, obj):
        return bool(obj.valid_until and obj.valid_until < timezone.localdate())


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BADMProfile
        exclude = ["id"]
        read_only_fields = ["site", "version"]
    def validate_station_id(self, value):
        if value and not re.fullmatch(r"[A-Z]{2}-[A-Za-z0-9]{3}", value):
            raise ValidationError("Use the assigned ICOS code, CC-Xxx.")
        return value
    def validate(self, attrs):
        cls = attrs.get("station_class", self.instance.station_class)
        allowed = {g for t in badm.templates(cls).values() for g in t["groups"]}
        groups = attrs.get("applicable_groups", self.instance.applicable_groups)
        if not isinstance(groups, list) or any(not isinstance(g, str) or g not in allowed for g in groups):
            raise ValidationError("Select applicable groups available for this station class.")
        return attrs


class RecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = BADMRecord
        fields = "__all__"
        read_only_fields = ["id", "site", "updated_by", "updated_at", "version"]
    def validate(self, attrs):
        template = attrs.get("template", getattr(self.instance, "template", ""))
        group = attrs.get("group", getattr(self.instance, "group", ""))
        fields = badm.schema()["templates"].get(template, {}).get("groups", {}).get(group)
        if fields is None:
            raise ValidationError("Select an official template and group.")
        values = attrs.get("values", getattr(self.instance, "values", {}))
        if not isinstance(values, dict) or any(k not in {f["name"] for f in fields} for k in values):
            raise ValidationError("Use only variables defined in this template group.")
        if any(not isinstance(v, (str, int, float)) or isinstance(v, bool) or len(str(v)) > 10000 for v in values.values()):
            raise ValidationError("Each variable needs a text or numeric value of at most 10,000 characters.")
        return attrs


class ProtocolSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()
    class Meta:
        model = Protocol
        exclude = ["file", "bundled_file"]
        read_only_fields = ["id", "filename", "sha256", "size", "uploaded_by", "created_at", "version"]
    def get_url(self, obj):
        return f"/protocols/{obj.pk}/file/"
    def get_available(self, obj):
        if obj.file:
            return obj.file.storage.exists(obj.file.name)
        return bool(obj.bundled_file and (settings.BASE_DIR / "seed/protocols" / obj.bundled_file).is_file())


class MediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = SiteMedia
        exclude = ["file"]
        read_only_fields = ["id", "site", "filename", "content_type", "size", "sha256", "uploaded_by", "created_at", "version"]
    def get_url(self, obj):
        return f"/site-media/{obj.pk}/file/"


def condition_data(site):
    obj = SiteCondition.objects.filter(site=site).first()
    return ConditionSerializer(obj).data if obj else {"site": site.pk, "status": "unknown", "statement": "", "valid_until": None, "version": 0, "review_overdue": False}


def resource_state(site):
    profile = BADMProfile.objects.filter(site=site).first() or BADMProfile(site=site, version=0)
    records = list(site.badm_records.order_by("group", "updated_at"))
    return {"condition": condition_data(site), "media": MediaSerializer(site.tower_media.filter(is_archived=False), many=True).data, "badm": {"profile": ProfileSerializer(profile).data, "records": RecordSerializer(records, many=True).data, "validation": badm.completeness(profile, records), "schema_date": badm.schema()["retrieved"]}}


@api_view(["GET"])
def badm_schema(request):
    team_access(request.user)
    return Response(badm.schema())


@api_view(["PATCH"])
@transaction.atomic
def condition(request, site_id):
    manage(request.user)
    site = require_site(request.user, site_id, writable=True)
    # Lock the site also serializes creation of its one-to-one resources.
    site.__class__.objects.select_for_update().get(pk=site.pk)
    obj = SiteCondition.objects.select_for_update().filter(site=site).first() or SiteCondition(site=site, version=0)
    check_version(obj, request.data.get("base_version"))
    serializer = ConditionSerializer(obj, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    obj = serializer.save(updated_by=request.user, version=obj.version + 1)
    audit(request.user, "site.condition_updated", obj, site, {"condition": serializer.data})
    return Response(serializer.data)


@api_view(["PATCH"])
@transaction.atomic
def profile(request, site_id):
    manage(request.user)
    site = require_site(request.user, site_id, writable=True)
    site.__class__.objects.select_for_update().get(pk=site.pk)
    obj = BADMProfile.objects.select_for_update().filter(site=site).first() or BADMProfile(site=site, version=0)
    check_version(obj, request.data.get("base_version"))
    before = ProfileSerializer(obj).data
    serializer = ProfileSerializer(obj, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save(version=obj.version + 1)
    audit(request.user, "badm.profile_updated", obj, site, {"before": before})
    return Response(serializer.data)


@api_view(["POST", "PATCH"])
@transaction.atomic
def record(request, site_id, pk=None):
    manage(request.user)
    site = require_site(request.user, site_id, writable=True)
    obj = BADMRecord.objects.select_for_update().filter(site=site, pk=pk).first() if pk else None
    if pk and not obj:
        raise Http404()
    before = RecordSerializer(obj).data if obj else {}
    if obj:
        check_version(obj, request.data.get("base_version"))
    serializer = RecordSerializer(obj, data=request.data, partial=bool(obj))
    serializer.is_valid(raise_exception=True)
    station = BADMProfile.objects.filter(site=site).first() or BADMProfile(site=site)
    template = serializer.validated_data.get("template", obj.template if obj else "")
    if template not in badm.templates(station.station_class):
        raise ValidationError("This template does not match the station class.")
    saved = serializer.save(site=site, updated_by=request.user, version=obj.version + 1 if obj else 1)
    audit(request.user, "badm.record_saved", saved, site, {"before": before})
    return Response(RecordSerializer(saved).data, status=200 if obj else 201)


def uploaded_file(request, kind):
    file = request.FILES.get("file")
    if not file or not file.size:
        raise ValidationError("Choose a nonempty file.")
    limit = settings.MAX_UPLOAD_BYTES if kind == "pdf" else getattr(settings, "MAX_SITE_MEDIA_BYTES", 100 * 1024 * 1024)
    if file.size > limit:
        raise ValidationError(f"Maximum file size is {limit // 1024 // 1024} MB.")
    suffix = Path(file.name).suffix.lower()
    head = file.read(32)
    file.seek(0)
    content_type = "application/pdf"
    if kind == "pdf":
        if suffix != ".pdf" or not head.startswith(b"%PDF-"):
            raise ValidationError("Upload a valid PDF file.")
    elif suffix in {".gif", ".webp", ".jpg", ".jpeg", ".png"}:
        content_type = image_content_type(file, file.name)
    elif suffix in {".mp4", ".m4v"} and head[4:8] == b"ftyp":
        content_type = "video/mp4"
    elif suffix == ".webm" and head.startswith(b"\x1aE\xdf\xa3"):
        content_type = "video/webm"
    else:
        raise ValidationError("Use MP4, WebM, GIF, WebP, JPEG or PNG.")
    file.seek(0)
    digest = hashlib.sha256()
    for chunk in file.chunks():
        digest.update(chunk)
    file.seek(0)
    return file, content_type, digest.hexdigest()


@api_view(["GET", "POST", "PATCH"])
@transaction.atomic
def protocols(request, pk=None):
    team_access(request.user)
    if request.method == "GET":
        return Response(ProtocolSerializer(Protocol.objects.filter(is_archived=False), many=True).data)
    manage(request.user)
    obj = Protocol.objects.select_for_update().filter(pk=pk).first() if pk else None
    if pk and not obj:
        raise Http404()
    before = ProtocolSerializer(obj).data if obj else {}
    if obj:
        check_version(obj, request.data.get("base_version"))
    serializer = ProtocolSerializer(obj, data=request.data, partial=bool(obj))
    serializer.is_valid(raise_exception=True)
    extra = {"version": obj.version + 1 if obj else 1}
    if not obj or request.FILES.get("file"):
        file, _, sha = uploaded_file(request, "pdf")
        extra.update(file=file, bundled_file="", filename=Path(file.name).name[:250], size=file.size, sha256=sha, uploaded_by=request.user)
    saved = serializer.save(**extra)
    audit(request.user, "protocol.saved", saved, detail={"before": before})
    return Response(ProtocolSerializer(saved).data, status=200 if obj else 201)


@api_view(["POST", "PATCH"])
@transaction.atomic
def media(request, site_id, pk=None):
    manage(request.user)
    site = require_site(request.user, site_id, writable=True)
    obj = SiteMedia.objects.select_for_update().filter(site=site, pk=pk).first() if pk else None
    if pk and not obj:
        raise Http404()
    if obj:
        check_version(obj, request.data.get("base_version"))
    serializer = MediaSerializer(obj, data=request.data, partial=bool(obj))
    serializer.is_valid(raise_exception=True)
    extra = {"site": site, "version": obj.version + 1 if obj else 1}
    if not obj or request.FILES.get("file"):
        file, mime, sha = uploaded_file(request, "media")
        extra.update(file=file, filename=Path(file.name).name[:250], content_type=mime, size=file.size, sha256=sha, uploaded_by=request.user)
    saved = serializer.save(**extra)
    audit(request.user, "site.media_saved", saved, site)
    return Response(MediaSerializer(saved).data, status=200 if obj else 201)


@api_view(["GET"])
@xframe_options_sameorigin
def protocol_file(request, pk):
    team_access(request.user)
    obj = Protocol.objects.filter(pk=pk).first()
    if not obj:
        raise Http404()
    from .views import file_response
    if obj.bundled_file:
        root = (settings.BASE_DIR / "seed/protocols").resolve()
        path = (root / obj.bundled_file).resolve()
        if path.parent != root or not path.is_file():
            raise Http404()
        response = FileResponse(path.open("rb"), content_type="application/pdf", as_attachment=request.GET.get("download") == "1", filename=obj.filename)
        response["Cache-Control"] = "private, no-store"
        response["Content-Security-Policy"] = "sandbox; default-src 'none'"
        response["X-Content-Type-Options"] = "nosniff"
        return response
    return file_response(obj.file, obj.filename, "application/pdf", inline=request.GET.get("download") != "1")


@api_view(["GET", "HEAD"])
def media_file(request, pk):
    team_access(request.user)
    obj = SiteMedia.objects.filter(pk=pk).first()
    if not obj:
        raise Http404()
    require_site(request.user, obj.site_id)
    from .media import stream_file
    return stream_file(request,obj.file,obj.filename,obj.content_type,download=request.GET.get("download")=="1")


@api_view(["GET"])
def badm_export(request, site_id):
    team_access(request.user)
    site = require_site(request.user, site_id)
    state = resource_state(site)["badm"]
    state["templates"] = badm.schema()["templates"]
    records = list(site.badm_records.order_by("template", "group", "updated_at"))
    output = io.BytesIO()
    station_id = state["profile"]["station_id"] or "UNASSIGNED"
    date = timezone.localdate().strftime("%Y%m%d")
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("all-records.json", json.dumps({"site": site.code, "exported_at": timezone.now().isoformat(), **state}, ensure_ascii=False, indent=2, default=str))
        groups = {}
        for obj in records:
            if not obj.is_archived:
                groups.setdefault((obj.template, obj.group), []).append(obj)
        for index, ((template, group), entries) in enumerate(groups.items(), 1):
            columns = [f["name"] for f in badm.schema()["templates"][template]["groups"][group] if f["requirement"] == "r" or any(badm.present(r.values.get(f["name"])) for r in entries)]
            stream = io.StringIO(newline="")
            writer = csv.writer(stream)
            writer.writerow(columns)
            # Preserve scientific values, including negative numbers. CSV is an
            # ICOS import format; spreadsheet users should import text columns.
            for obj in entries:
                writer.writerow([obj.values.get(c, "") for c in columns])
            archive.writestr(f"{template}/{group}/{station_id}_{date}_BADM_{index:06d}.csv", stream.getvalue())
        archive.writestr("README.txt", "ICOS BADM export: one CSV per variable group, with variables in columns and observations in rows. SITE_ID is carried by the filename, as specified in the ICOS instructions. JSON preserves all records, including archived records, notes, template versions and validation.\n\n" + state["validation"]["scope"] + "\nFiles with missing data or an UNASSIGNED station ID are drafts. The JSON validation report lists outstanding items. Nothing is submitted to ICOS automatically.\nCSV values are preserved exactly for scientific import. Import text columns as text when opening in a spreadsheet.\nSources: https://www.icos-etc.eu/icos/documents/templates and https://www.icos-etc.eu/icos/documents/instructions/badm\n")
    response = HttpResponse(output.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{site.code}-BADM-{date}.zip"'
    response["Cache-Control"] = "private, no-store"
    return response


@api_view(["GET"])
def inventory_source(request):
    team_access(request.user)
    root = settings.BASE_DIR / "seed/ecoflux_inventory_export"
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(root).as_posix())
    response = HttpResponse(output.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="ecoflux-inventory-source-20261016.zip"'
    response["Cache-Control"] = "private, no-store"
    return response
