import io
import json
import zipfile
from pathlib import Path
from datetime import datetime, timezone
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Create a portable JSON+media backup. Quiesce writers for a consistent snapshot; use native DB backups for production."
    def add_arguments(self, parser):
        parser.add_argument("--output", required=True)
    def handle(self, *args, **options):
        output = Path(options["output"]).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        if settings.MEDIA_ROOT.resolve() in output.parents:
            raise ValueError("Store backups outside MEDIA_ROOT.")
        fixture = io.StringIO()
        call_command("dumpdata", "auth.user", "auth.group", "inventory", "hub", use_natural_foreign_keys=True, use_natural_primary_keys=False, indent=2, stdout=fixture)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("data.json", fixture.getvalue())
            archive.writestr("manifest.json", json.dumps({"format": "carbonique-backup-v1", "created_at": datetime.now(timezone.utc).isoformat(), "contains_account_password_hashes": True, "requires_quiesced_writers": True}))
            if settings.MEDIA_ROOT.exists():
                for file in settings.MEDIA_ROOT.rglob("*"):
                    if file.is_file() and not file.is_symlink():
                        archive.write(file, "media/"+file.relative_to(settings.MEDIA_ROOT).as_posix())
        self.stdout.write(self.style.SUCCESS(f"Backup written to {output}. Keep it private; it contains research records and account password hashes."))
