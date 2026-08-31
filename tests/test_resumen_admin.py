"""TDD: la portada del admin dice qué hay pendiente, sin ir a buscarlo.

El administrador entraba a `/admin/` y veía la lista de modelos de Django: para
saber si había altas esperando aprobación, sindicatos usando el sistema sin
firmar el acuerdo, o gente que dejó de subir, tenía que recordar qué listado
filtrar y cómo. Nada de eso avisa solo.

Va **dentro** del admin y no en una vista aparte a propósito. Una vista con
`@staff_member_required` comprueba `is_active and is_staff` y nada más: sería
alcanzable con la contraseña sola, pegada a un admin que exige segundo factor.
Sobrescribiendo el índice se pasa por `admin_view()` → `has_permission()`, que
en OTPAdminSite incluye `is_verified()`. Hay un test que lo fija.
"""

import json
from datetime import datetime, timedelta, timezone as tz

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from gestion.auditoria import ACCIONES
from gestion.models import Afiliado, Notificacion, PerfilSindicato, RegistroSubida
from gestion.resumen import DIAS_SIN_ACTIVIDAD, resumen_operativo

pytestmark = pytest.mark.django_db

URL_INDICE = "/admin/"
NOMBRE_REAL = "Aurora Beltrán Casanova"


@pytest.fixture(autouse=True)
def claves_de_prueba(settings):
    import base64
    settings.CARNETS_ENCRYPTION_KEYS = f"pruebas:{base64.b64encode(bytes(range(32))).decode()}"


@pytest.fixture
def registro_de_auditoria(settings, tmp_path):
    """Un registro de auditoría de mentira, en un archivo temporal."""
    ruta = tmp_path / "auditoria.jsonl"
    ruta.write_text("", encoding="utf-8")
    settings.AUDITORIA_LOG_PATH = str(ruta)

    def escribir(accion, *, hace_minutos=1, veces=1, **extra):
        momento = datetime.now(tz.utc) - timedelta(minutes=hace_minutos)
        with ruta.open("a", encoding="utf-8") as archivo:
            for _ in range(veces):
                archivo.write(json.dumps({
                    "ts": momento.isoformat(), "accion": accion,
                    "usuario": "jefa", "ip": "203.0.113.7", **extra,
                }) + "\n")

    escribir.ruta = ruta
    return escribir


def _sindicato(nombre="sov_avila", activo=True, firmado=True):
    usuario = User.objects.create_user(nombre, password="clave-larga-123")  # noqa: S106
    usuario.is_active = activo
    usuario.save()
    PerfilSindicato.objects.create(
        usuario=usuario,
        nombre_identificativo=f"CGT {nombre}",
        persona_contacto="Marta Ruiz",
        acuerdo_aceptado=firmado,
        fecha_aceptacion=timezone.now() if firmado else None,
    )
    return usuario


