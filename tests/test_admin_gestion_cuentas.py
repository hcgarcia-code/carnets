"""TDD: el admin tiene que dejar ver el estado de cada sindicato sin rebuscar.

`PerfilSindicato` estaba registrado a pelo (`admin.site.register(PerfilSindicato)`),
así que en pantalla se leía «Perfil de <usuario>» y nada más: ni quién pidió el
alta, ni si la cuenta está aprobada, ni si firmó el acuerdo, ni qué ha cargado.
Todo eso ya estaba en la base de datos; lo que faltaba era enseñarlo.

Los tests entran por HTTP a propósito. Un nombre mal escrito en `list_display`
o un `annotate` sobre una relación que no existe no falla al importar: falla con
un 500 en la única pantalla desde la que se administra el sistema.
"""

import json
import logging
from datetime import timedelta

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from django.utils import timezone

from gestion.admin import AfiliadoAdmin, asignar_fecha_hoy
from gestion.auditoria import ACCIONES
from gestion.models import Afiliado, Notificacion, PerfilSindicato, RegistroSubida

pytestmark = pytest.mark.django_db

URL_PERFILES = "/admin/gestion/perfilsindicato/"
URL_NOTIFICACIONES = "/admin/gestion/notificacion/"
URL_SUBIDAS = "/admin/gestion/registrosubida/"

NOMBRE_REAL = "Aurora Beltrán Casanova"


@pytest.fixture(autouse=True)
def claves_de_prueba(settings):
    import base64
    settings.CARNETS_ENCRYPTION_KEYS = f"pruebas:{base64.b64encode(bytes(range(32))).decode()}"


@pytest.fixture
def auditoria(caplog):
    caplog.set_level(logging.INFO, logger="auditoria")

    def leer():
        return [json.loads(r.getMessage()) for r in caplog.records if r.name == "auditoria"]

    return leer


def _sindicato(nombre="sov_avila", **perfil):
    usuario = User.objects.create_user(nombre, password="clave-larga-123")  # noqa: S106
    datos = {"nombre_identificativo": "CGT SOV Ávila", "persona_contacto": "Marta Ruiz"}
    datos.update(perfil)
    PerfilSindicato.objects.create(usuario=usuario, **datos)
    return usuario


def _afiliado(usuario, **overrides):
    datos = {
        "sindicato_usuario": usuario,
        "confederacion_territorial": "01",
        "federacion_local": "12345",
        "federacion_sectorial": "02",
        "sindicato_codigo": "003",
        "num_afiliado": "123456",
        "nombre_apellidos": NOMBRE_REAL,
        "lengua": "A",
        "estado": "ALTA",
    }
    datos.update(overrides)
    afiliado = Afiliado(**datos)
    afiliado.full_clean(exclude=["sindicato_usuario"])
    afiliado.save()
    return afiliado


def _entrar(client, entrar_en_el_admin):
    jefa = User.objects.create_superuser("jefa", "j@ejemplo.es", "clave-larga-123")  # noqa: S106
    entrar_en_el_admin(client, jefa)
    return jefa


# --- El listado de sindicatos ---

def test_el_listado_de_sindicatos_se_abre_sin_error(client, entrar_en_el_admin):
    _entrar(client, entrar_en_el_admin)
    _sindicato()

    assert client.get(URL_PERFILES).status_code == 200


def test_el_listado_muestra_quien_pidio_el_alta_y_si_firmo(client, entrar_en_el_admin):
    _entrar(client, entrar_en_el_admin)
    _sindicato(nombre_identificativo="CGT Rama Metal Barcelona", persona_contacto="Marta Ruiz")

    contenido = client.get(URL_PERFILES).content.decode()

    assert "CGT Rama Metal Barcelona" in contenido, "sin esto no se sabe a quién se aprueba"
    assert "Marta Ruiz" in contenido, "el beta lo recogía y aquí se había perdido de vista"


def test_el_listado_dice_cuantas_cargas_lleva_cada_sindicato(client, entrar_en_el_admin):
    _entrar(client, entrar_en_el_admin)
    usuario = _sindicato()
    RegistroSubida.objects.create(sindicato=usuario, cantidad_afiliados=24, nombre_archivo="a.xlsx")
    RegistroSubida.objects.create(sindicato=usuario, cantidad_afiliados=11, nombre_archivo="b.xlsx")

    from gestion.admin import PerfilSindicatoAdmin

    respuesta = client.get(URL_PERFILES)

    columnas = PerfilSindicatoAdmin(PerfilSindicato, AdminSite())
    fila = respuesta.context["cl"].result_list[0]
    assert columnas.num_cargas(fila) == 2
    assert columnas.ultima_carga(fila) != "Nunca"


