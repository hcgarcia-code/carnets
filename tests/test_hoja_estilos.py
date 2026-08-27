"""Una sola hoja de estilos y una sola plantilla base para todas las pantallas.

Cada plantilla llevaba su propio bloque `<style>` con el mismo CSS repetido:
ocho copias de los mismos colores, botones y cajas, ademas de ocho cabeceras
HTML identicas. Cambiar un color exigia recordar las ocho, y en la practica se
olvidaba alguna: el resultado son pantallas que se parecen pero no coinciden.

Estas pruebas comprueban el HTML **renderizado**, no el archivo fuente: que una
plantilla enlace la hoja no significa que la pagina la sirva, y es la pagina lo
que ve el navegador.
"""

from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User

from gestion.models import PerfilSindicato

DIRECTORIO = Path(settings.BASE_DIR) / "gestion" / "templates" / "gestion"
HOJA = Path(settings.BASE_DIR) / "gestion" / "static" / "gestion" / "carnets.css"

# Las plantillas propias del proyecto. El admin de Django trae las suyas y no
# se toca: sobrescribir el CSS del admin es fragil y se rompe al actualizarlo.
PLANTILLAS = [
    "portada.html", "login.html", "registro.html", "acuerdo_legal.html",
    "subir_excel.html", "notificaciones.html", "panel_imprenta.html",
    "password/solicitar.html", "password/enviado.html",
    "password/nueva.html", "password/hecho.html",
]


@pytest.fixture
def sindicato(client):
    usuario = User.objects.create_user("sindicato_css", "a@ejemplo.es", "clave-larga-123")  # noqa: S106
    PerfilSindicato.objects.create(usuario=usuario, acuerdo_aceptado=True)
    client.force_login(usuario)
    return usuario


@pytest.fixture
def imprenta(client):
    usuario = User.objects.create_user("imprenta_css", "i@ejemplo.es", "clave-larga-123")  # noqa: S106
    grupo, _ = Group.objects.get_or_create(name="Imprenta")
    usuario.groups.add(grupo)
    client.force_login(usuario)
    return usuario


# --- La hoja ---

def test_la_hoja_comun_existe():
    assert HOJA.is_file(), f"no se encuentra la hoja comun en {HOJA}"


def test_django_encuentra_la_hoja():
    """Que el archivo exista no basta: tiene que estar donde Django lo busca."""
    from django.contrib.staticfiles import finders

    assert finders.find("gestion/carnets.css") is not None
    assert finders.find("gestion/logo-cgt.png") is not None


def test_la_hoja_define_el_sistema_completo():
    """Si falta una pieza, las plantillas la reinventan localmente y volvemos
    al punto de partida."""
    css = HOJA.read_text(encoding="utf-8")

    for pieza in ("--rojo", "--tinta", "--papel", "--radio",
                  ".vidrio", ".boton", ".campo", ".fondo", ".marca"):
        assert pieza in css, f"la hoja no define {pieza}"


def test_no_se_cargan_fuentes_ni_recursos_de_terceros():
    """Cargar una fuente desde Google manda la IP de cada visitante a Google en
    cada visita. La EIPD (§7.2) declara que toda la cadena permanece en la UE, y
    la politica de seguridad del sitio solo admite recursos propios. Una de las
    dos cosas tendria que cambiar, y ninguna merece cambiarse por una
    tipografia: se usa la pila del sistema."""
    fuentes = [HOJA.read_text(encoding="utf-8")]
    fuentes += [(DIRECTORIO / n).read_text(encoding="utf-8") for n in PLANTILLAS]
    fuentes.append((DIRECTORIO / "base.html").read_text(encoding="utf-8"))

    for texto in fuentes:
        for host in ("fonts.googleapis.com", "fonts.gstatic.com",
                     "cdn.jsdelivr", "unpkg.com", "cdnjs."):
            assert host not in texto, f"se carga algo de {host}"


# --- Las plantillas ---

