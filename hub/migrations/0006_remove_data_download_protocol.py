"""Remove the retired protocol entry and its protected uploaded copy."""
import uuid
from django.db import migrations, transaction


def remove_protocol(apps, schema_editor):
    Protocol = apps.get_model('hub', 'Protocol')
    key = uuid.uuid5(uuid.NAMESPACE_URL, 'carbonique-protocol:Data_download.pdf')
    protocol = Protocol.objects.filter(pk=key).first()
    if protocol:
        if protocol.file:
            storage, name = protocol.file.storage, protocol.file.name
            transaction.on_commit(lambda: storage.delete(name), using=schema_editor.connection.alias)
        protocol.delete()


class Migration(migrations.Migration):
    dependencies = [('hub', '0005_caveat_review_and_publication')]
    operations = [migrations.RunPython(remove_protocol, migrations.RunPython.noop)]
