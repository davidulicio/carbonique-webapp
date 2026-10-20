import hashlib
import json
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as ModelValidationError
from django.db import transaction, IntegrityError
from django.db.models import Q, F
from django.http import Http404
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from rest_framework import mixins, viewsets
from rest_framework.decorators import api_view
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.response import Response
from inventory.models import Site, Equipment, History, DOI, Photo, Document, FieldNote
from .models import Visit, Task, TaskActivity, VisitObservation, Deployment, ConfigurationVersion, DataCaveat, Attachment, ChecklistTemplate, TeamMember
from .permissions import accessible_sites, require_site, require_role, role_for, display_name
from .serializers import SiteSerializer, EquipmentSerializer, HistorySerializer, DOISerializer, TaskSerializer, VisitSerializer, TaskActivitySerializer, VisitObservationSerializer, DeploymentSerializer, ConfigurationSerializer, CaveatSerializer, AttachmentSerializer, ChecklistSerializer
from .services import apply_operation, audit, check_version, Conflict

def all_team(user):
    require_role(user, "viewer", "member", "researcher", "manager", "admin")

def legacy_attachments(site, equipment):
    output = []
    equipment_ids = set(equipment.values_list("pk", flat=True))
    for p in Photo.objects.filter(fieldnote__site=site).select_related("fieldnote"):
        visit = getattr(p.fieldnote, "hub_visit", None)
        output.append({"id": f"photo-{p.pk}", "filename": Path(p.photo.name).name, "caption": f"Photo · {p.fieldnote.date_visited}", "content_type": "image/jpeg", "visit": str(visit.pk) if visit else None, "equipment": None, "caveat": None, "configuration": None, "url": f"/legacy-attachments/photo/{p.pk}/", "legacy": True})
    for d in Document.objects.select_related("content_type").all():
        obj = d.content_object
        obj_site = obj.pk if isinstance(obj, Site) else getattr(obj, "site_id", None)
        if obj_site == site.pk or (isinstance(obj, Equipment) and obj.pk in equipment_ids):
            visit = getattr(obj, "hub_visit", None) if isinstance(obj, FieldNote) else None
            output.append({"id": f"document-{d.pk}", "filename": Path(d.file.name).name, "caption": d.summary, "content_type": "application/octet-stream", "visit": str(visit.pk) if visit else None, "equipment": obj.pk if isinstance(obj, Equipment) else None, "caveat": None, "configuration": None, "url": f"/legacy-attachments/document/{d.pk}/", "legacy": True})
    return output

@api_view(["GET"])
def bootstrap(request):
    all_team(request.user)
    sites = accessible_sites(request.user).order_by("code")
    from .resources_api import ProtocolSerializer
    from .models import Protocol
    return Response({"me": {"id": request.user.pk, "username": request.user.username, "name": display_name(request.user), "email": request.user.email, "role": role_for(request.user), "can_edit_shared_references": request.user.is_superuser or not request.user.team_member.sites.exists()}, "sites": SiteSerializer(sites, many=True).data, "protocols": ProtocolSerializer(Protocol.objects.filter(is_archived=False), many=True).data, "checklists": ChecklistSerializer(ChecklistTemplate.objects.filter(is_active=True), many=True).data, "server_time": timezone.now(), "public_reference_enabled": settings.PUBLIC_FIELDNOTES_ENABLED})

@api_view(["GET"])
def snapshot(request):
    all_team(request.user)
    site = require_site(request.user, request.query_params.get("site"))
    visits = site.visits.select_related("site").prefetch_related("reports").all()
    equipment = Equipment.objects.filter(Q(site__in=accessible_sites(request.user)) | Q(site__isnull=True)).order_by("instrument", "serial_number")
    attachments = Attachment.objects.filter(Q(site=site) | Q(equipment__in=equipment, site__in=accessible_sites(request.user))).distinct()
    caveats = DataCaveat.objects.filter(sites=site).prefetch_related("sites", "configurations").distinct()
    from .processing_files import library_state
    from .record_resources import CalibrationSerializer, knowledge_state
    from .resources_api import resource_state
    return Response({"calibrations": CalibrationSerializer(site.calibrations.all(), many=True).data, "knowledge": knowledge_state(request.user), "processing_files": library_state(request.user), "resources": resource_state(site), "site": SiteSerializer(site).data, "tasks": TaskSerializer(site.tasks.all(), many=True).data, "visits": VisitSerializer(visits, many=True).data, "activities": TaskActivitySerializer(TaskActivity.objects.filter(task__site=site), many=True).data, "observations": VisitObservationSerializer(VisitObservation.objects.filter(visit__site=site), many=True).data, "equipment": EquipmentSerializer(equipment, many=True).data, "equipment_history": HistorySerializer(History.objects.filter(item__in=equipment), many=True).data, "deployments": DeploymentSerializer(site.deployments.all(), many=True).data, "configurations": ConfigurationSerializer(site.configurations.all(), many=True).data, "caveats": CaveatSerializer(caveats, many=True).data, "attachments": AttachmentSerializer(attachments, many=True).data + legacy_attachments(site, equipment), "dois": DOISerializer(site.doi_records.all(), many=True).data, "server_time": timezone.now()})

