from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from inventory.models import Site
from inventory.site_names import SITE_NAMES


class Command(BaseCommand):
    help = "Apply the six approved project display names, for example after restoring an older backup."

    @transaction.atomic
    def handle(self, *args, **options):
        count = 0
        for code, name in SITE_NAMES.items():
            count += Site.objects.filter(code__iexact=code).exclude(name=name).update(
                name=name, version=F('version') + 1, updated_at=timezone.now()
            )
        self.stdout.write(self.style.SUCCESS(f"Updated {count} site names. Site codes and linked records were preserved."))
