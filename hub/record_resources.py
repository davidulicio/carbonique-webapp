"""Site calibration records and protected technical knowledge resources."""
import hashlib
import json
import io
from pathlib import Path
from urllib.parse import urlsplit
from django.conf import settings
from django.core.exceptions import ValidationError as ModelValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from .models import CalibrationLog, KnowledgeEntry, KnowledgeFile
from .permissions import accessible_sites, require_role, require_site
from .services import audit, check_version, Conflict
from .views import file_response

READ_ROLES = ('viewer', 'member', 'researcher', 'manager', 'admin')
WRITE_ROLES = ('member', 'researcher', 'manager', 'admin')


class CalibrationSerializer(serializers.ModelSerializer):
    event_label = serializers.CharField(source='get_event_type_display', read_only=True)
    preparation_label = serializers.CharField(source='get_preparation_display', read_only=True)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=20000)
    class Meta:
        model = CalibrationLog
        fields = '__all__'
        read_only_fields = ['id', 'site', 'created_by', 'updated_by', 'created_at', 'updated_at', 'version']
    def validate(self, attrs):
        user = self.context['user']
        for key in ['equipment', 'replacement_equipment']:
            equipment = attrs.get(key)
            if self.instance and equipment and equipment.pk == getattr(self.instance, key + '_id', None):
                continue
            if equipment and equipment.site_id:
                require_site(user, equipment.site_id)
        return attrs


@transaction.atomic
def save_calibration(user, site, pk, payload, *, create=False, base_version=None):
    require_role(user, *WRITE_ROLES)
    require_site(user, site.pk, writable=True)
    current = CalibrationLog.objects.select_for_update().filter(pk=pk).first()
    if create and current:
        raise Conflict('A calibration log already uses this identifier.')
    if not create and (not current or current.site_id != site.pk):
        raise PermissionDenied('The calibration record is not available for this site.')
    if current:
        check_version(current, base_version)
    serializer = CalibrationSerializer(current, data=payload, partial=not create, context={'user': user})
    serializer.is_valid(raise_exception=True)
    visit = serializer.validated_data.get('source_visit', getattr(current, 'source_visit', None))
    if visit and visit.site_id != site.pk:
        raise ValidationError({'source_visit': 'The linked visit must belong to this site.'})
    before = json.loads(json.dumps(CalibrationSerializer(current).data, cls=DjangoJSONEncoder)) if current else None
    kwargs = {'site': site, 'updated_by': user, 'version': current.version+1 if current else 1}
    if create:
        kwargs.update(id=pk, created_by=user)
    obj = serializer.save(**kwargs)
    try:
        obj.full_clean()
    except ModelValidationError as exc:
        raise ValidationError(exc.message_dict)
    audit(user, 'calibration.created' if create else 'calibration.updated', obj, site, {'before': before} if before else {})
    return obj


@api_view(['GET', 'POST', 'PATCH'])
def calibrations(request, site_id, pk=None):
    import uuid
    require_role(request.user, *READ_ROLES)
    site = require_site(request.user, site_id, writable=request.method != 'GET')
    if request.method == 'GET':
        queryset = site.calibrations.all()
        if pk:
            obj = queryset.filter(pk=pk).first()
            if not obj: raise Http404()
            return Response(CalibrationSerializer(obj).data)
        return Response({'calibrations': CalibrationSerializer(queryset, many=True).data})
    if request.method == 'PATCH' and not pk:
        raise ValidationError('Select the calibration record to update.')
    if request.method == 'POST' and pk:
        raise ValidationError('Create a new calibration using the site log URL.')
    obj = save_calibration(request.user, site, pk or uuid.uuid4(), request.data,
        create=request.method == 'POST', base_version=request.data.get('base_version'))
    return Response(CalibrationSerializer(obj).data, status=201 if request.method == 'POST' else 200)


def unrestricted(user):
    return user.is_superuser or not user.team_member.sites.exists()


def visible_knowledge(user):
    require_role(user, *READ_ROLES)
    return KnowledgeEntry.objects.filter(Q(site__in=accessible_sites(user)) | Q(site__isnull=True)).select_related('site').prefetch_related('files')


def writable_knowledge(user, obj):
    require_role(user, *WRITE_ROLES)
    if obj.site_id:
        require_site(user, obj.site_id, writable=True)
    elif not unrestricted(user):
        raise PermissionDenied('Network-wide access is needed to edit shared references.')


class KnowledgeFileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = KnowledgeFile
        exclude = ['file']
    def get_url(self, obj):
        return f'/knowledge-files/{obj.pk}/'


class KnowledgeSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source='get_category_display', read_only=True)
    site_code = serializers.SerializerMethodField()
    files = KnowledgeFileSerializer(many=True, read_only=True)
    body = serializers.CharField(required=False, allow_blank=True, max_length=50000)
    class Meta:
        model = KnowledgeEntry
        fields = '__all__'
        read_only_fields = ['id', 'created_by', 'updated_by', 'created_at', 'updated_at', 'version']
    def get_site_code(self, obj):
        return obj.site.code if obj.site_id else ''
    def validate_external_url(self, value):
        if value:
            try: parsed = urlsplit(value)
            except ValueError: raise ValidationError('Use a complete HTTP or HTTPS sharing link.')
            if parsed.scheme.lower() not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
                raise ValidationError('Use an HTTP or HTTPS link without embedded credentials. For OneNote, paste its web sharing link.')
        return value


def knowledge_state(user):
    return KnowledgeSerializer(visible_knowledge(user), many=True).data