@api_view(["POST"])
def sync(request):
    operations = request.data.get("operations")
    if not isinstance(operations, list) or not 1 <= len(operations) <= 100:
        raise ValidationError("Send between 1 and 100 operations.")
    results = []
    for operation in operations:
        try:
            results.append(apply_operation(request.user, operation))
        except APIException as exc:
            results.append({"id": operation.get("id") if isinstance(operation, dict) else None, "ok": False, "status": exc.status_code, "error": exc.detail})
            break  # Keep dependent operations queued until this one is resolved.
        except (ModelValidationError, ValueError, TypeError) as exc:
            results.append({"id": operation.get("id"), "ok": False, "status": 400, "error": str(exc)})
            break
    return Response({"results": results})

class ScopedViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    write_roles = ("researcher", "manager", "admin")
    def validate_scope(self, data, instance=None):
        site = data.get("site", getattr(instance, "site", None))
        if site:
            require_site(self.request.user, site.pk, writable=True)
        return site
    def get_queryset(self):
        all_team(self.request.user)
        qs = super().get_queryset()
        if self.action in {"update", "partial_update"}:
            qs = qs.select_for_update()
        return qs
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        require_role(request.user, *self.write_roles)
        return super().create(request, *args, **kwargs)
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        require_role(request.user, *self.write_roles)
        return super().update(request, *args, **kwargs)
    def save_validated(self, serializer, **kwargs):
        obj = serializer.save(**kwargs)
        try:
            obj.full_clean()
        except ModelValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        return obj
    def perform_create(self, serializer):
        site = self.validate_scope(serializer.validated_data)
        obj = self.save_validated(serializer)
        audit(self.request.user, "created", obj, site)
    def perform_update(self, serializer):
        site = self.validate_scope(serializer.validated_data, serializer.instance)
        version = getattr(serializer.instance, "version", None)
        if version is not None:
            check_version(serializer.instance, self.request.data.get("base_version"))
        before = dict(serializer.__class__(serializer.instance).data)
        kwargs = {"version": version + 1} if version is not None else {}
        obj = self.save_validated(serializer, **kwargs)
        audit(self.request.user, "updated", obj, site, {"before": json.loads(json.dumps(before, default=str))})

class SiteViewSet(ScopedViewSet):
    queryset = Site.objects.all()
    serializer_class = SiteSerializer
    write_roles = ("admin",)
    def get_queryset(self):
        return super().get_queryset().filter(pk__in=accessible_sites(self.request.user))
    def validate_scope(self, data, instance=None):
        # Editing an archived site is how an administrator restores it.
        return require_site(self.request.user, instance.pk) if instance else None

class EquipmentViewSet(ScopedViewSet):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    def get_queryset(self):
        return super().get_queryset().filter(Q(site__in=accessible_sites(self.request.user)) | Q(site__isnull=True))
    def validate_scope(self, data, instance=None):
        site = super().validate_scope(data, instance)
        if instance and "site" in data and (data["site"].pk if data["site"] else None) != instance.site_id:
            now = timezone.now()
            if instance.deployments.filter(installed_at__lte=now).filter(Q(removed_at__isnull=True) | Q(removed_at__gt=now)).exists():
                raise ValidationError("Record the current deployment's removal before moving this instrument.")
        return site

