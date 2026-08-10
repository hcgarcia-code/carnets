"""TDD: estado de impresión de afiliados + notificaciones a los sindicatos.

Cubre el flujo funcional (pendiente -> impreso, notificación por sindicato) y,
sobre todo, los escenarios de seguridad: aislamiento entre sindicatos (evitar
fugas de datos/notificaciones de un sindicato a otro) e intentos de inyección
de datos maliciosos a través de los campos del afiliado.
"""

import pytest
from django.contrib.auth.models import User

from gestion.models import Afiliado, Notificacion
from gestion.services import marcar_como_impresos_y_notificar

pytestmark = pytest.mark.django_db


def _crear_usuario(username):
    # No es un secreto real: es la contraseña fija usada solo para crear
    # usuarios de prueba en la base de datos de test.
    return User.objects.create_user(username=username, password="clave-segura-123")  # noqa: S106


def _crear_afiliado(usuario, **overrides):
    datos = {
        "sindicato_usuario": usuario,
        "confederacion_territorial": "01",
        "federacion_local": "12345",
        "federacion_sectorial": "02",
        "sindicato_codigo": "003",
        "num_afiliado": "123456",
        "nombre_apellidos": "Nombre Apellido",
        "lengua": "A",
        "estado": "ALTA",
    }
    datos.update(overrides)
    afiliado = Afiliado(**datos)
    afiliado.full_clean(exclude=["sindicato_usuario"])
    afiliado.save()
    return afiliado


# --- Estado por defecto y transición pendiente -> impreso ---

def test_afiliado_nuevo_esta_pendiente_por_defecto():
    usuario = _crear_usuario("sindicato_a")
    afiliado = _crear_afiliado(usuario)
    assert afiliado.estado_impresion == Afiliado.ESTADO_PENDIENTE
    assert afiliado.fecha_envio_imprenta is None


def test_marcar_como_impresos_actualiza_estado_y_fecha():
    usuario = _crear_usuario("sindicato_a")
    a1 = _crear_afiliado(usuario, num_afiliado="111111")
    a2 = _crear_afiliado(usuario, num_afiliado="222222")

    marcar_como_impresos_y_notificar(Afiliado.objects.filter(id__in=[a1.id, a2.id]))

    a1.refresh_from_db()
    a2.refresh_from_db()
    assert a1.estado_impresion == Afiliado.ESTADO_IMPRESO
    assert a2.estado_impresion == Afiliado.ESTADO_IMPRESO
    assert a1.fecha_envio_imprenta is not None
    assert a2.fecha_envio_imprenta is not None


def test_marcar_como_impresos_no_afecta_afiliados_no_seleccionados():
    usuario = _crear_usuario("sindicato_a")
    seleccionado = _crear_afiliado(usuario, num_afiliado="111111")
    no_seleccionado = _crear_afiliado(usuario, num_afiliado="222222")

    marcar_como_impresos_y_notificar(Afiliado.objects.filter(id=seleccionado.id))

    no_seleccionado.refresh_from_db()
    assert no_seleccionado.estado_impresion == Afiliado.ESTADO_PENDIENTE
    assert no_seleccionado.fecha_envio_imprenta is None


def test_marcar_como_impresos_con_queryset_vacio_no_falla_ni_notifica():
    marcar_como_impresos_y_notificar(Afiliado.objects.none())
    assert Notificacion.objects.count() == 0


def test_reenvio_a_imprenta_actualiza_fecha_y_genera_nueva_notificacion():
    usuario = _crear_usuario("sindicato_a")
    afiliado = _crear_afiliado(usuario)

    marcar_como_impresos_y_notificar(Afiliado.objects.filter(id=afiliado.id))
    afiliado.refresh_from_db()
    primera_fecha = afiliado.fecha_envio_imprenta

    marcar_como_impresos_y_notificar(Afiliado.objects.filter(id=afiliado.id))
    afiliado.refresh_from_db()

    assert afiliado.fecha_envio_imprenta >= primera_fecha
    assert Notificacion.objects.filter(usuario=usuario).count() == 2


# --- Notificaciones: contenido y agrupación correcta por sindicato ---

def test_marcar_como_impresos_crea_una_notificacion_para_el_sindicato():
    usuario = _crear_usuario("sindicato_a")
    _crear_afiliado(usuario, num_afiliado="111111")
    _crear_afiliado(usuario, num_afiliado="222222")

    marcar_como_impresos_y_notificar(Afiliado.objects.filter(sindicato_usuario=usuario))

    notificaciones = Notificacion.objects.filter(usuario=usuario)
    assert notificaciones.count() == 1
    assert "2" in notificaciones.first().mensaje


