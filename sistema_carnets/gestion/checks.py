"""Comprobaciones de configuración que solo tienen sentido antes de desplegar.

Se registran con `deploy=True`, así que no se ejecutan al arrancar ni durante
las pruebas: solo cuando alguien pide `manage.py check --deploy`, que es lo que
hace el script de despliegue antes de recargar la aplicación.
"""

from django.conf import settings
from django.core.checks import Error, Tags, register

CACHE_NO_COMPARTIDA = "gestion.E001"

# Backends que viven en la memoria de un proceso (o que no guardan nada). Para
# una caché de rendimiento serían una elección válida; para sostener un contador
# de intentos, no.
CACHES_NO_COMPARTIDAS = frozenset({
    "django.core.cache.backends.locmem.LocMemCache",
    "django.core.cache.backends.dummy.DummyCache",
})


@register(Tags.security, deploy=True)
def comprobar_cache_compartida(app_configs, **kwargs):
    """La caché sostiene los limitadores de intentos, así que debe compartirse.

    El limitador de login (gestion/auth_views.py) y el de alta de sindicatos
    (gestion/views.py) guardan su contador en la caché. Con el backend por
    defecto de Django —memoria del proceso— cada worker de gunicorn lleva su
    propia cuenta: el límite de 5 intentos pasa a ser 5 por worker, y se
    reinicia entero en cada recarga. No falla nada de forma visible; solo deja
    de proteger.
    """
    backend = settings.CACHES.get("default", {}).get("BACKEND", "")
    if backend not in CACHES_NO_COMPARTIDAS:
        return []

    return [
        Error(
            f"La caché por defecto es {backend}, que no se comparte entre procesos. "
            "Los limitadores de intentos de login y de alta guardan ahí su contador, "
            "así que con varios workers el límite de 5 intentos pasa a ser 5 por "
            "worker y se reinicia en cada recarga: la protección contra fuerza bruta "
            "queda anulada sin que nada falle.",
            hint=(
                "Configura CACHE_BACKEND y CACHE_LOCATION en el .env del servidor "
                "apuntando a una caché compartida entre workers (Redis, o "
                "django.core.cache.backends.db.DatabaseCache si no quieres otro "
                "servicio: esa solo necesita 'manage.py createcachetable')."
            ),
            id=CACHE_NO_COMPARTIDA,
        ),
    ]