class DeploymentViewSet(ScopedViewSet):
    queryset = Deployment.objects.all()
    serializer_class = DeploymentSerializer
    def get_queryset(self):
        return super().get_queryset().filter(site__in=accessible_sites(self.request.user))
    def validate_scope(self, data, instance=None):
        site = super().validate_scope(data, instance)
        equipment = data.get("equipment", getattr(instance, "equipment", None))
        if not site or not equipment:
            raise ValidationError("Site and equipment are required.")
        if instance and (instance.equipment_id != equipment.pk or instance.site_id != site.pk):
            raise ValidationError("A deployment's site and instrument cannot be changed. Record removal, then create a new deployment.")
        Equipment.objects.select_for_update().get(pk=equipment.pk)
        if equipment.site_id and equipment.site_id not in accessible_sites(self.request.user).values_list("id", flat=True):
            raise PermissionDenied("You do not have access to this instrument.")
        return site
    def update_current_site(self, obj):
        now = timezone.now()
        current = Deployment.objects.filter(equipment=obj.equipment, installed_at__lte=now).filter(Q(removed_at__isnull=True) | Q(removed_at__gt=now)).order_by("-installed_at").first()
        Equipment.objects.filter(pk=obj.equipment_id).update(site=current.site if current else None, status="deployed" if current else "available", version=F("version") + 1)
    def perform_create(self, serializer):
        super().perform_create(serializer)
        self.update_current_site(serializer.instance)
    def perform_update(self, serializer):
        super().perform_update(serializer)
        self.update_current_site(serializer.instance)

class ConfigurationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = ConfigurationVersion.objects.all()
    serializer_class = ConfigurationSerializer
    def get_queryset(self):
        all_team(self.request.user)
        return self.queryset.filter(site__in=accessible_sites(self.request.user))
    @transaction.atomic
    def perform_create(self, serializer):
        require_role(self.request.user, "researcher", "manager", "admin")
        site = require_site(self.request.user, serializer.validated_data["site"].pk, writable=True)
        old = serializer.validated_data.get("supersedes")
        if old and old.site_id != site.pk:
            raise ValidationError("The replaced configuration must belong to this site.")
        obj = serializer.save(created_by=self.request.user)
        try:
            obj.full_clean()
        except ModelValidationError as exc:
            raise ValidationError(exc.messages)
        audit(self.request.user, "configuration.created", obj, site)

class CaveatViewSet(ScopedViewSet):
    queryset = DataCaveat.objects.prefetch_related("sites", "configurations")
    serializer_class = CaveatSerializer
    def save_validated(self, serializer, **kwargs):
        previous = serializer.instance.status if serializer.instance else "draft"
        status = serializer.validated_data.get("status", previous)
        now = timezone.now()
        if status == "draft":
            kwargs.update(reviewed_at=None, resolved_at=None)
        else:
            if previous == "draft":
                kwargs["reviewed_at"] = now
            if status == "resolved" and previous != "resolved":
                kwargs["resolved_at"] = now
            elif status != "resolved":
                kwargs["resolved_at"] = None
        return super().save_validated(serializer, **kwargs)
    def get_queryset(self):
        allowed = DataCaveat.objects.filter(sites__in=accessible_sites(self.request.user)).values("pk")
        return super().get_queryset().filter(pk__in=allowed)
    def validate_scope(self, data, instance=None):
        sites = data.get("sites", list(instance.sites.all()) if instance else [])
        if not sites:
            raise ValidationError("Select at least one affected site.")
        for site in sites:
            require_site(self.request.user, site.pk, writable=True)
        # A user may not remove inaccessible sites from an existing shared caveat.
        if instance:
            for site in instance.sites.all():
                require_site(self.request.user, site.pk)
        visit = data.get("source_visit", getattr(instance, "source_visit", None))
        if visit and visit.site_id not in [s.pk for s in sites]:
            raise ValidationError("The source visit must belong to an affected site.")
        equipment = data.get("equipment", getattr(instance, "equipment", None))
        if equipment and equipment.site_id:
            require_site(self.request.user, equipment.site_id)
        for config in data.get("configurations", []):
            if config.site_id not in [s.pk for s in sites]:
                raise ValidationError("Linked configurations must belong to affected sites.")
        return sites[0]
    def perform_create(self, serializer):
        site = self.validate_scope(serializer.validated_data)
        obj = self.save_validated(serializer, created_by=self.request.user)
        audit(self.request.user, "caveat.created", obj, site)

