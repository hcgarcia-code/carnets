"""El manual de usuario, servido como pagina web desde la ayuda.

El manual existia solo como archivo Markdown en el repositorio: para leerlo
habia que tener el proyecto descargado, que es justo lo que no tiene el
sindicato al que va dirigido.

Se sirve renderizando `MANUAL_USUARIO.md`, no una copia en HTML. Mantener dos
versiones del mismo texto termina siempre igual: se corrige una y la otra se
queda contando lo de antes, y nadie sabe cual esta mirando.
"""

from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import User

from gestion.models import PerfilSindicato

MANUAL = Path(settings.BASE_DIR).parent / "MANUAL_USUARIO.md"
PLANTILLA = "documentos/plantilla_afiliacion_oficial.xlsx"


# --- La pagina ---

@pytest.mark.django_db
def test_el_manual_responde(client):
    assert client.get("/ayuda/manual/").status_code == 200


@pytest.mark.django_db
def test_el_manual_se_lee_sin_tener_cuenta(client):
    """Va con la ayuda, que es publica: buena parte del manual explica como
    conseguir la cuenta que aun no se tiene."""
    respuesta = client.get("/ayuda/manual/")

    assert respuesta.status_code == 200
    assert "login" not in respuesta.headers.get("Location", "")


@pytest.mark.django_db
def test_el_manual_sirve_el_contenido_del_archivo(client):
    """Que responda 200 no dice nada: podria estar sirviendo una pagina vacia."""
    contenido = client.get("/ayuda/manual/").content.decode()

    assert "plantilla_afiliacion_oficial.xlsx" in contenido
    assert "Checklist" in contenido or "Primer Uso" in contenido


@pytest.mark.django_db
def test_el_markdown_se_convierte_en_html_de_verdad(client):
    """El fallo silencioso de servir Markdown sin renderizar: la pagina carga,
    pero las tablas salen como una sopa de barras verticales."""
    contenido = client.get("/ayuda/manual/").content.decode()

    assert "<table>" in contenido, "las tablas no se han renderizado"
    assert "<h2" in contenido, "los titulos no se han renderizado"
    assert "|---" not in contenido, "hay tabla en Markdown sin convertir"


@pytest.mark.django_db
def test_el_manual_trae_indice_navegable(client):
    """Son seiscientas lineas: sin indice, la pagina es un scroll infinito."""
    contenido = client.get("/ayuda/manual/").content.decode()

    assert 'class="toc"' in contenido, "no se ha generado el indice"
    assert 'href="#' in contenido, "el indice no enlaza a ninguna seccion"
    assert 'id="' in contenido, "los titulos no tienen ancla a la que saltar"


@pytest.mark.django_db
def test_el_manual_usa_la_hoja_comun(client):
    """Es el encargo: que se parezca al resto del sitio, no a un archivo suelto."""
    contenido = client.get("/ayuda/manual/").content.decode()

    assert "gestion/carnets.css" in contenido
    assert "logo-cgt.png" in contenido


@pytest.mark.django_db
def test_el_manual_no_dice_quien_usa_el_sistema(client):
    """Publica, luego el mismo criterio que la portada y la ayuda."""
    usuario = User.objects.create_user("sov_oculto", "c@ejemplo.es", "clave-larga-123")  # noqa: S106
    PerfilSindicato.objects.create(
        usuario=usuario,
        nombre_identificativo="Sindicato Zarzaparrilla",
        persona_contacto="Zenobia Quiroga",
    )

    contenido = client.get("/ayuda/manual/").content.decode()

    assert "Sindicato Zarzaparrilla" not in contenido
    assert "Zenobia Quiroga" not in contenido
    assert "sov_oculto" not in contenido


# --- El enlace desde la ayuda ---

@pytest.mark.django_db
def test_la_ayuda_enlaza_el_manual(client):
    contenido = client.get("/ayuda/").content.decode()

    assert 'href="/ayuda/manual/"' in contenido, "no se llega al manual desde la ayuda"


@pytest.mark.django_db
def test_la_ayuda_ya_no_ofrece_la_plantilla(client):
    """La caja del manual sustituye a la de la plantilla, no se suma a ella."""
    contenido = client.get("/ayuda/").content.decode()

    assert PLANTILLA not in contenido


@pytest.mark.django_db
def test_pero_la_plantilla_sigue_descargandose_desde_la_carga(client):
    """La comprobacion que protege el cambio de arriba: quitar la caja de la
    ayuda no puede dejar a los sindicatos sin plantilla. En /subir-datos/, que
    es donde de verdad hace falta, tiene que seguir estando."""
    usuario = User.objects.create_user("sov_carga", "d@ejemplo.es", "clave-larga-123")  # noqa: S106
    PerfilSindicato.objects.create(usuario=usuario, acuerdo_aceptado=True)
    client.force_login(usuario)

    contenido = client.get("/subir-datos/").content.decode()

    assert PLANTILLA in contenido


# --- El archivo de origen ---

def test_el_manual_existe_donde_la_vista_lo_busca():
    assert MANUAL.is_file(), f"no se encuentra el manual en {MANUAL}"


def test_el_manual_no_trae_html_en_crudo():
    """El renderizador deja pasar el HTML que venga dentro del Markdown. El
    archivo es del repositorio y pasa por revision, asi que el riesgo es
    remoto, pero si alguien pega ahi un bloque de otra parte conviene que salte
    aqui y no en produccion."""
    texto = MANUAL.read_text(encoding="utf-8")

    for etiqueta in ("<script", "<iframe", "<object", "<embed", "onerror=", "javascript:"):
        assert etiqueta not in texto.lower(), f"el manual trae {etiqueta}"


@pytest.mark.django_db
def test_si_falta_el_archivo_la_pagina_no_revienta(client, monkeypatch, tmp_path):
    """Un despliegue que no copie el .md daria un 500 en una pagina publica.
    Mejor un 404, que dice lo que pasa sin ensenar la traza."""
    from gestion import views

    monkeypatch.setattr(views, "RUTA_MANUAL", tmp_path / "no_existe.md")

    assert client.get("/ayuda/manual/").status_code == 404


@pytest.mark.django_db
def test_el_html_en_crudo_del_origen_sale_escapado(client, monkeypatch, tmp_path):
    """La prueba que sostiene el `mark_safe` de la vista.

    La de arriba comprueba que HOY el manual no trae HTML. Esta comprueba que
    aunque lo trajera **no se ejecutaria**, que es una garantia distinta y mas
    fuerte: el renderizador tiene desactivado el paso de HTML en crudo.
    """
    from gestion import views

    falso = tmp_path / "MANUAL.md"
    falso.write_text(
        "# Manual\n\n## Seccion\n\n<script>alert(1)</script>\n\n"
        "Texto con <img src=x onerror=alert(1)> dentro.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(views, "RUTA_MANUAL", falso)
    views._manual_renderizado.cache_clear()

    contenido = client.get("/ayuda/manual/").content.decode()

    assert "<script>alert(1)</script>" not in contenido
    assert "<img src=x onerror" not in contenido
    assert "&lt;script&gt;" in contenido, "deberia verse como texto, no desaparecer"

    views._manual_renderizado.cache_clear()
