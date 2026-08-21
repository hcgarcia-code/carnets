"""Borra los datos personales que el log del admin guardó en claro.

Django escribe `str(obj)` en `django_admin_log.object_repr` cada vez que
alguien crea, cambia o borra un objeto desde el admin. Mientras
`Afiliado.__str__` incluyó el nombre y el número de afiliado, cada una de esas
operaciones dejó una copia en claro de esos datos en una tabla que no está
cifrada, no se purga y viaja en todos los backups.

`__str__` ya no los incluye, pero eso solo evita el problema de aquí en
adelante: las filas anteriores siguen ahí. Esta migración las reescribe
dejando únicamente el identificador del afiliado, que es lo que hace falta
para la trazabilidad y no revela a quién corresponde.

No es reversible: los datos borrados no deben poder recuperarse. Es
intencionado.
"""

from django.db import migrations, models
from django.db.models.functions import Concat


def depurar_repr_de_afiliados(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    LogEntry = apps.get_model("admin", "LogEntry")

    tipo = ContentType.objects.filter(app_label="gestion", model="afiliado").first()
    if tipo is None:
        return  # nunca se usó el admin sobre afiliados: nada que depurar

    LogEntry.objects.filter(content_type=tipo).update(
        object_repr=Concat(models.Value("Afiliado #"), "object_id"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("gestion", "0007_cifrar_datos_personales_existentes"),
        ("admin", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(
            depurar_repr_de_afiliados,
            reverse_code=migrations.RunPython.noop,
            elidable=False,
        ),
    ]
