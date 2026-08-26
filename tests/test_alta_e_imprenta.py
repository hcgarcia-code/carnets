"""Tests del alta autoservicio de sindicatos y del panel de la imprenta.

Dos piezas nuevas, con requisitos de seguridad opuestos entre sí:

- El alta es pública (sin login, cualquiera puede llegar al formulario), así
  que la cuenta creada debe nacer INACTIVA: solo puede empezar a subir datos
  de afiliación sindical después de que un administrador la revise y la
  active a mano. Sin este cierre, el formulario público sería una vía directa
  para que cualquiera cargue datos de categoría especial sin supervisión.
- El panel de la imprenta es lo contrario: una cuenta ya de confianza (la
  creas tú a mano, no hay alta pública para ella) pero con visibilidad
  deliberadamente limitada. Ve números de afiliado y sindicato —lo que
  necesita para su logística— nunca nombres, y solo de los lotes que ya has
  mandado a imprimir.
"""

import base64
import json
import logging

import pytest
from django.contrib.auth.models import Group, User

from gestion.auditoria import ACCIONES
from gestion.models import Afiliado, PerfilSindicato
from gestion.views import GRUPO_IMPRENTA, INTENTOS_REGISTRO_MAXIMOS

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def claves_de_prueba(settings):
    settings.CARNETS_ENCRYPTION_KEYS = f"pruebas:{base64.b64encode(bytes(range(32))).decode()}"


@pytest.fixture
def auditoria(caplog):
    caplog.set_level(logging.INFO, logger="auditoria")

    def leer():
        return [json.loads(r.getMessage()) for r in caplog.records if r.name == "auditoria"]

    return leer


def _crear_afiliado(usuario, **overrides):
    datos = {
        "sindicato_usuario": usuario,
        "confederacion_territorial": "01",
        "federacion_local": "12345",
        "federacion_sectorial": "02",
        "sindicato_codigo": "003",
        "num_afiliado": "556677",
        "nombre_apellidos": "Aurora Beltrán Casanova",
        "lengua": "A",
        "estado": "ALTA",
    }
    datos.update(overrides)
    afiliado = Afiliado(**datos)
    afiliado.full_clean(exclude=["sindicato_usuario"])
    afiliado.save()
    return afiliado


# --- Alta autoservicio ---

def test_el_formulario_de_alta_no_requiere_sesion(client):
    respuesta = client.get("/alta/")
    assert respuesta.status_code == 200


def test_dar_de_alta_crea_una_cuenta_inactiva(client):
    respuesta = client.post("/alta/", {
        "username": "rama_barcelona",
        "nombre_identificativo": "CGT Rama Metal Barcelona",
        "email": "prueba@ejemplo.es",
        "persona_contacto": "Persona de prueba",
        "password1": "una-clave-realmente-larga-123",
        "password2": "una-clave-realmente-larga-123",
    })
    assert respuesta.status_code == 302

    usuario = User.objects.get(username="rama_barcelona")
    assert usuario.is_active is False, "debe nacer inactiva hasta que se apruebe"
    assert usuario.check_password("una-clave-realmente-larga-123")

    perfil = PerfilSindicato.objects.get(usuario=usuario)
    assert perfil.nombre_identificativo == "CGT Rama Metal Barcelona"


def test_una_cuenta_inactiva_no_puede_iniciar_sesion(client):
    client.post("/alta/", {
        "username": "rama_pendiente",
        "nombre_identificativo": "Rama pendiente de aprobar",
        "email": "prueba@ejemplo.es",
        "persona_contacto": "Persona de prueba",
        "password1": "una-clave-realmente-larga-123",
        "password2": "una-clave-realmente-larga-123",
    })

    conectado = client.login(username="rama_pendiente", password="una-clave-realmente-larga-123")  # noqa: S106
    assert not conectado


def test_tras_activarla_a_mano_si_puede_iniciar_sesion(client):
    client.post("/alta/", {
        "username": "rama_activada",
        "nombre_identificativo": "Rama ya aprobada",
        "email": "prueba@ejemplo.es",
        "persona_contacto": "Persona de prueba",
        "password1": "una-clave-realmente-larga-123",
        "password2": "una-clave-realmente-larga-123",
    })
    usuario = User.objects.get(username="rama_activada")
    usuario.is_active = True
    usuario.save()

    conectado = client.login(username="rama_activada", password="una-clave-realmente-larga-123")  # noqa: S106
    assert conectado


