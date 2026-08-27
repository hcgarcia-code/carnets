"""El aviso a los sindicatos del paso a la version 2.0.

Un envio a todo el censo de sindicatos tiene dos formas de salir mal que no se
ven hasta que ya ha salido:

1. Meter a todos los destinatarios en el mismo mensaje. Cada sindicato veria la
   lista completa de los demas: quien usa el sistema, con su direccion. Eso no
   es una molestia de estilo, es una comunicacion de datos a terceros que nadie
   ha autorizado.
2. Enviarlo desde `webmaster@localhost`, que es lo que Django pone si nadie
   configura el remitente. El correo no llega, o llega a spam, y no se entera
   nadie porque el envio no falla.

Las dos cosas se comprueban aqui.
"""

import pytest
from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.management import call_command

from gestion.models import PerfilSindicato


def _sindicato(nombre, correo, activo=True):
    usuario = User.objects.create_user(nombre, correo, "clave-larga-123", is_active=activo)  # noqa: S106
    PerfilSindicato.objects.create(usuario=usuario, nombre_identificativo=nombre)
    return usuario


@pytest.fixture
def censo(db):
    """El censo de prueba, con los cuatro casos que hay que distinguir."""
    return {
        "con_correo": _sindicato("sov_uno", "uno@ejemplo.es"),
        "otro": _sindicato("sov_dos", "dos@ejemplo.es"),
        "sin_correo": _sindicato("sov_tres", ""),
        "pendiente": _sindicato("sov_cuatro", "cuatro@ejemplo.es", activo=False),
    }


# --- Lo que NO debe pasar ---

@pytest.mark.django_db
def test_en_seco_no_envia_nada(censo):
    """El modo por defecto. Un comando que envia de verdad si se te olvida una
    opcion es un comando que algun dia envia sin querer."""
    call_command("avisar_version_2")

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_cada_sindicato_recibe_su_propio_mensaje(censo):
    """La comprobacion que de verdad importa: un mensaje por destinatario, y
    cada uno con UNA sola direccion. Si alguien 'optimiza' esto metiendo a
    todos en un send_mass_mail con varios destinatarios, salta aqui."""
    call_command("avisar_version_2", "--enviar")

    assert len(mail.outbox) == 2, "deberia haber un mensaje por sindicato con correo"
    for mensaje in mail.outbox:
        assert len(mensaje.to) == 1, f"mensaje con {len(mensaje.to)} destinatarios: {mensaje.to}"
        assert not mensaje.cc, "nadie en copia"
        assert not mensaje.bcc, "ni siquiera en copia oculta: un mensaje, un destinatario"


@pytest.mark.django_db
def test_no_escribe_a_quien_aun_no_esta_aprobado(censo):
    """Una cuenta pendiente de aprobacion todavia no usa el sistema: decirle
    que 'pasamos a la 2.0' solo genera una consulta a soporte."""
    call_command("avisar_version_2", "--enviar")

    destinatarios = [d for m in mail.outbox for d in m.to]
    assert "cuatro@ejemplo.es" not in destinatarios


@pytest.mark.django_db
def test_la_imprenta_no_recibe_el_aviso_de_los_sindicatos(db):
    """El aviso habla de subir archivos y de la plantilla, que no es su trabajo."""
    usuario = User.objects.create_user("imprenta", "imprenta@ejemplo.es", "clave-larga-123")  # noqa: S106
    grupo, _ = Group.objects.get_or_create(name="Imprenta")
    usuario.groups.add(grupo)

    call_command("avisar_version_2", "--enviar")

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_no_sale_desde_webmaster_localhost(censo, settings):
    """El remitente por defecto de Django. Con el, el correo no llega."""
    call_command("avisar_version_2", "--enviar")

    for mensaje in mail.outbox:
        assert "localhost" not in mensaje.from_email, (
            f"remitente sin configurar: {mensaje.from_email}"
        )


# --- Lo que sí debe pasar ---

@pytest.mark.django_db
def test_avisa_de_quien_se_queda_sin_recibirlo(censo, capsys):
    """Un sindicato sin correo no recibe nada y nadie se entera: hay que
    llegarle por otra via, y para eso hay que saber quien es."""
    call_command("avisar_version_2")

    salida = capsys.readouterr().out
    assert "sov_tres" in salida, "no dice quien se queda fuera"


@pytest.mark.django_db
def test_en_seco_dice_a_cuantos_escribiria(censo, capsys):
    call_command("avisar_version_2")

    assert "2" in capsys.readouterr().out


@pytest.mark.django_db
def test_el_mensaje_lleva_lo_que_el_sindicato_necesita_saber(censo):
    """Las tres cosas que evitan una llamada a soporte: donde esta ahora, que
    su contrasena sigue valiendo, y que hacer si no."""
    call_command("avisar_version_2", "--enviar", "--url", "https://ejemplo.eu.pythonanywhere.com")

    cuerpo = mail.outbox[0].body
    assert "https://ejemplo.eu.pythonanywhere.com" in cuerpo, "no dice la direccion nueva"
    assert "contraseña" in cuerpo.lower(), "no habla de la contrasena"
    assert "soporte-carnets@cgt.org.es" in cuerpo, "no dice a quien escribir"


@pytest.mark.django_db
def test_el_mensaje_no_lleva_datos_de_otros_sindicatos(censo):
    """Cada mensaje se compone para su destinatario y nadie mas."""
    call_command("avisar_version_2", "--enviar")

    for mensaje in mail.outbox:
        otros = [d for m in mail.outbox for d in m.to if d not in mensaje.to]
        for direccion in otros:
            assert direccion not in mensaje.body, f"el cuerpo menciona a {direccion}"


@pytest.mark.django_db
def test_el_envio_queda_auditado(censo, caplog):
    """Es una operacion masiva sobre el censo entero: tiene que dejar rastro."""
    with caplog.at_level("INFO", logger="auditoria"):
        call_command("avisar_version_2", "--enviar")

    registros = "\n".join(r.getMessage() for r in caplog.records)
    assert "aviso.enviado" in registros


@pytest.mark.django_db
def test_la_auditoria_no_guarda_las_direcciones(censo, caplog):
    """El registro de auditoria sale del ambito cifrado: lleva el recuento,
    nunca a quien se escribio."""
    with caplog.at_level("INFO", logger="auditoria"):
        call_command("avisar_version_2", "--enviar")

    registros = "\n".join(r.getMessage() for r in caplog.records)
    assert "uno@ejemplo.es" not in registros
    assert "dos@ejemplo.es" not in registros