@api_view(['GET', 'POST', 'PATCH'])
@transaction.atomic
def knowledge(request, pk=None):
    queryset = visible_knowledge(request.user)
    if request.method == 'GET':
        if pk:
            obj = queryset.filter(pk=pk).first()
            if not obj: raise Http404()
            return Response(KnowledgeSerializer(obj).data)
        return Response({'entries': KnowledgeSerializer(queryset, many=True).data})
    require_role(request.user, *WRITE_ROLES)
    if request.method == 'PATCH' and not pk: raise ValidationError('Select a reference to update.')
    if request.method == 'POST' and pk: raise ValidationError('Use the reference library URL to add an entry.')
    obj = queryset.select_related(None).select_for_update().filter(pk=pk).first() if pk else None
    if pk and not obj: raise Http404()
    if obj:
        writable_knowledge(request.user, obj)
        check_version(obj, request.data.get('base_version'))
    serializer = KnowledgeSerializer(obj, data=request.data, partial=bool(obj))
    serializer.is_valid(raise_exception=True)
    target_site = serializer.validated_data.get('site', obj.site if obj else None)
    writable_knowledge(request.user, KnowledgeEntry(site=target_site))
    before = json.loads(json.dumps(KnowledgeSerializer(obj).data, cls=DjangoJSONEncoder)) if obj else None
    kwargs = {'updated_by': request.user, 'version': obj.version+1 if obj else 1}
    if not obj: kwargs['created_by'] = request.user
    saved = serializer.save(**kwargs)
    try: saved.full_clean()
    except ModelValidationError as exc: raise ValidationError(exc.message_dict)
    audit(request.user, 'knowledge.updated' if obj else 'knowledge.created', saved, target_site, {'before': before} if before else {})
    return Response(KnowledgeSerializer(saved).data, status=200 if obj else 201)


def upload_type(data, filename):
    suffix = Path(filename).suffix.lower()
    if suffix in {'.png', '.jpg', '.jpeg', '.gif', '.webp'}:
        try:
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
                return Image.MIME.get(image.format, 'application/octet-stream')
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise ValidationError('The selected image is invalid.')
    if suffix == '.pdf':
        if not data.startswith(b'%PDF-'): raise ValidationError('The selected PDF is invalid.')
        return 'application/pdf'
    return 'application/octet-stream'


@api_view(['POST', 'PATCH'])
def knowledge_files(request, pk, file_id=None):
    entry = visible_knowledge(request.user).filter(pk=pk).first()
    if not entry: raise Http404()
    writable_knowledge(request.user, entry)
    if request.method == 'PATCH':
        with transaction.atomic():
            entry = KnowledgeEntry.objects.select_for_update().get(pk=entry.pk)
            writable_knowledge(request.user, entry)
            item = entry.files.select_for_update().filter(pk=file_id).first()
            if not item: raise Http404()
            check_version(item, request.data.get('base_version'))
            archived = request.data.get('is_archived')
            if not isinstance(archived, bool): raise ValidationError('Set archive status to true or false.')
            item.is_archived = archived; item.version += 1; item.save(update_fields=['is_archived', 'version'])
            audit(request.user, 'knowledge.file_archived' if archived else 'knowledge.file_restored', item, entry.site)
        return Response(KnowledgeFileSerializer(item).data)
    if file_id: raise ValidationError('Upload files using the reference entry file URL.')
    if entry.is_archived: raise ValidationError('Restore this reference before adding files.')
    uploads = request.FILES.getlist('files')
    if not 1 <= len(uploads) <= 10: raise ValidationError('Select between 1 and 10 files.')
    if any(upload.size > settings.MAX_UPLOAD_BYTES for upload in uploads) or sum(upload.size for upload in uploads) > settings.MAX_UPLOAD_BYTES:
        raise ValidationError(f'The selected files must total at most {settings.MAX_UPLOAD_BYTES // 1024 // 1024} MiB.')
    prepared = []
    for upload in uploads:
        data = upload.read()
        prepared.append((Path(upload.name).name[:250], data, upload_type(data, upload.name), hashlib.sha256(data).hexdigest()))
    stored = []; added = 0
    try:
        with transaction.atomic():
            entry = KnowledgeEntry.objects.select_for_update().get(pk=entry.pk)
            writable_knowledge(request.user, entry)
            if entry.is_archived: raise ValidationError('Restore this reference before adding files.')
            for filename, data, content_type, digest in prepared:
                if entry.files.filter(sha256=digest, is_archived=False).exists(): continue
                obj = KnowledgeFile(entry=entry, filename=filename, content_type=content_type, sha256=digest, size=len(data), uploaded_by=request.user)
                storage = obj.file.storage
                name = storage.save(obj.file.field.generate_filename(obj, filename), ContentFile(data))
                stored.append((storage, name)); obj.file.name = name; obj.save(); added += 1
                audit(request.user, 'knowledge.file_uploaded', obj, entry.site)
    except Exception:
        for storage, name in stored: storage.delete(name)
        raise
    return Response({'added': added, 'unchanged': len(prepared)-added, 'entry': KnowledgeSerializer(visible_knowledge(request.user).get(pk=entry.pk)).data})


@api_view(['GET', 'HEAD'])
def knowledge_download(request, pk):
    item = KnowledgeFile.objects.filter(pk=pk, entry__in=visible_knowledge(request.user)).first()
    if not item: raise Http404()
    inline = item.content_type.startswith('image/')
    return file_response(item.file, item.filename, item.content_type, inline=inline)