@pytest.mark.parametrize("nombre", PLANTILLAS)
def test_cada_plantilla_hereda_de_la_base(nombre):
    """La base trae la cabecera, la hoja y el fondo. Una plantilla que no la
    extienda tiene que repetir las tres cosas, que es de donde venimos."""
    contenido = (DIRECTORIO / nombre).read_text(encoding="utf-8")

    assert "{% extends" in contenido, f"{nombre} no extiende ninguna base"


@pytest.mark.parametrize("nombre", PLANTILLAS)
def test_ninguna_plantilla_guarda_su_propia_copia_del_sistema(nombre):
    """El punto de la refactorizacion. Un bloque `<style>` para algo exclusivo
    de una pantalla es legitimo; repetir los colores o los botones no."""
    contenido = (DIRECTORIO / nombre).read_text(encoding="utf-8")

    duplicados = [d for d in ("#cc0000", "backdrop-filter", "<!DOCTYPE", "<body")
                  if d.lower() in contenido.lower()]
    assert not duplicados, f"{nombre} repite {duplicados}: eso vive en la base o en carnets.css"


# --- Lo que ve el navegador ---

@pytest.mark.django_db
@pytest.mark.parametrize("url", ["/", "/login/", "/alta/", "/recuperar-password/"])
def test_las_paginas_publicas_sirven_la_hoja(client, url):
    respuesta = client.get(url)

    assert respuesta.status_code == 200, f"{url} no responde"
    assert "gestion/carnets.css" in respuesta.content.decode(), f"{url} no enlaza la hoja"


@pytest.mark.django_db
@pytest.mark.parametrize("url", ["/subir-datos/", "/notificaciones/"])
def test_las_paginas_con_sesion_sirven_la_hoja(client, sindicato, url):
    respuesta = client.get(url)

    assert respuesta.status_code == 200, f"{url} no responde"
    assert "gestion/carnets.css" in respuesta.content.decode()


@pytest.mark.django_db
def test_el_acuerdo_legal_sirve_la_hoja(client):
    usuario = User.objects.create_user("sin_acuerdo", "b@ejemplo.es", "clave-larga-123")  # noqa: S106
    PerfilSindicato.objects.create(usuario=usuario, acuerdo_aceptado=False)
    client.force_login(usuario)

    respuesta = client.get("/acuerdo-legal/")

    assert respuesta.status_code == 200
    assert "gestion/carnets.css" in respuesta.content.decode()


@pytest.mark.django_db
def test_el_panel_de_imprenta_sirve_la_hoja(client, imprenta):
    respuesta = client.get("/panel-imprenta/")

    assert respuesta.status_code == 200
    assert "gestion/carnets.css" in respuesta.content.decode()


@pytest.mark.django_db
def test_ninguna_pagina_deja_estilos_sueltos(client):
    """Un `<style>` con el sistema dentro del HTML servido significa que esa
    pantalla se quedo fuera de la refactorizacion."""
    for url in ("/", "/login/", "/alta/", "/recuperar-password/"):
        html = client.get(url).content.decode()
        assert "#cc0000" not in html, f"{url} lleva colores del sistema en linea"


@pytest.mark.django_db
def test_el_logo_aparece_en_las_pantallas_publicas(client):
    """Sustituye al cuadrado de marcador. Si falta, la marca no se ve."""
    for url in ("/", "/login/"):
        assert "logo-cgt.png" in client.get(url).content.decode(), f"{url} sin logo"


@pytest.mark.django_db
def test_la_politica_de_seguridad_sigue_permitiendo_la_hoja(client):
    """`style-src 'self'` cubre una hoja propia; si alguien la endurece a
    `'none'` o mueve la hoja a un CDN, esto salta."""
    politica = client.get("/").headers.get("Content-Security-Policy", "")

    assert "style-src 'self'" in politica
    assert "img-src 'self'" in politica, "el logo es una imagen propia"