def test_notificacion_agrupa_por_sindicato_sin_mezclar_datos_entre_usuarios():
    usuario_a = _crear_usuario("sindicato_a")
    usuario_b = _crear_usuario("sindicato_b")
    _crear_afiliado(usuario_a, num_afiliado="111111")
    _crear_afiliado(usuario_a, num_afiliado="222222")
    afiliado_b = _crear_afiliado(usuario_b, num_afiliado="333333")

    marcar_como_impresos_y_notificar(Afiliado.objects.all())

    notif_a = Notificacion.objects.filter(usuario=usuario_a)
    notif_b = Notificacion.objects.filter(usuario=usuario_b)
    assert notif_a.count() == 1
    assert notif_b.count() == 1
    assert "2" in notif_a.first().mensaje
    assert "1" in notif_b.first().mensaje
    # Ningún dato del afiliado del sindicato B debe colarse en la notificación de A.
    assert afiliado_b.nombre_apellidos not in notif_a.first().mensaje


def test_afiliados_sin_seleccionar_de_otro_sindicato_no_generan_notificacion():
    usuario_a = _crear_usuario("sindicato_a")
    usuario_b = _crear_usuario("sindicato_b")
    afiliado_a = _crear_afiliado(usuario_a)
    _crear_afiliado(usuario_b)  # no se selecciona para imprimir

    marcar_como_impresos_y_notificar(Afiliado.objects.filter(id=afiliado_a.id))

    assert Notificacion.objects.filter(usuario=usuario_b).count() == 0


# --- Intentos de inyección de datos maliciosos ---

@pytest.mark.parametrize(
    "payload",
    [
        "Robert'); DROP TABLE gestion_afiliado;--",
        "<script>alert('xss')</script>",
        "{{ 7*7 }}",
        "' OR '1'='1",
        "../../etc/passwd",
    ],
)
def test_nombre_malicioso_no_se_filtra_al_mensaje_de_notificacion(payload):
    usuario = _crear_usuario("sindicato_a")
    _crear_afiliado(usuario, nombre_apellidos=payload)

    marcar_como_impresos_y_notificar(Afiliado.objects.filter(sindicato_usuario=usuario))

    mensaje = Notificacion.objects.get(usuario=usuario).mensaje
    assert payload not in mensaje


def test_marcar_como_impresos_con_datos_maliciosos_no_rompe_ni_ejecuta_nada():
    usuario = _crear_usuario("sindicato_a")
    _crear_afiliado(
        usuario,
        nombre_apellidos="'; DELETE FROM auth_user WHERE '1'='1",
        notas_historicas="<img src=x onerror=alert(1)>",
    )

    marcar_como_impresos_y_notificar(Afiliado.objects.filter(sindicato_usuario=usuario))

    # El usuario y el afiliado siguen intactos: no se ejecutó nada del payload.
    assert User.objects.filter(username="sindicato_a").exists()
    assert Afiliado.objects.filter(sindicato_usuario=usuario).count() == 1


def test_afiliado_no_admite_estado_impresion_fuera_de_los_valores_permitidos():
    usuario = _crear_usuario("sindicato_a")
    afiliado = _crear_afiliado(usuario)
    afiliado.estado_impresion = "IMPRESO'; DROP TABLE gestion_afiliado;--"
    with pytest.raises(Exception):  # noqa: B017 - ValidationError de Django
        afiliado.full_clean(exclude=["sindicato_usuario"])


# --- Vista de notificaciones: control de acceso ---

def test_vista_notificaciones_requiere_login(client):
    respuesta = client.get("/notificaciones/")
    assert respuesta.status_code == 302
    assert "/login/" in respuesta.url


def test_usuario_solo_ve_sus_propias_notificaciones(client):
    usuario_a = _crear_usuario("sindicato_a")
    usuario_b = _crear_usuario("sindicato_b")
    _crear_afiliado(usuario_a, num_afiliado="111111")
    _crear_afiliado(usuario_b, num_afiliado="222222", nombre_apellidos="Secreto De B")

    marcar_como_impresos_y_notificar(Afiliado.objects.filter(sindicato_usuario=usuario_a))
    marcar_como_impresos_y_notificar(Afiliado.objects.filter(sindicato_usuario=usuario_b))

    client.force_login(usuario_a)
    respuesta = client.get("/notificaciones/")

    assert respuesta.status_code == 200
    notificaciones_mostradas = list(respuesta.context["notificaciones"])
    assert all(n.usuario_id == usuario_a.id for n in notificaciones_mostradas)
    assert not any(n.usuario_id == usuario_b.id for n in notificaciones_mostradas)


def test_mensaje_de_notificacion_se_muestra_escapado_en_el_html(client):
    usuario = _crear_usuario("sindicato_a")
    _crear_afiliado(usuario)
    marcar_como_impresos_y_notificar(Afiliado.objects.filter(sindicato_usuario=usuario))

    # Forzamos un mensaje con HTML crudo directamente en BD para comprobar que
    # la plantilla lo escapa (defensa en profundidad, no depende de que el
    # servicio nunca genere ese contenido).
    notificacion = Notificacion.objects.get(usuario=usuario)
    notificacion.mensaje = "<script>alert('xss')</script>"
    notificacion.save()

    client.force_login(usuario)
    respuesta = client.get("/notificaciones/")

    contenido = respuesta.content.decode()
    assert "<script>alert" not in contenido
    assert "&lt;script&gt;" in contenido