def test_un_sindicato_que_nunca_ha_subido_no_rompe_el_listado(client, entrar_en_el_admin):
    _entrar(client, entrar_en_el_admin)
    _sindicato()

    from gestion.admin import PerfilSindicatoAdmin

    respuesta = client.get(URL_PERFILES)

    assert respuesta.status_code == 200
    columnas = PerfilSindicatoAdmin(PerfilSindicato, AdminSite())
    fila = respuesta.context["cl"].result_list[0]
    assert columnas.num_cargas(fila) == 0
    assert columnas.ultima_carga(fila) == "Nunca"


def test_el_listado_de_sindicatos_no_ensena_datos_de_afiliados(client, entrar_en_el_admin):
    """Es una pantalla de gestión de cuentas, no de datos del Art. 9."""
    _entrar(client, entrar_en_el_admin)
    usuario = _sindicato()
    _afiliado(usuario)

    contenido = client.get(URL_PERFILES).content.decode()

    assert NOMBRE_REAL not in contenido
    assert "123456" not in contenido


def test_se_puede_filtrar_por_los_que_no_han_firmado_el_acuerdo(client, entrar_en_el_admin):
    _entrar(client, entrar_en_el_admin)
    _sindicato("firmado", acuerdo_aceptado=True, fecha_aceptacion=timezone.now())
    _sindicato("sin_firmar", acuerdo_aceptado=False)

    respuesta = client.get(URL_PERFILES, {"acuerdo_aceptado__exact": "0"})

    nombres = [p.usuario.username for p in respuesta.context["cl"].result_list]
    assert nombres == ["sin_firmar"]


def test_se_puede_filtrar_por_sindicatos_sin_actividad(client, entrar_en_el_admin):
    """Detectar sindicatos dormidos es la consulta que hoy no se puede hacer."""
    _entrar(client, entrar_en_el_admin)
    activo = _sindicato("activo")
    RegistroSubida.objects.create(sindicato=activo, cantidad_afiliados=5, nombre_archivo="a.xlsx")
    _sindicato("dormido")

    respuesta = client.get(URL_PERFILES, {"actividad": "sin_cargas"})

    nombres = [p.usuario.username for p in respuesta.context["cl"].result_list]
    assert nombres == ["dormido"]


def test_se_puede_filtrar_por_sindicatos_que_llevan_meses_sin_cargar(client, entrar_en_el_admin):
    from gestion.admin import DIAS_SIN_ACTIVIDAD, PerfilSindicatoAdmin

    _entrar(client, entrar_en_el_admin)
    reciente = _sindicato("reciente")
    RegistroSubida.objects.create(sindicato=reciente, cantidad_afiliados=5, nombre_archivo="a.xlsx")
    antiguo = _sindicato("antiguo")
    vieja = RegistroSubida.objects.create(
        sindicato=antiguo, cantidad_afiliados=9, nombre_archivo="b.xlsx",
    )
    # `fecha` es auto_now_add: para envejecerla hay que escribirla luego.
    RegistroSubida.objects.filter(pk=vieja.pk).update(
        fecha=timezone.now() - timedelta(days=DIAS_SIN_ACTIVIDAD + 10),
    )

    respuesta = client.get(URL_PERFILES, {"actividad": "dormidos"})

    nombres = [p.usuario.username for p in respuesta.context["cl"].result_list]
    assert nombres == ["antiguo"]

    # El recuento de cargas debe seguir siendo correcto con el filtro puesto:
    # un JOIN de más sobre `subidas` lo inflaría en silencio.
    columnas = PerfilSindicatoAdmin(PerfilSindicato, AdminSite())
    assert columnas.num_cargas(respuesta.context["cl"].result_list[0]) == 1


def test_la_firma_del_acuerdo_no_se_puede_editar_a_mano(client, entrar_en_el_admin):
    """`fecha_aceptacion` e `ip_aceptacion` son la constancia de un
    consentimiento: si se pueden teclear, dejan de probar nada."""
    from gestion.admin import PerfilSindicatoAdmin

    solo_lectura = PerfilSindicatoAdmin(PerfilSindicato, AdminSite()).readonly_fields

    assert "fecha_aceptacion" in solo_lectura
    assert "ip_aceptacion" in solo_lectura


# --- Historial de cargas en la ficha de la cuenta ---

def test_la_ficha_del_sindicato_ensena_su_historial_de_cargas(client, entrar_en_el_admin):
    _entrar(client, entrar_en_el_admin)
    usuario = _sindicato()
    RegistroSubida.objects.create(
        sindicato=usuario, cantidad_afiliados=24, nombre_archivo="altas_marzo.xlsx",
    )

    contenido = client.get(f"/admin/auth/user/{usuario.pk}/change/").content.decode()

    assert "altas_marzo.xlsx" in contenido, "el historial debe verse sin cambiar de pantalla"


