import time
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from inventory.models import Site
from hub.monitor import collect
from hub.models import TowerReading


class Command(BaseCommand):
    help = "Read tower diagnostics using only fixed LI-COR queries; no instrument writes."
    def add_arguments(self, parser):
        parser.add_argument("--watch",action="store_true")
        parser.add_argument("--interval",type=int,default=60)
    def handle(self,*args,**options):
        try:
            while True:
                collect(list(Site.objects.filter(is_archived=False).order_by("code")))
                TowerReading.objects.filter(observed_at__lt=timezone.now()-timedelta(days=7)).delete()
                self.stdout.write("Tower check complete. No instrument settings changed.")
                if not options["watch"]:
                    break
                time.sleep(max(30,options["interval"]))
        except KeyboardInterrupt:
            self.stdout.write("Tower monitoring stopped.")
