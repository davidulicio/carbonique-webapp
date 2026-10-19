import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from hub.processing_files import canonical_path, decoded, store_version
from hub.models import ProcessingFile


class Command(BaseCommand):
    help = 'Copy INI files into the versioned library without modifying source files or executing their contents.'
    def add_arguments(self, parser):
        parser.add_argument('--directory',default=str(settings.BASE_DIR/'seed/processing_files'))
    def handle(self, *args, **options):
        root=Path(options['directory']).resolve()
        if not root.is_dir():
            raise CommandError('The INI source directory does not exist.')
        catalogue=root/'catalogue.json'
        manifest=json.loads(catalogue.read_text(encoding='utf-8')) if catalogue.is_file() else {}
        prepared=[]
        for path in sorted(root.rglob('*')):
            if path.is_file() and path.suffix.lower()=='.ini' and not path.is_symlink():
                relative=path.relative_to(root).as_posix();canonical_path(relative)
                data=path.read_bytes();decoded(data)
                info=manifest.get(relative,{})
                if info.get('sha256') and hashlib.sha256(data).hexdigest()!=info['sha256']:
                    raise CommandError(f'The bundled source hash differs for {relative}.')
                modified=datetime.fromisoformat(info['modified_at']) if info.get('modified_at') else datetime.fromtimestamp(path.stat().st_mtime,tz=timezone.utc)
                prepared.append((relative,data,modified))
        files=[];created=0
        try:
            with transaction.atomic():
                for path,data,modified in prepared:
                    canonical,_=canonical_path(path)
                    if catalogue.is_file() and ProcessingFile.objects.filter(path__iexact=canonical,revisions__isnull=False).exists():
                        continue  # Bundled initialization never supersedes a team upload.
                    _,added=store_version(path,data,note='Imported source copy; no processing effective date inferred.',source_modified_at=modified,created_files=files)
                    created+=added
        except Exception:
            for storage,name in files:storage.delete(name)
            raise
        self.stdout.write(self.style.SUCCESS(f'INI library: {len(prepared)} source files, {created} new revisions. Source files were read only.'))
