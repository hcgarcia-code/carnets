from django.apps import AppConfig


def comprobar_claves_de_cifrado():
    """Verifica que hay claves de cifrado utilizables.

    Lanza ImproperlyConfigured si faltan o están mal formadas.
    """
    from .crypto import _claves

    _claves()


class GestionConfig(AppConfig):
    name = 'gestion'

    def ready(self):
        # Registra las comprobaciones de despliegue (gestion/checks.py). Van en
        # `check --deploy` y no aquí porque solo aplican a producción: un guard
        # de arranque que mire DEBUG tumbaría también las pruebas, que se
        # ejecutan con DEBUG=False.
        from . import checks  # noqa: F401

        # Las claves se comprueban al arrancar, no en el primer uso.
        #
        # Sin esto, la aplicación arranca tan campante con la clave vacía o mal
        # escrita: `manage.py check` pasa, `collectstatic` pasa, el script de
        # despliegue informa de éxito, la web se recarga... y el fallo aparece
        # después, en producción, a un sindicato subiendo su Excel o a alguien
        # abriendo el listado de afiliados. Como los datos personales no pueden
        # tratarse sin cifrado, es preferible no arrancar a arrancar roto.
        comprobar_claves_de_cifrado()
