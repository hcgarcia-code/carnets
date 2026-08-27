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


REMITENTE_SIN_CONFIGURAR = "gestion.E002"
ADMINS_SIN_CONFIGURAR = "gestion.E003"

# El que pone Django cuando nadie configura nada.
REMITENTE_DE_DJANGO = "webmaster@localhost"


@register(Tags.security, deploy=True)
def comprobar_remitente_de_correo(app_configs, **kwargs):
    """Con el remitente por defecto de Django, el correo sale y no llega.

    `webmaster@localhost` no es una dirección enrutable: los servidores de
    destino la rechazan o la mandan a spam. Y el envío no falla —Django
    entrega el mensaje al SMTP y da por hecho que ya está—, así que la
    reposición de contraseña, que el manual de usuario da como vía principal,
    deja de funcionar sin que nada avise.

    Solo aplica si hay servidor de correo configurado: en local no lo hay y
    los mensajes van a la consola.
    """
    if not settings.EMAIL_HOST:
        return []
    if settings.DEFAULT_FROM_EMAIL != REMITENTE_DE_DJANGO:
        return []

    return [
        Error(
            f"DEFAULT_FROM_EMAIL sigue siendo '{REMITENTE_DE_DJANGO}', el valor por "
            "defecto de Django, y hay un servidor de correo configurado. Los mensajes "
            "saldrán con un remitente que el destino rechaza: la reposición de "
            "contraseña dejará de llegar sin que ningún envío falle.",
            hint=(
                "Pon DEFAULT_FROM_EMAIL en el .env del servidor "
                "(p. ej. soporte-carnets@cgt.org.es)."
            ),
            id=REMITENTE_SIN_CONFIGURAR,
        ),
    ]


@register(Tags.security, deploy=True)
def comprobar_destinatarios_de_alertas(app_configs, **kwargs):
    """Sin ADMINS, las alertas de seguridad no le llegan a nadie.

    `revisar_auditoria` avisa por `mail_admins()` de las rachas de bloqueos de
    acceso y de cada exportación de datos personales. Con `ADMINS` vacío esa
    llamada no lanza ningún error: simplemente no escribe. El cron sigue
    corriendo, el registro se sigue escribiendo, y el aviso no existe.
    """
    if not settings.EMAIL_HOST or settings.ADMINS:
        return []

    return [
        Error(
            "ADMINS está vacío y hay servidor de correo configurado. Las alertas de "
            "`revisar_auditoria` (rachas de bloqueos, exportaciones de datos "
            "personales) se envían con mail_admins(), que sin destinatarios no falla "
            "ni escribe: la detección de incidentes queda anulada en silencio.",
            hint="Pon ADMINS_CORREOS en el .env del servidor, separando por comas.",
            id=ADMINS_SIN_CONFIGURAR,
        ),
    ]
