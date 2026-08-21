"""Tests del comando `preparar_pruebas`, que deja el entorno listo para probar.

El comando existe para una sola cosa: que arrancar una prueba de extremo a
extremo no requiera media docena de pasos manuales (crear superusuario, crear
el grupo Imprenta, crear una cuenta de sindicato, fabricar un Excel con la
plantilla exacta). Eso lo hace cómodo, y lo cómodo es justo lo que acaba
ejecutándose en producción por error.

De ahí que la mitad de estas pruebas no comprueben que el comando funcione,
sino que se NIEGUE a funcionar: crea cuentas con contraseña conocida y datos
de afiliados inventados, así que ejecutarlo contra la base de datos real
mezclaría afiliados ficticios con los verdaderos y dejaría cuentas de acceso
que nadie ha aprobado.
"""

import base64
from pathlib import Path

import pandas as pd
import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import CommandError

from gestion.models import Afiliado, PerfilSindicato
from gestion.views import COLUMNAS_REQUERIDAS, GRUPO_IMPRENTA

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def claves_de_prueba(settings):
    settings.CARNETS_ENCRYPTION_KEYS = f"pruebas:{base64.b64encode(bytes(range(32))).decode()}"


@pytest.fixture(autouse=True)
def modo_desarrollo(settings):
    # El comando solo se permite fuera de producción; sin esto, todas las
    # pruebas del camino feliz chocarían con la propia guarda.
    settings.DEBUG = True


def _ejecutar(**opciones):
    call_command('preparar_pruebas', **opciones)


# --- Guardas: el comando debe negarse a tocar un entorno de producción ---

def test_se_niega_a_ejecutarse_con_debug_desactivado(settings):
    # DEBUG=False es la señal de "esto es un servidor de verdad". El comando
    # crea cuentas con contraseña impresa por pantalla y afiliados ficticios:
    # ejecutarlo ahí sería a la vez una brecha de acceso y una corrupción de
    # los datos reales.
    settings.DEBUG = False
    with pytest.raises(CommandError, match="DEBUG"):
        _ejecutar()


def test_se_niega_si_ya_hay_afiliados_reales_en_la_base_de_datos(django_user_model):
    # Segunda red, independiente de DEBUG: aunque alguien deje DEBUG=True en un
    # servidor con datos reales (un error de configuración de lo más común), la
    # presencia de afiliados delata que esta base de datos no es un juguete.
    usuario = django_user_model.objects.create_user('sindicato_real', password='clave-larga-123')  # noqa: S106
    Afiliado.objects.create(
        sindicato_usuario=usuario,
        confederacion_territorial='01', federacion_local='12345',
        federacion_sectorial='02', sindicato_codigo='003',
        num_afiliado='123456', nombre_apellidos='Persona Real',
        lengua='A', estado='ALTA',
    )
    with pytest.raises(CommandError, match="afiliado"):
        _ejecutar()


def test_la_guarda_de_afiliados_se_puede_saltar_a_proposito(django_user_model):
    # Reejecutar el comando sobre un entorno de pruebas que ya tiene datos de
    # ejemplo es legítimo. Debe requerir decirlo explícitamente, no ser lo que
    # pasa por defecto.
    usuario = django_user_model.objects.create_user('sindicato_demo', password='clave-larga-123')  # noqa: S106
    Afiliado.objects.create(
        sindicato_usuario=usuario,
        confederacion_territorial='01', federacion_local='12345',
        federacion_sectorial='02', sindicato_codigo='003',
        num_afiliado='123456', nombre_apellidos='Afiliado Ejemplo',
        lengua='A', estado='ALTA',
    )
    _ejecutar(forzar=True)  # no lanza


# --- Camino feliz: qué deja montado ---

def test_crea_el_grupo_imprenta():
    _ejecutar()
    assert Group.objects.filter(name=GRUPO_IMPRENTA).exists()


def test_crea_un_administrador_con_acceso_al_admin():
    _ejecutar()
    admin = User.objects.get(username='admin')
    assert admin.is_superuser and admin.is_staff and admin.is_active


