"""Las acciones del admin exigen permiso de escritura.

Django gatea las acciones del admin solo por poder llegar al listado. Sin
declarar `permissions=`, cualquier cuenta de staff con permiso de *ver* podia
ejecutarlas: activar cuentas de sindicato pendientes de aprobacion, cambiar
fechas de expedicion, o --la mas grave-- exportar a Excel los datos personales
descifrados de los afiliados seleccionados.

Hoy no hay ninguna cuenta con solo permiso de ver (todas las de staff son
superusuario), asi que no es un agujero explotable ahora mismo. Pero el dia que
se cree un rol de consulta --que es lo natural cuando alguien pide "acceso solo
para mirar"-- ese rol vendria con capacidad de exportar el archivo entero, y
nadie lo esperaria. Declararlo cuesta un argumento.
"""

import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission, User

from gestion.admin import UsuarioAdmin, aprobar_cuentas, asignar_fecha_hoy, exportar_imprenta


def _staff_solo_lectura(nombre="mirona"):
    """Cuenta de staff que puede VER afiliados y usuarios, pero no cambiarlos."""
    usuario = User.objects.create_user(nombre, password="clave-larga-123", is_staff=True)  # noqa: S106
    usuario.user_permissions.add(
        Permission.objects.get(codename="view_afiliado"),
        Permission.objects.get(codename="view_user"),
    )
    return usuario


@pytest.mark.parametrize(
    "accion",
    [asignar_fecha_hoy, exportar_imprenta, aprobar_cuentas],
    ids=["asignar_fecha", "exportar_imprenta", "aprobar_cuentas"],
)
def test_las_acciones_declaran_que_exigen_permiso_de_cambio(accion):
    """`permissions` es lo que Django consulta para decidir si ofrece la accion."""
    # Django guarda tal cual lo que se le pase (lista, no tupla), asi que se
    # compara el contenido y no el tipo.
    assert list(getattr(accion, "allowed_permissions", [])) == ["change"], (
        f"{accion.__name__} no declara permissions=['change']: Django la ofreceria "
        "a cualquier cuenta de staff que alcance el listado."
    )


@pytest.mark.django_db
def test_una_cuenta_de_solo_lectura_no_puede_aprobar_cuentas(rf):
    """La consecuencia concreta: aprobar una cuenta salta el control manual de
    altas, que es lo unico que impide que cualquiera suba datos de afiliacion."""
    peticion = rf.get("/admin/auth/user/")
    peticion.user = _staff_solo_lectura()

    disponibles = UsuarioAdmin(User, admin.site).get_actions(peticion)

    assert "aprobar_cuentas" not in disponibles


@pytest.mark.django_db
def test_un_superusuario_si_puede(rf):
    """La restriccion no debe estorbar a quien si tiene que usarla."""
    peticion = rf.get("/admin/auth/user/")
    peticion.user = User.objects.create_superuser("jefa", "j@ejemplo.es", "clave-larga-123")  # noqa: S106

    disponibles = UsuarioAdmin(User, admin.site).get_actions(peticion)

    assert "aprobar_cuentas" in disponibles


# --- Filtro duplicado en el listado de usuarios ---

def test_el_listado_de_usuarios_no_repite_ningun_filtro():
    """`is_active` ya viene en UserAdmin.list_filter de Django, asi que
    anadirlo lo dejaba dos veces y el panel lateral pintaba "Por activo"
    duplicado. Django no deduplica list_filter."""
    filtros = list(UsuarioAdmin.list_filter)

    assert len(filtros) == len(set(filtros)), f"filtros repetidos: {filtros}"
    assert "is_active" in filtros, "sigue haciendo falta para revisar las altas pendientes"
