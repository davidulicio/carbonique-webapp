"""Versioned scientific INI documents. Source text is stored, never executed."""
import hashlib
import json
import re
from pathlib import PurePosixPath

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from inventory.models import Site
from .models import ProcessingFile, ProcessingFileVersion
from .permissions import accessible_sites, require_role, require_site, role_for
from .services import audit


def canonical_path(value):
    value = str(value).replace('\\', '/')
    parts = value.split('/')
    if parts and parts[0].lower() == 'traceanalysis_ini':
        parts.pop(0)
    if not parts or any(part in {'', '.', '..'} or not re.fullmatch(r'[\w .-]+', part) for part in parts):
        raise ValidationError('Use a relative INI filename without parent-directory or drive paths.')
    if not parts[-1].lower().endswith('.ini') or len('/'.join(parts)) > 250:
        raise ValidationError('Only .ini files with paths of at most 250 characters are accepted.')
    match = re.match(r'^(UQAM_\d+|MCGILL_\d+)(?:_|\.|$)', parts[-1], re.I)
    code = match[1].upper() if match else ''
    if len(parts) == 1 and code:
        parts.insert(0, code)
    if code and parts[0].upper() == code:
        parts[0] = code
    return '/'.join(parts), code


def decoded(data):
    if b'\x00' in data:
        raise ValidationError('The selected INI file contains binary data.')
    try:
        return data.decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            return data.decode('cp1252')
        except UnicodeDecodeError:
            raise ValidationError('Use an INI text file encoded as UTF-8 or Windows-1252.')


def unrestricted(user):
    return user.is_superuser or not user.team_member.sites.exists()


def visible_files(user):
    require_role(user, 'viewer', 'member', 'researcher', 'manager', 'admin')
    query = ProcessingFile.objects.all()
    if not unrestricted(user):
        query = query.filter(Q(site__in=accessible_sites(user)) | Q(site_code=''))
    return query


def validate_write(user, path, code):
    site = Site.objects.filter(code__iexact=code).first() if code else None
    if user:
        require_role(user, 'researcher', 'manager', 'admin')
        if site:
            require_site(user, site.pk, writable=True)
        elif not unrestricted(user):
            raise PermissionDenied('Only a user with network-wide access may update shared or unassigned INI files.')
    return site


def store_version(path, data, user=None, note='', source_modified_at=None, created_files=None):
    path, code = canonical_path(path)
    decoded(data)
    site = validate_write(user, path, code)
    document, _ = ProcessingFile.objects.get_or_create(path=path, defaults={'site':site, 'site_code':code})
    document = ProcessingFile.objects.select_for_update().get(pk=document.pk)
    latest = document.revisions.order_by('-revision').first()
    digest = hashlib.sha256(data).hexdigest()
    if latest and latest.sha256 == digest:
        return latest, False
    version = ProcessingFileVersion(document=document, revision=(latest.revision+1 if latest else 1),
        sha256=digest, size=len(data), note=str(note)[:500], uploaded_by=user, source_modified_at=source_modified_at)
    version.file.save(PurePosixPath(path).name, ContentFile(data), save=True)
    if created_files is not None:
        created_files.append((version.file.storage, version.file.name))
    if user:
        audit(user, 'processing_file.uploaded', version, site, {'path':path, 'revision':version.revision})
    return version, True


def library_state(user):
    output=[]
    for document in visible_files(user).prefetch_related('revisions__uploaded_by'):
        versions=[{'id':str(version.pk), 'revision':version.revision, 'sha256':version.sha256,
            'size':version.size, 'note':version.note, 'uploaded_at':version.uploaded_at.isoformat(),
            'source_modified_at':version.source_modified_at.isoformat() if version.source_modified_at else None,
            'url':f'/processing-files/{version.pk}/'} for version in document.revisions.all()]
        output.append({'id':str(document.pk), 'path':document.path, 'site':document.site_id,
            'site_code':document.site_code, 'latest':versions[0] if versions else None, 'versions':versions})
    return output


@api_view(['GET', 'POST'])
def library(request):
    if request.method == 'GET':
        return Response({'files':library_state(request.user)})
    require_role(request.user, 'researcher', 'manager', 'admin')
    uploads=request.FILES.getlist('files')
    if not 1 <= len(uploads) <= 100:
        raise ValidationError('Select between 1 and 100 INI files.')
    try:
        paths=json.loads(request.data.get('paths', 'null'))
    except (ValueError, TypeError):
        raise ValidationError('The file path list is invalid.')
    if paths is not None and (not isinstance(paths,list) or len(paths)!=len(uploads) or not all(isinstance(path,str) for path in paths)):
        raise ValidationError('Provide one relative path per selected file.')
    prepared=[];seen=set();total=0
    for index, upload in enumerate(uploads):
        path,code=canonical_path(paths[index] if paths is not None else upload.name)
        if path.casefold() in seen:
            raise ValidationError('The selection contains the same file path more than once.')
        seen.add(path.casefold())
        if upload.size>5*1024*1024:
            raise ValidationError('Each INI file must be at most 5 MiB.')
        total+=upload.size
        if total>25*1024*1024:
            raise ValidationError('A batch must be at most 25 MiB in total.')
        data=upload.read();decoded(data);validate_write(request.user,path,code)
        existing=ProcessingFile.objects.filter(path__iexact=path).first()
        prepared.append((existing.path if existing else path,data))
    created=[];count=0
    try:
        with transaction.atomic():
            for path,data in prepared:
                _,added=store_version(path,data,request.user,request.data.get('note',''),created_files=created)
                count+=added
    except Exception:
        for storage,name in created:
            storage.delete(name)
        raise
    return Response({'files':library_state(request.user),'created':count,'unchanged':len(prepared)-count})


@api_view(['GET'])
def version_file(request, pk):
    version=ProcessingFileVersion.objects.select_related('document').filter(pk=pk,document__in=visible_files(request.user)).first()
    if not version:
        raise Http404()
    try:
        handle=version.file.open('rb')
    except (OSError, ValueError):
        raise Http404('The INI file is missing from storage.')
    if request.query_params.get('preview') == '1':
        with handle:
            text=decoded(handle.read())
        response=Response({'path':version.document.path,'revision':version.revision,'text':text})
    else:
        response=FileResponse(handle,as_attachment=True,filename=PurePosixPath(version.document.path).name,content_type='application/octet-stream')
        response['X-Content-Type-Options']='nosniff'
    response['Cache-Control']='private, no-store'
    return response
