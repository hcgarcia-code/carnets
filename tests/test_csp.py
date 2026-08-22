"""Cabecera Content-Security-Policy.

Hoy no hay ningún punto por donde inyectar HTML: las plantillas no usan
`|safe`, ni `mark_safe`, ni `{% autoescape off %}`, y el autoescapado de Django
está activo. La CSP no arregla por tanto ningún agujero conocido: es la red que
queda debajo si algún día alguien añade una plantilla que sí lo tenga.

Su valor está en `script-src 'self'`: aunque se colara un `<script>` en la
página, el navegador se negaría a ejecutarlo por no venir de un archivo del
propio sitio. Eso convierte un XSS explotable en uno inerte.

`style-src` sí admite 'unsafe-inline' porque las plantillas llevan sus estilos
en bloques `<style>` dentro del HTML. Es una concesión real, pero el daño que
habilita un estilo inyectado es de otro orden que el de un script.
"""

import pytest
from django.contrib.auth.models import User

DIRECTIVAS_ESPERADAS = {
    "default-src": "'self'",
    "script-src": "'self'",
    "object-src": "'none'",
    "frame-ancestors": "'none'",
    "base-uri": "'self'",
    "form-action": "'self'",
}


def _politica(respuesta):
    cabecera = respuesta.headers.get("Content-Security-Policy", "")
    return {
        trozo.split()[0]: " ".join(trozo.split()[1:])
        for trozo in cabecera.split(";")
        if trozo.strip()
    }


@pytest.mark.django_db
def test_el_login_lleva_la_cabecera(client):
    politica = _politica(client.get("/login/"))

    for directiva, valor in DIRECTIVAS_ESPERADAS.items():
        assert politica.get(directiva) == valor, f"falta o difiere {directiva}"


@pytest.mark.django_db
def test_los_scripts_en_linea_no_estan_permitidos(client):
    """Es la directiva que hace que esto sirva de algo. Si alguna vez hay que
    poner 'unsafe-inline' aquí, la CSP deja de proteger contra XSS y más vale
    saberlo por una prueba en rojo que creerse cubierto."""
    politica = _politica(client.get("/login/"))

    assert "unsafe-inline" not in politica.get("script-src", "")
    assert "unsafe-eval" not in politica.get("script-src", "")


@pytest.mark.django_db
def test_los_estilos_en_linea_si(client):
    """Las plantillas llevan <style> dentro del HTML: sin esto se verían sin
    formato alguno."""
    assert "unsafe-inline" in _politica(client.get("/login/")).get("style-src", "")


@pytest.mark.django_db
def test_el_admin_tambien_la_lleva(client, entrar_en_el_admin):
    """El admin es donde se descifran los datos: es la página que más importa
    proteger, no una que se pueda excluir por comodidad."""
    usuario = User.objects.create_superuser("jefa", "j@ejemplo.es", "clave-larga-123")  # noqa: S106
    entrar_en_el_admin(client, usuario)

    politica = _politica(client.get("/admin/gestion/afiliado/"))

    assert politica.get("script-src") == "'self'"


@pytest.mark.django_db
def test_no_se_permite_cargar_nada_de_terceros(client):
    """La aplicación no usa CDN ni fuentes externas. Si algún día alguien
    añade una, esta prueba la obliga a pasar por aquí en vez de colarse."""
    politica = _politica(client.get("/login/"))

    for directiva in ("default-src", "script-src", "img-src", "font-src", "connect-src"):
        valor = politica.get(directiva, "")
        assert "http://" not in valor and "https://" not in valor, (
            f"{directiva} permite un origen externo: {valor}"
        )