def test_el_alta_queda_auditada_sin_filtrar_la_contrasena(client, auditoria):
    client.post("/alta/", {
        "username": "rama_auditada",
        "nombre_identificativo": "Nombre libre de la rama",
        "email": "prueba@ejemplo.es",
        "persona_contacto": "Persona de prueba",
        "password1": "una-clave-super-secreta-999",
        "password2": "una-clave-super-secreta-999",
    })

    registros = [r for r in auditoria() if r["accion"] == ACCIONES.SINDICATO_REGISTRADO]
    assert registros and registros[0]["usuario"] == "rama_auditada"
    texto = json.dumps(auditoria())
    assert "una-clave-super-secreta-999" not in texto


def test_contrasenas_que_no_coinciden_no_crean_la_cuenta(client):
    client.post("/alta/", {
        "username": "rama_fallida",
        "nombre_identificativo": "X",
        "email": "prueba@ejemplo.es",
        "persona_contacto": "Persona de prueba",
        "password1": "una-clave-realmente-larga-123",
        "password2": "otra-clave-completamente-distinta",
    })
    assert not User.objects.filter(username="rama_fallida").exists()


def test_una_contrasena_demasiado_simple_no_crea_la_cuenta(client):
    # AUTH_PASSWORD_VALIDATORS ya exige longitud mínima y descarta contraseñas
    # comunes; el formulario de alta debe heredar esa validación, no saltársela.
    client.post("/alta/", {
        "username": "rama_debil",
        "nombre_identificativo": "X",
        "email": "prueba@ejemplo.es",
        "persona_contacto": "Persona de prueba",
        "password1": "12345",
        "password2": "12345",
    })
    assert not User.objects.filter(username="rama_debil").exists()


def test_pasado_el_limite_de_intentos_el_alta_se_bloquea(client):
    for i in range(INTENTOS_REGISTRO_MAXIMOS):
        client.post("/alta/", {
            "username": f"rama_{i}",
            "nombre_identificativo": "X",
            "email": "prueba@ejemplo.es",
            "persona_contacto": "Persona de prueba",
            "password1": "una-clave-realmente-larga-123",
            "password2": "una-clave-realmente-larga-123",
        })

    respuesta = client.post("/alta/", {
        "username": "rama_de_mas",
        "nombre_identificativo": "X",
        "email": "prueba@ejemplo.es",
        "persona_contacto": "Persona de prueba",
        "password1": "una-clave-realmente-larga-123",
        "password2": "una-clave-realmente-larga-123",
    })
    assert respuesta.status_code == 429
    assert not User.objects.filter(username="rama_de_mas").exists()


# --- Panel de la imprenta ---

def _crear_cuenta_imprenta(username="imprenta"):
    usuario = User.objects.create_user(username=username, password="clave-imprenta-larga-123")  # noqa: S106
    grupo, _ = Group.objects.get_or_create(name=GRUPO_IMPRENTA)
    usuario.groups.add(grupo)
    return usuario


def test_el_panel_de_imprenta_exige_sesion(client):
    respuesta = client.get("/panel-imprenta/")
    assert respuesta.status_code == 302
    assert "/login/" in respuesta["Location"]


def test_un_sindicato_normal_no_puede_ver_el_panel_de_imprenta(client):
    sindicato = User.objects.create_user(username="sindicato", password="clave-larga-123")  # noqa: S106
    client.force_login(sindicato)

    respuesta = client.get("/panel-imprenta/")
    assert respuesta.status_code == 403


def test_el_acceso_denegado_al_panel_queda_auditado(client, auditoria):
    sindicato = User.objects.create_user(username="sindicato2", password="clave-larga-123")  # noqa: S106
    client.force_login(sindicato)

    client.get("/panel-imprenta/")

    denegados = [r for r in auditoria() if r["accion"] == ACCIONES.ACCESO_DENEGADO]
    assert denegados


