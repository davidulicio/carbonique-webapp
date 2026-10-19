import json
import tempfile
import zipfile
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from inventory.models import Site

class Command(BaseCommand):
    help = "Restore a Carbonique backup into a migrated, empty database and empty media directory."
    def add_arguments(self, parser):
        parser.add_argument("--file", required=True)
    def handle(self, *args, **options):
        if Site.objects.exists() or get_user_model().objects.exists() or (settings.MEDIA_ROOT.exists() and any(settings.MEDIA_ROOT.iterdir())):
            raise CommandError("Restore only into an empty database and empty media directory. Existing records were not changed.")
        with zipfile.ZipFile(options["file"]) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            if manifest.get("format") != "carbonique-backup-v1":
                raise CommandError("Unsupported backup format.")
            members = archive.infolist()
            if sum(m.file_size for m in members) > 20 * 1024**3:
                raise CommandError("Backup exceeds the 20 GB restore limit.")
            for member in members:
                path = Path(member.filename)
                if path.is_absolute() or ".." in path.parts or "\\" in member.filename:
                    raise CommandError("Unsafe path in backup.")
            with tempfile.TemporaryDirectory() as temp:
                fixture = Path(temp)/"data.json"
                fixture.write_bytes(archive.read("data.json"))
                call_command("loaddata", str(fixture))
            for member in members:
                if member.filename.startswith("media/") and not member.is_dir():
                    destination = settings.MEDIA_ROOT / Path(member.filename).relative_to("media")
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(archive.read(member))
        self.stdout.write(self.style.SUCCESS("Backup restored. Verify records and attachments before allowing writes."))