class DOIViewSet(ScopedViewSet):
    queryset = DOI.objects.all()
    serializer_class = DOISerializer
    def get_queryset(self):
        return super().get_queryset().filter(site__in=accessible_sites(self.request.user))

class HistoryViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = History.objects.all()
    serializer_class = HistorySerializer
    def get_queryset(self):
        all_team(self.request.user)
        return self.queryset.filter(Q(item__site__in=accessible_sites(self.request.user)) | Q(item__site__isnull=True))
    @transaction.atomic
    def perform_create(self, serializer):
        require_role(self.request.user, "member", "researcher", "manager", "admin")
        item = serializer.validated_data["item"]
        if item.site_id:
            require_site(self.request.user, item.site_id, writable=True)
        obj = serializer.save(note=f"{display_name(self.request.user)}: {serializer.validated_data['note']}")
        audit(self.request.user, "equipment.history_added", obj, item.site)

class ChecklistViewSet(ScopedViewSet):
    queryset = ChecklistTemplate.objects.all()
    serializer_class = ChecklistSerializer
    write_roles = ("admin",)

@api_view(["GET", "POST", "PATCH"])
def team(request):
    require_role(request.user, "admin")
    User = get_user_model()
    if request.method == "GET":
        return Response([{"id": u.pk, "username": u.username, "email": u.email, "name": display_name(u), "role": role_for(u), "is_active": u.is_active, "sites": list(u.team_member.sites.values_list("pk", flat=True)) if hasattr(u, "team_member") else []} for u in User.objects.all().order_by("username")])
    data = request.data
    role = data.get("role", "viewer")
    if role not in dict(TeamMember.ROLES):
        raise ValidationError("Unknown team role.")
    if not isinstance(data.get("sites", []), list):
        raise ValidationError("Allowed sites must be a list.")
    sites = [require_site(request.user, pk) for pk in data.get("sites", [])]
    with transaction.atomic():
        if request.method == "POST":
            username = str(data.get("username", "")).strip()
            if not username or User.objects.filter(username=username).exists():
                raise ValidationError("Choose an unused username.")
            user = User(username=username, email=str(data.get("email", "")), first_name=str(data.get("name", ""))[:150])
            try:
                validate_password(data.get("password", ""), user)
            except ModelValidationError as exc:
                raise ValidationError({"password": exc.messages})
            user.set_password(data["password"])
            try:
                user.full_clean()
            except ModelValidationError as exc:
                raise ValidationError(exc.message_dict)
            user.save()
        else:
            try:
                user = User.objects.select_for_update().filter(pk=data.get("id")).first()
            except (ValueError, TypeError):
                raise ValidationError("Invalid user identifier.")
            if not user:
                raise ValidationError("Unknown user.")
            if user.is_superuser or user.pk == request.user.pk:
                raise ValidationError("Use Django administration to modify a superuser or your own access.")
            if "is_active" in data and not isinstance(data["is_active"], bool):
                raise ValidationError("Account activity must be true or false.")
            user.is_active = data.get("is_active", user.is_active)
            user.save(update_fields=["is_active"])
            if data.get("password"):
                try:
                    validate_password(data["password"], user)
                except ModelValidationError as exc:
                    raise ValidationError({"password": exc.messages})
                user.set_password(data["password"])
                user.save(update_fields=["password"])
        member, _ = TeamMember.objects.get_or_create(user=user)
        member.role = role
        member.save()
        member.sites.set(sites)
        audit(request.user, "team.updated", member, detail={"user_id": user.pk, "role": role, "is_active": user.is_active})
    return Response({"id": user.pk, "role": role})