def test_crea_la_cuenta_de_imprenta_dentro_del_grupo_y_sin_permisos_de_staff():
    _ejecutar()
    imprenta = User.objects.get(username='imprenta')
    assert imprenta.groups.filter(name=GRUPO_IMPRENTA).exists()
    # La imprenta entra por /panel-imprenta/, nunca por el admin de Django:
    # el admin le daría acceso a las fichas completas de los afiliados, que es
    # justo lo que el panel está diseñado para no enseñarle.
    assert imprenta.is_staff is False
    assert imprenta.is_superuser is False


def test_crea_una_cuenta_de_sindicato_activa():
    # A diferencia del alta autoservicio (que nace inactiva a propósito), esta
    # se crea ya aprobada: es el equivalente a que el administrador la hubiera
    # revisado, y sin eso no se podría probar el flujo de subida.
    _ejecutar()
    sindicato = User.objects.get(username='sindicato')
    assert sindicato.is_active is True
    assert sindicato.is_staff is False


def test_las_contrasenas_no_estan_escritas_en_el_codigo_fuente():
    # Se generan al azar en cada ejecución y se imprimen una sola vez. Una
    # contraseña fija en el código acabaría, tarde o temprano, en un servidor
    # accesible desde internet.
    from gestion.management.commands import preparar_pruebas

    fuente = Path(preparar_pruebas.__file__).read_text(encoding='utf-8')
    assert 'secrets' in fuente
    for sospechosa in ('password="', "password='", 'admin123', 'contrasena = "'):
        assert sospechosa not in fuente


def test_genera_un_excel_con_la_plantilla_oficial(tmp_path):
    destino = tmp_path / "ejemplo.xlsx"
    _ejecutar(excel=str(destino))
    assert destino.exists()

    df = pd.read_excel(destino)
    # Si la plantilla generada no cuadra con lo que la vista exige, el archivo
    # de ejemplo sería inútil justo para lo que se creó: probar la subida.
    assert list(df.columns) == COLUMNAS_REQUERIDAS
    assert len(df) > 0


def test_el_excel_generado_lo_acepta_la_vista_de_subida(client, tmp_path):
    # La prueba que de verdad importa: no que el archivo tenga las columnas
    # correctas, sino que la subida real lo trague sin un solo error de
    # validación. Recorre el mismo camino que hará el sindicato.
    destino = tmp_path / "ejemplo.xlsx"
    _ejecutar(excel=str(destino))

    sindicato = User.objects.get(username='sindicato')
    # El comando deja la cuenta sin perfil a propósito: firmar el acuerdo es
    # parte del recorrido que se quiere probar a mano. Aquí se da por firmado
    # para llegar directamente a lo que mide esta prueba, la subida.
    PerfilSindicato.objects.create(usuario=sindicato, acuerdo_aceptado=True)
    client.force_login(sindicato)

    antes = Afiliado.objects.count()
    with open(destino, 'rb') as archivo:
        respuesta = client.post('/subir-datos/', {'archivo_excel': archivo}, follow=True)

    mensajes = [str(m) for m in respuesta.context['messages']]
    assert not any('error' in m.lower() or 'no se ha guardado' in m.lower() for m in mensajes), (
        f"La plantilla generada fue rechazada: {mensajes}"
    )
    assert Afiliado.objects.count() > antes


def test_es_idempotente_y_se_puede_repetir():
    # Vuelve a ejecutarse sin estallar por usuarios duplicados: es lo primero
    # que se hace al reintentar una prueba que salió mal.
    _ejecutar()
    _ejecutar(forzar=True)
    assert User.objects.filter(username='admin').count() == 1
    assert User.objects.filter(username='imprenta').count() == 1


def test_reejecutar_renueva_la_contrasena(capsys):
    # Las contraseñas se imprimen una sola vez y no se guardan en ningún sitio.
    # Si se pierden, la salida de escape es reejecutar el comando: eso solo
    # sirve si de verdad reasigna una contraseña nueva y utilizable.
    _ejecutar()
    primera = capsys.readouterr().out

    _ejecutar(forzar=True)
    segunda = capsys.readouterr().out

    assert 'admin' in primera and 'admin' in segunda
    assert primera != segunda