def _afiliado(usuario, **overrides):
    datos = {
        "sindicato_usuario": usuario,
        "confederacion_territorial": "01", "federacion_local": "12345",
        "federacion_sectorial": "02", "sindicato_codigo": "003",
        "num_afiliado": "123456", "nombre_apellidos": NOMBRE_REAL,
        "lengua": "A", "estado": "ALTA",
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


def _textos(avisos):
    return " · ".join(a["texto"] for a in avisos)


# --- Que el resumen llegue a la portada ---

def test_la_portada_del_admin_se_abre_sin_error(client, entrar_en_el_admin):
    _entrar(client, entrar_en_el_admin)

    assert client.get(URL_INDICE).status_code == 200


def test_la_portada_exige_el_segundo_factor(client):
    """El motivo de meterlo en el admin y no en una vista aparte."""
    jefa = User.objects.create_superuser("jefa", "j@ejemplo.es", "clave-larga-123")  # noqa: S106
    client.force_login(jefa)  # autentica, pero NO verifica el segundo factor

    assert client.get(URL_INDICE).status_code != 200


def test_la_portada_enumera_lo_que_esta_pendiente(client, entrar_en_el_admin):
    _entrar(client, entrar_en_el_admin)
    _sindicato("pendiente_de_aprobar", activo=False)

    contenido = client.get(URL_INDICE).content.decode()

    assert "pendiente" in contenido.lower()
    assert "is_active__exact=0" in contenido, "cada aviso debe enlazar al listado ya filtrado"


def test_la_portada_no_ensena_datos_de_afiliados(client, entrar_en_el_admin):
    _entrar(client, entrar_en_el_admin)
    usuario = _sindicato()
    _afiliado(usuario)

    contenido = client.get(URL_INDICE).content.decode()

    assert NOMBRE_REAL not in contenido
    assert "123456" not in contenido


def test_la_portada_no_imprime_comentarios_de_la_plantilla(client, entrar_en_el_admin):
    """`{# ... #}` solo comenta UNA línea. En varias, Django lo imprime en la
    página, y ningún test que mire recuentos se entera."""
    _entrar(client, entrar_en_el_admin)

    contenido = client.get(URL_INDICE).content.decode()

    assert "{#" not in contenido
    assert "{% comment" not in contenido
    assert "no llevan enlace" not in contenido


def test_los_modelos_salen_con_nombres_legibles(client, entrar_en_el_admin):
    """Django pluraliza añadiendo una «s» al nombre de la clase: sin
    `verbose_name_plural`, el índice ofrece «Notificacions»."""
    _entrar(client, entrar_en_el_admin)

    contenido = client.get(URL_INDICE).content.decode()

    assert "Notificacions" not in contenido
    assert "Perfil sindicatos" not in contenido
    assert "Registro subidas" not in contenido


def test_la_portada_sigue_mostrando_la_lista_de_modelos(client, entrar_en_el_admin):
    """El resumen se añade encima; no sustituye a lo que ya había."""
    _entrar(client, entrar_en_el_admin)

    contenido = client.get(URL_INDICE).content.decode()

    assert "/admin/gestion/afiliado/" in contenido


# --- Qué cuenta el resumen ---

def test_avisa_de_las_cuentas_pendientes_de_aprobar():
    _sindicato("esperando", activo=False)
    _sindicato("ya_dentro", activo=True)

    avisos = resumen_operativo()

    aprobar = [a for a in avisos if "aprobar" in a["texto"]]
    assert len(aprobar) == 1
    assert "1" in aprobar[0]["texto"]
    assert "is_active__exact=0" in aprobar[0]["url"]


def test_avisa_de_los_sindicatos_que_usan_el_sistema_sin_firmar():
    _sindicato("sin_firmar", activo=True, firmado=False)
    _sindicato("firmado", activo=True, firmado=True)

    avisos = resumen_operativo()

    sin_firmar = [a for a in avisos if "acuerdo" in a["texto"]]
    assert len(sin_firmar) == 1
    assert "1" in sin_firmar[0]["texto"]


def test_no_cuenta_como_sin_firmar_a_quien_todavia_no_esta_aprobado():
    """Una cuenta sin aprobar aún no ha podido firmar: no es una incidencia."""
    _sindicato("esperando", activo=False, firmado=False)

    avisos = resumen_operativo()

    assert not [a for a in avisos if "acuerdo" in a["texto"]]


def test_avisa_de_los_sindicatos_que_llevan_meses_sin_cargar():
    activo = _sindicato("al_dia")
    RegistroSubida.objects.create(sindicato=activo, cantidad_afiliados=5, nombre_archivo="a.xlsx")
    dormido = _sindicato("dormido")
    vieja = RegistroSubida.objects.create(
        sindicato=dormido, cantidad_afiliados=9, nombre_archivo="b.xlsx",
    )
    RegistroSubida.objects.filter(pk=vieja.pk).update(
        fecha=timezone.now() - timedelta(days=DIAS_SIN_ACTIVIDAD + 10),
    )

    avisos = resumen_operativo()

    dormidos = [a for a in avisos if "sin cargar" in a["texto"]]
    assert len(dormidos) == 1
    assert "1" in dormidos[0]["texto"]
    assert "actividad=dormidos" in dormidos[0]["url"]


def test_dice_cuantos_carnets_estan_pendientes_de_imprimir():
    usuario = _sindicato()
    _afiliado(usuario, num_afiliado="111111")
    impreso = _afiliado(usuario, num_afiliado="222222")
    impreso.estado_impresion = Afiliado.ESTADO_IMPRESO
    impreso.save()

    avisos = resumen_operativo()

    imprimir = [a for a in avisos if a["url"] and "estado_impresion" in a["url"]]
    assert len(imprimir) == 1
    assert "1" in imprimir[0]["texto"]
    assert "estado_impresion__exact=PENDIENTE" in imprimir[0]["url"]


def _sindicato_al_dia(nombre="todo_en_orden"):
    """Aprobado, con el acuerdo firmado y con una carga reciente."""
    usuario = _sindicato(nombre)
    RegistroSubida.objects.create(sindicato=usuario, cantidad_afiliados=5, nombre_archivo="a.xlsx")
    return usuario


def test_un_sindicato_que_nunca_ha_subido_cuenta_como_dormido():
    """Aprobarlo y que no llegue a usarlo nunca es justo lo que hay que ver."""
    _sindicato("nunca_subio")

    dormidos = [a for a in resumen_operativo() if "sin cargar" in a["texto"]]

    assert len(dormidos) == 1


def test_sin_nada_pendiente_no_inventa_avisos(registro_de_auditoria):
    _sindicato_al_dia()

    assert resumen_operativo() == []


def test_la_portada_lo_dice_cuando_no_hay_nada_que_hacer(
    client, entrar_en_el_admin, registro_de_auditoria,
):
    _entrar(client, entrar_en_el_admin)
    _sindicato_al_dia()

    contenido = client.get(URL_INDICE).content.decode()

    assert "No hay nada pendiente" in contenido


# --- Bloqueos de acceso leídos del registro de auditoría ---

def test_avisa_de_los_bloqueos_de_acceso_de_la_ultima_hora(registro_de_auditoria):
    registro_de_auditoria(ACCIONES.LOGIN_BLOQUEADO, veces=4, hace_minutos=10)

    avisos = resumen_operativo()

    bloqueos = [a for a in avisos if "bloqueo" in a["texto"].lower()]
    assert len(bloqueos) == 1
    assert "4" in bloqueos[0]["texto"]


def test_no_cuenta_los_bloqueos_de_ayer(registro_de_auditoria):
    registro_de_auditoria(ACCIONES.LOGIN_BLOQUEADO, veces=9, hace_minutos=60 * 25)

    avisos = resumen_operativo()

    assert not [a for a in avisos if "bloqueo" in a["texto"].lower()]


def test_una_linea_corrupta_del_registro_no_rompe_el_resumen(registro_de_auditoria):
    registro_de_auditoria(ACCIONES.LOGIN_BLOQUEADO, veces=2, hace_minutos=5)
    with registro_de_auditoria.ruta.open("a", encoding="utf-8") as archivo:
        archivo.write("{esto no es json\n")

    avisos = resumen_operativo()

    bloqueos = [a for a in avisos if "bloqueo" in a["texto"].lower()]
    assert len(bloqueos) == 1
    assert "2" in bloqueos[0]["texto"]


def test_avisa_si_el_registro_de_auditoria_no_esta_configurado(settings):
    """Callarse haría que un despliegue sin registro pareciese vigilado."""
    settings.AUDITORIA_LOG_PATH = ""

    avisos = resumen_operativo()

    assert [a for a in avisos if "registro de auditoría" in a["texto"]]


def test_un_registro_que_no_se_puede_leer_no_tumba_la_portada(
    client, entrar_en_el_admin, settings, tmp_path,
):
    settings.AUDITORIA_LOG_PATH = str(tmp_path / "no-existe" / "auditoria.jsonl")
    _entrar(client, entrar_en_el_admin)

    assert client.get(URL_INDICE).status_code == 200


def test_el_resumen_no_lee_el_registro_entero(registro_de_auditoria):
    """El índice se carga en cada visita al admin y el registro crece sin
    límite: leerlo entero cada vez lo haría más lento cuanto más se usa."""
    from gestion.resumen import MAX_BYTES_AUDITORIA

    registro_de_auditoria(ACCIONES.LOGIN_BLOQUEADO, veces=3, hace_minutos=5)
    relleno = "x" * (MAX_BYTES_AUDITORIA + 1000)
    contenido = registro_de_auditoria.ruta.read_text(encoding="utf-8")
    registro_de_auditoria.ruta.write_text(relleno + "\n" + contenido, encoding="utf-8")

    avisos = resumen_operativo()

    # Los sucesos recientes están al final: se siguen viendo pese al relleno.
    bloqueos = [a for a in avisos if "bloqueo" in a["texto"].lower()]
    assert len(bloqueos) == 1
    assert "3" in bloqueos[0]["texto"]


# --- Que el resumen no cueste caro ---

def test_el_resumen_no_hace_una_consulta_por_sindicato(django_assert_num_queries):
    """Con un `annotate` mal puesto, el recuento de dormidos haría una consulta
    por cada sindicato: con 50 sindicatos son 50 viajes en cada carga."""
    for numero in range(12):
        _sindicato(f"sindicato_{numero}")

    with django_assert_num_queries(4):
        resumen_operativo()


def test_las_notificaciones_no_entran_en_el_resumen():
    """No es una incidencia: es correo ya enviado."""
    usuario = _sindicato()
    Notificacion.objects.create(usuario=usuario, mensaje="Tu paquete de 3 afiliado(s)...")

    assert not [a for a in resumen_operativo() if "notificaci" in a["texto"].lower()]
