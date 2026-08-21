"""Cifra los datos personales que ya estaban guardados en claro.

La migración anterior (0006) solo cambia el tipo de columna: los nombres y
números de afiliado que ya había siguen escritos en claro. Esta migración los
reescribe cifrados, en el afiliado y también en su tabla de historial (de nada
sirve cifrar el afiliado si el historial de auditoría conserva el nombre).

Se trabaja con SQL parametrizado y no con el ORM a propósito: al leer por el
ORM, el campo intentaría descifrar un valor que todavía está en claro y
fallaría. El SQL crudo lee la columna tal cual está.

Es reversible (descifra de vuelta) y se puede repetir sin estropear nada: los
valores que ya están cifrados se reconocen por el prefijo de formato y se
dejan como están.
"""

from django.db import migrations

from gestion.crypto import VERSION_FORMATO, cifrar, descifrar

COLUMNAS = ("nombre_apellidos", "num_afiliado", "notas_historicas")
MODELOS = ("Afiliado", "HistoricalAfiliado")
PREFIJO_CIFRADO = f"{VERSION_FORMATO}$"


def _esta_cifrado(valor):
    return isinstance(valor, str) and valor.startswith(PREFIJO_CIFRADO)


def _a_cifrado(valor):
    if valor is None or _esta_cifrado(valor):
        return valor
    return cifrar(str(valor))


def _a_claro(valor):
    if not _esta_cifrado(valor):
        return valor
    return descifrar(valor)


def _reescribir(apps, schema_editor, transformar):
    columnas = ", ".join(f'"{c}"' for c in COLUMNAS)
    asignaciones = ", ".join(f'"{c}" = %s' for c in COLUMNAS)

    for nombre_modelo in MODELOS:
        modelo = apps.get_model("gestion", nombre_modelo)
        tabla = modelo._meta.db_table
        pk = modelo._meta.pk.column

        # Lo único que se interpola son identificadores que vienen del propio
        # modelo (_meta.db_table, _meta.pk.column) y la constante COLUMNAS de
        # este archivo; nada procede de entrada externa. Los valores sí viajan
        # como parámetros. No hay vector de inyección.
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(f'SELECT "{pk}", {columnas} FROM "{tabla}"')  # nosec B608
            filas = cursor.fetchall()

            for fila in filas:
                identificador, valores = fila[0], list(fila[1:])
                nuevos = [transformar(v) for v in valores]
                if nuevos == valores:
                    continue  # ya estaba en el estado destino
                cursor.execute(
                    f'UPDATE "{tabla}" SET {asignaciones} WHERE "{pk}" = %s',  # nosec B608
                    [*nuevos, identificador],
                )


def cifrar_existentes(apps, schema_editor):
    _reescribir(apps, schema_editor, _a_cifrado)


def descifrar_existentes(apps, schema_editor):
    _reescribir(apps, schema_editor, _a_claro)


class Migration(migrations.Migration):

    dependencies = [
        ("gestion", "0006_alter_afiliado_nombre_apellidos_and_more"),
    ]

    operations = [
        migrations.RunPython(
            cifrar_existentes,
            reverse_code=descifrar_existentes,
            elidable=False,
        ),
    ]