@api_view(["POST"])
def upload_attachment(request):
    require_role(request.user, "member", "researcher", "manager", "admin")
    site = require_site(request.user, request.data.get("site"), writable=True)
    from .services import entity_uuid
    attachment_id = entity_uuid(request.data.get("id"))
    file = request.FILES.get("file")
    if not file:
        raise ValidationError("Select a file to upload.")
    if file.size > settings.MAX_UPLOAD_BYTES:
        raise ValidationError(f"Maximum upload size is {settings.MAX_UPLOAD_BYTES // 1024 // 1024} MB.")
    digest = hashlib.sha256()
    for chunk in file.chunks():
        digest.update(chunk)
    file.seek(0)
    sha = digest.hexdigest()
    linked = {}
    from .models import CalibrationLog
    targets = [("calibration", CalibrationLog), ("visit", Visit), ("task", Task), ("activity", TaskActivity), ("observation", VisitObservation), ("equipment", Equipment), ("caveat", DataCaveat), ("configuration", ConfigurationVersion)]
    for field, model in targets:
        value = request.data.get(field)
        if not value:
            continue
        try:
            obj = model.objects.filter(pk=value).first()
        except (ModelValidationError, ValueError, TypeError):
            raise ValidationError(f"Invalid {field} identifier.")
        if not obj:
            raise ValidationError(f"Unknown {field}.")
        if field == "caveat":
            if not obj.sites.filter(pk=site.pk).exists():
                raise PermissionDenied("The caveat is not linked to this site.")
        else:
            target_site = obj.task.site_id if field == "activity" else obj.visit.site_id if field == "observation" else obj.site_id
            if target_site != site.pk and not (field == "equipment" and target_site is None):
                raise PermissionDenied("The attachment target is not linked to this site.")
        linked[field] = obj
    def associate(field, obj):
        if obj is None:
            return
        if field in linked and linked[field].pk != obj.pk:
            raise ValidationError("The selected note, task and visit do not belong together.")
        linked[field] = obj
    if "activity" in linked:
        if "visit" in linked and linked["activity"].visit_id != linked["visit"].pk:
            raise ValidationError("This activity was not recorded during the selected visit.")
        associate("task", linked["activity"].task)
        associate("visit", linked["activity"].visit)
    if "observation" in linked:
        associate("visit", linked["observation"].visit)
    if "activity" in linked and "observation" in linked:
        raise ValidationError("Attach a file to one individual note at a time.")
    if 'calibration' in linked:
        if set(linked) != {'calibration'}:
            raise ValidationError('Attach a calibration file to its calibration log entry only.')
        if linked['calibration'].is_archived:
            raise ValidationError('Restore the calibration log before adding files.')
    content_type = "application/octet-stream"
    if file.name.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
        try:
            with Image.open(file) as img:
                img.verify()
                content_type = Image.MIME.get(img.format, "application/octet-stream")
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise ValidationError("This file is not a valid supported image.")
        file.seek(0)
    elif file.name.lower().endswith(".pdf"):
        if file.read(5) != b"%PDF-":
            raise ValidationError("This file is not a valid PDF.")
        content_type = "application/pdf"
        file.seek(0)
    elif file.name.lower().endswith((".mp4", ".m4v", ".mov", ".webm", ".mp3", ".wav", ".ogg", ".flac", ".m4a")):
        import mimetypes
        content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
    with transaction.atomic():
        request.user.__class__.objects.select_for_update().get(pk=request.user.pk)
        previous = Attachment.objects.filter(pk=attachment_id).first()
        if previous:
            if previous.site_id != site.pk or previous.sha256 != sha or previous.uploaded_by_id != request.user.pk or any(getattr(previous, field + "_id") != (linked[field].pk if field in linked else None) for field, _ in targets):
                raise Conflict("This upload identifier already belongs to another file or record.")
            return Response(AttachmentSerializer(previous).data)
        obj = Attachment(id=attachment_id, site=site, file=file, filename=Path(file.name).name[:250], caption=str(request.data.get("caption", ""))[:500], content_type=content_type, sha256=sha, size=file.size, uploaded_by=request.user, **linked)
        obj.save()
        audit(request.user, "attachment.uploaded", obj, site)
    return Response(AttachmentSerializer(obj).data, status=201)

@api_view(["GET"])
def overview(request):
    all_team(request.user)
    output = []
    from .resources_api import condition_data
    for s in accessible_sites(request.user).order_by("code"):
        last = s.visits.order_by("-date").first()
        caveat_ids = list(s.caveats.exclude(status="resolved").values_list("pk", flat=True))
        output.append({"id": s.pk, "code": s.code, "name": s.name, "condition": condition_data(s), "archived": s.is_archived, "pending": s.tasks.filter(status="pending").count(), "high_priority": s.tasks.filter(status="pending", priority="high").count(), "open_visits": s.visits.filter(status="open").count(), "visits": s.visits.count(), "caveats": len(caveat_ids), "caveat_ids": caveat_ids, "last_visit": last.date if last else None})
    return Response(output)