def test_la_cuenta_de_imprenta_ve_el_panel(client):
    imprenta = _crear_cuenta_imprenta()
    client.force_login(imprenta)

    respuesta = client.get("/panel-imprenta/")
    assert respuesta.status_code == 200


def test_el_panel_no_muestra_nombres_ni_notas(client):
    sindicato = User.objects.create_user(username="s", password="clave-larga-123")  # noqa: S106
    afiliado = _crear_afiliado(sindicato, notas_historicas="Reemitido en 2024")
    afiliado.estado_impresion = Afiliado.ESTADO_IMPRESO
    afiliado.save()

    imprenta = _crear_cuenta_imprenta()
    client.force_login(imprenta)

    respuesta = client.get("/panel-imprenta/")
    contenido = respuesta.content.decode()
    assert "Aurora" not in contenido
    assert "Beltrán" not in contenido
    assert "Reemitido en 2024" not in contenido
    assert "556677" in contenido  # el número sí es visible
    assert "003" in contenido  # el sindicato sí es visible


def test_el_panel_solo_muestra_lo_ya_enviado_a_imprenta(client):
    sindicato = User.objects.create_user(username="s2", password="clave-larga-123")  # noqa: S106
    _crear_afiliado(sindicato, num_afiliado="111111")  # sigue PENDIENTE

    enviado = _crear_afiliado(sindicato, num_afiliado="222222")
    enviado.estado_impresion = Afiliado.ESTADO_IMPRESO
    enviado.save()

    imprenta = _crear_cuenta_imprenta()
    client.force_login(imprenta)

    respuesta = client.get("/panel-imprenta/")
    contenido = respuesta.content.decode()
    assert "111111" not in contenido, "lo pendiente de imprimir no debe verse todavía"
    assert "222222" in contenido


def test_consultar_el_panel_queda_auditado(client, auditoria):
    imprenta = _crear_cuenta_imprenta()
    client.force_login(imprenta)

    client.get("/panel-imprenta/")

    consultas = [r for r in auditoria() if r["accion"] == ACCIONES.LOTE_IMPRESION_CONSULTADO]
    assert consultas and consultas[0]["usuario"] == "imprenta"


def test_la_cuenta_de_imprenta_no_puede_subir_afiliados(client):
    imprenta = _crear_cuenta_imprenta()
    client.force_login(imprenta)

    respuesta = client.get("/subir-datos/")
    assert respuesta.status_code == 403


def test_el_login_muestra_el_aviso_de_cuenta_pendiente_tras_darse_de_alta(client):
    """Tras el alta se redirige al login: el aviso tiene que llegar hasta ahí.

    La vista crea el mensaje "un administrador debe activar tu cuenta", pero
    quien lo tiene que leer es la plantilla de destino. Si el login no lo
    pinta, el sindicato recién registrado llega a una pantalla muda, intenta
    entrar, y recibe "usuario o contraseña incorrectos" —que es falso y le
    manda a revisar justo lo que no falla— en vez de saber que solo tiene que
    esperar la aprobación.
    """
    respuesta = client.post('/alta/', {
        'username': 'rama_avisada',
        'password1': 'Clave-Solida-Sindical-88',
        'password2': 'Clave-Solida-Sindical-88',
        'nombre_identificativo': 'CGT Rama Prueba',
        'email': 'prueba@ejemplo.es',
        'persona_contacto': 'Persona de prueba',
    }, follow=True)

    assert 'administrador' in respuesta.content.decode().lower()


def test_el_login_enlaza_al_alta(client):
    # Sin este enlace no hay forma de llegar al formulario de alta salvo que
    # alguien te pase la URL a mano, que es justo el trabajo manual que el
    # autoservicio venía a quitar.
    respuesta = client.get('/login/')
    assert '/alta/' in respuesta.content.decode()


def test_las_plantillas_no_filtran_marcas_de_comentario(client):
    # {# ... #} solo comenta una linea: escrito en varias, Django lo imprime
    # como texto y el comentario interno acaba en pantalla del usuario.
    for url in ('/login/', '/alta/'):
        contenido = client.get(url).content.decode()
        assert '{#' not in contenido and '{%' not in contenido, (
            f"{url} filtra marcas de plantilla sin procesar"
        )