def test_el_historial_de_cargas_no_se_puede_inventar_desde_el_admin(client, entrar_en_el_admin):
    """Un RegistroSubida solo lo crea una subida real: es la prueba de qué
    entregó cada sindicato y cuándo."""
    from gestion.admin import RegistroSubidaInline

    inline = RegistroSubidaInline(User, AdminSite())
    peticion = RequestFactory().get("/admin/")

    assert inline.has_add_permission(peticion, None) is False
    assert inline.has_change_permission(peticion, None) is False


def test_dar_de_alta_una_cuenta_a_mano_sigue_funcionando(client, entrar_en_el_admin):
    """Regresión: un inline en UserAdmin puede romper el alta en dos pasos que
    trae Django de serie."""
    _entrar(client, entrar_en_el_admin)

    assert client.get("/admin/auth/user/add/").status_code == 200


def test_el_listado_de_subidas_se_puede_recorrer_por_fechas(client, entrar_en_el_admin):
    _entrar(client, entrar_en_el_admin)
    usuario = _sindicato()
    RegistroSubida.objects.create(sindicato=usuario, cantidad_afiliados=3, nombre_archivo="a.xlsx")

    respuesta = client.get(URL_SUBIDAS)

    assert respuesta.status_code == 200
    assert respuesta.context["cl"].date_hierarchy == "fecha"


# --- Notificaciones ---

def test_se_puede_consultar_que_se_le_notifico_a_un_sindicato(client, entrar_en_el_admin):
    _entrar(client, entrar_en_el_admin)
    usuario = _sindicato()
    Notificacion.objects.create(usuario=usuario, mensaje="Tu paquete de 3 afiliado(s)...")

    contenido = client.get(URL_NOTIFICACIONES).content.decode()

    assert "Tu paquete de 3 afiliado(s)" in contenido


def test_las_notificaciones_no_se_crean_ni_se_editan_a_mano(client, entrar_en_el_admin):
    """Las genera el envío a imprenta. Una escrita a mano diría al sindicato
    que se imprimió algo que no se imprimió."""
    from gestion.admin import NotificacionAdmin

    admin_obj = NotificacionAdmin(Notificacion, AdminSite())
    peticion = RequestFactory().get("/admin/")

    assert admin_obj.has_add_permission(peticion) is False
    assert set(admin_obj.readonly_fields) >= {"usuario", "mensaje", "fecha_creacion"}


# --- Auditoría de la acción de fechar ---

def test_asignar_fecha_de_expedicion_queda_auditado(auditoria):
    """Cambia un campo de registros del Art. 9. Era la única de las tres
    acciones del admin que no aparecía en ningún registro."""
    usuario = _sindicato()
    afiliado = _afiliado(usuario)

    peticion = RequestFactory().get("/admin/")
    peticion.user = usuario
    peticion.session = {}
    peticion._messages = FallbackStorage(peticion)  # noqa: SLF001

    asignar_fecha_hoy(
        AfiliadoAdmin(Afiliado, AdminSite()), peticion, Afiliado.objects.all(),
    )

    fechados = [r for r in auditoria() if r["accion"] == ACCIONES.AFILIADOS_FECHADOS]
    assert len(fechados) == 1
    assert fechados[0]["cantidad"] == 1
    assert fechados[0]["ids"] == [str(afiliado.pk)]


def test_asignar_fecha_no_escribe_datos_personales_en_el_registro(auditoria):
    usuario = _sindicato()
    _afiliado(usuario)

    peticion = RequestFactory().get("/admin/")
    peticion.user = usuario
    peticion.session = {}
    peticion._messages = FallbackStorage(peticion)  # noqa: SLF001

    asignar_fecha_hoy(
        AfiliadoAdmin(Afiliado, AdminSite()), peticion, Afiliado.objects.all(),
    )

    assert NOMBRE_REAL not in json.dumps(auditoria())


def test_asignar_fecha_sigue_poniendo_la_fecha_de_hoy():
    usuario = _sindicato()
    afiliado = _afiliado(usuario)

    peticion = RequestFactory().get("/admin/")
    peticion.user = usuario
    peticion.session = {}
    peticion._messages = FallbackStorage(peticion)  # noqa: SLF001

    asignar_fecha_hoy(
        AfiliadoAdmin(Afiliado, AdminSite()), peticion, Afiliado.objects.all(),
    )

    afiliado.refresh_from_db()
    assert afiliado.fecha_expedicion == timezone.now().date()
