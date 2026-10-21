from django.db import migrations
from django.db.models import F
from django.utils import timezone


def rename_sites(apps, schema_editor):
    Site = apps.get_model("inventory", "Site")
    names = {
        "UQAM_1": "Lac Saint-Pierre Transformed Marsh",
        "UQAM_2": "Lac-à-la-Tortue Natural Open Bog",
        "UQAM_3": "Lac-à-la-Tortue Natural Forested Bog",
        "UQAM_4": "Saint-Rémi Transformed Forested Peatland",
        "UQAM_5": "Baie Saint-François Natural Marsh",
        "MCGILL_1": "Lac Saint-Pierre Restored Marsh",
    }
    for code, name in names.items():
        Site.objects.filter(code__iexact=code).exclude(name=name).update(
            name=name, version=F("version") + 1, updated_at=timezone.now()
        )


class Migration(migrations.Migration):
    dependencies = [("inventory", "0014_alter_site_name")]
    operations = [migrations.RunPython(rename_sites, migrations.RunPython.noop)]
