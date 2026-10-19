from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.db.models.functions import Lower
from inventory.models import Site
from hub.models import ChecklistTemplate, TeamMember

class Command(BaseCommand):
    help = "Set up maintenance checklists and link legacy notes. Does not create passwords or overwrite existing sites."
    def add_arguments(self, parser):
        parser.add_argument("--with-reference", action="store_true", help="Import the bundled Field Notes reference and historical summaries.")
        parser.add_argument("--grant-existing-users", choices=["viewer", "member", "researcher"], help="Assign this role only to existing users without a team profile.")
    def handle(self, *args, **options):
        duplicates = list(Site.objects.annotate(canonical_code=Lower("code")).values("canonical_code").annotate(n=Count("id")).filter(n__gt=1))
        if duplicates:
            raise CommandError(f"Resolve duplicate site codes before setup: {duplicates}")
        defaults = [
            ("Routine eddy covariance maintenance", [{"title": "Inspect tower, guy wires and access", "details": "Record any damage or unsafe condition before climbing.", "priority": "high"}, {"title": "Clean LI-7700 optics", "details": "Follow the approved instrument protocol."}, {"title": "Inspect analyzer intake and flow", "details": "Record flow, filter condition and any changes."}, {"title": "Check power and communications", "details": "Record battery voltage, charging status and connectivity."}, {"title": "Check data recording and clock", "details": "Logger time stays in fixed EST (UTC−05:00)."}, {"title": "Photograph instruments and site conditions"}]),
            ("Winter preparation", [{"title": "Record removal of water sensors", "details": "Close their deployments and flag the affected data periods."}, {"title": "Inspect winter power supply"}, {"title": "Document seasonal changes and access"}]),
        ]
        for name, tasks in defaults:
            ChecklistTemplate.objects.get_or_create(name=name, defaults={"tasks": tasks})
        if options["grant_existing_users"]:
            for user in get_user_model().objects.filter(team_member__isnull=True, is_superuser=False):
                TeamMember.objects.create(user=user, role=options["grant_existing_users"])
        call_command("backfill_visits")
        if options["with_reference"]:
            call_command("import_resources")
        self.stdout.write(self.style.SUCCESS("Carbonique Hub setup complete. Create a superuser with createsuperuser if needed."))
