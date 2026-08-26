"""Importacion de las cuentas y afiliados del despliegue beta.

El beta (carnetscgt.eu.pythonanywhere.com) tiene sindicatos que ya se dieron de
alta, aceptaron el acuerdo y subieron sus listas. Hacerles repetir todo eso
seria perderlos por el camino, asi que el objetivo del comando es que la
migracion sea invisible para ellos: **misma contrasena, mismo acuerdo ya
firmado, mismos afiliados**.

Tres cosas que el comando tiene que resolver y no son evidentes:

1. **Las contrasenas se migran tal cual.** Django guarda un hash con su
   algoritmo y su sal por delante (`pbkdf2_sha256$...`); copiarlo al campo
   `password` sin volver a cifrarlo hace que la contrasena de siempre siga
   valiendo. Volver a pasarlo por `set_password` lo cifraria dos veces y nadie
   podria entrar.

2. **Los afiliados llegan en claro y tienen que quedar cifrados.** El volcado
   del beta es anterior al cifrado en reposo, asi que trae nombres y numeros
   legibles. Deben entrar por el ORM --nunca por SQL directo ni `bulk_create`
   sin senales-- para que `CampoTextoCifrado` los cifre al guardarlos.

3. **Tiene que poder ejecutarse dos veces.** Una importacion de este tipo casi
   nunca sale bien a la primera: falta un campo, se corta a la mitad, aparece
   un dato raro. Si la segunda pasada duplica cuentas y afiliados, el remedio
   es peor que la enfermedad.
"""

import json
from io import StringIO

import pytest
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command

from gestion.models import Afiliado, PerfilSindicato

CLAVE_DEL_BETA = "la-clave-que-ya-usaba-123"  # noqa: S105
NOMBRE_AFILIADO = "Rosa Ejemplo Apellido"
NUM_AFILIADO = "654321"


def _volcado(usuarios=None, perfiles=None, afiliados=None):
    """Construye un volcado con el formato de `manage.py dumpdata`."""
    return (usuarios or []) + (perfiles or []) + (afiliados or [])


def _usuario_beta(pk=1, username="sov_madrid", email="sov@ejemplo.es", activo=True):
    return {
        "model": "auth.user",
        "pk": pk,
        "fields": {
            "username": username,
            "email": email,
            # Hash real, tal y como lo escribiria Django en el beta.
            "password": make_password(CLAVE_DEL_BETA),
            "is_active": activo,
            "is_staff": False,
            "is_superuser": False,
            "date_joined": "2026-07-01T10:00:00Z",
            "last_login": None,
            "first_name": "",
            "last_name": "",
        },
    }


def _perfil_beta(pk=1, usuario_pk=1, **extra):
    campos = {
        "usuario": usuario_pk,
        "nombre_identificativo": "SOV Madrid",
        "acuerdo_aceptado": True,
        "fecha_aceptacion": "2026-07-01T10:05:00Z",
        "ip_aceptacion": "203.0.113.9",
    }
    campos.update(extra)
    return {"model": "gestion.perfilsindicato", "pk": pk, "fields": campos}


def _afiliado_beta(pk=1, usuario_pk=1, **extra):
    campos = {
        "sindicato_usuario": usuario_pk,
        "confederacion_territorial": "01",
        "federacion_local": "12345",
        "federacion_sectorial": "02",
        "sindicato_codigo": "003",
        "num_afiliado": NUM_AFILIADO,
        "nombre_apellidos": NOMBRE_AFILIADO,
        "lengua": "A",
        "estado": "ALTA",
        "fecha_expedicion": None,
    }
    campos.update(extra)
    return {"model": "gestion.afiliado", "pk": pk, "fields": campos}


@pytest.fixture
def archivo_volcado(tmp_path):
    def _escribir(contenido):
        ruta = tmp_path / "beta.json"
        ruta.write_text(json.dumps(contenido, ensure_ascii=False), encoding="utf-8")
        return str(ruta)
    return _escribir


def _importar(ruta, *args):
    salida = StringIO()
    call_command("importar_desde_beta", ruta, *args, stdout=salida)
    return salida.getvalue()


def _buscar(num_afiliado):
    """Localiza un afiliado por su numero, comparando en Python.

    `num_afiliado` va cifrado y `CampoTextoCifrado` prohibe expresamente
    consultarlo desde SQL: en la base solo hay texto cifrado, y un
    `filter(num_afiliado=...)` no encontraria nada aunque el dato exista. Es la
    misma restriccion que obliga al comando a deduplicar en memoria.
    """
    for afiliado in Afiliado.objects.all():
        if afiliado.num_afiliado == num_afiliado:
            return afiliado
    return None


# --- Lo que justifica el comando: que nadie repita nada ---

@pytest.mark.django_db
def test_la_contrasena_de_siempre_sigue_valiendo(archivo_volcado):
    """El punto entero de la migracion. Si esto falla, todos los sindicatos
    tienen que pedir una contrasena nueva y no se ha ahorrado nada."""
    ruta = archivo_volcado(_volcado(usuarios=[_usuario_beta()]))

    _importar(ruta)

    usuario = User.objects.get(username="sov_madrid")
    assert usuario.check_password(CLAVE_DEL_BETA), (
        "la contrasena del beta ya no vale: probablemente se ha vuelto a cifrar "
        "un hash que ya lo estaba"
    )


@pytest.mark.django_db
def test_no_tienen_que_volver_a_firmar_el_acuerdo(archivo_volcado):
    """La fecha y la IP de aceptacion son la prueba de que lo firmaron.
    Perderlas obligaria a repetir la firma y, peor, dejaria a CGT sin la
    constancia de la anterior."""
    ruta = archivo_volcado(_volcado(
        usuarios=[_usuario_beta()], perfiles=[_perfil_beta()],
    ))

    _importar(ruta)

    perfil = PerfilSindicato.objects.get(usuario__username="sov_madrid")
    assert perfil.acuerdo_aceptado is True
    assert perfil.fecha_aceptacion is not None
    assert perfil.ip_aceptacion == "203.0.113.9"


@pytest.mark.django_db
def test_los_afiliados_llegan_y_quedan_cifrados(archivo_volcado):
    """El volcado del beta trae los nombres en claro, porque es anterior al
    cifrado en reposo. Deben entrar por el ORM para que se cifren; si alguien
    optimizara esto con SQL directo, se replicaria en la base nueva justo el
    problema que el cifrado existe para evitar."""
    ruta = archivo_volcado(_volcado(
        usuarios=[_usuario_beta()], afiliados=[_afiliado_beta()],
    ))

    _importar(ruta)

    afiliado = _buscar(NUM_AFILIADO)
    assert afiliado.nombre_apellidos == NOMBRE_AFILIADO, "el ORM debe devolverlo descifrado"

    from django.db import connection
    with connection.cursor() as cur:
        cur.execute(
            'SELECT "nombre_apellidos" FROM "gestion_afiliado" WHERE "id" = %s',
            [afiliado.pk],
        )
        crudo = cur.fetchone()[0]
    assert crudo.startswith("v1$"), f"guardado en claro en la base de datos: {crudo!r}"
    assert NOMBRE_AFILIADO not in crudo


@pytest.mark.django_db
def test_cada_afiliado_queda_bajo_su_sindicato(archivo_volcado):
    """Sin esto, la migracion mezclaria los afiliados de unos sindicatos con
    otros, que es exactamente el aislamiento que el sistema garantiza."""
    ruta = archivo_volcado(_volcado(
        usuarios=[
            _usuario_beta(pk=1, username="sov_madrid", email="a@ejemplo.es"),
            _usuario_beta(pk=2, username="sov_valencia", email="b@ejemplo.es"),
        ],
        afiliados=[
            _afiliado_beta(pk=1, usuario_pk=1, num_afiliado="111111"),
            _afiliado_beta(pk=2, usuario_pk=2, num_afiliado="222222"),
        ],
    ))

    _importar(ruta)

    assert _buscar("111111").sindicato_usuario.username == "sov_madrid"
    assert _buscar("222222").sindicato_usuario.username == "sov_valencia"


# --- Robustez: esto casi nunca sale bien a la primera ---

@pytest.mark.django_db
def test_ejecutarlo_dos_veces_no_duplica_nada(archivo_volcado):
    """Una importacion se corta, se corrige y se repite. Si la segunda pasada
    duplica las cuentas y los afiliados, el remedio es peor que el problema."""
    ruta = archivo_volcado(_volcado(
        usuarios=[_usuario_beta()], perfiles=[_perfil_beta()],
        afiliados=[_afiliado_beta()],
    ))

    _importar(ruta)
    _importar(ruta)

    assert User.objects.filter(username="sov_madrid").count() == 1
    assert PerfilSindicato.objects.count() == 1
    assert Afiliado.objects.count() == 1


@pytest.mark.django_db
def test_no_pisa_la_contrasena_de_una_cuenta_que_ya_existe(archivo_volcado):
    """Si alguien ya se ha dado de alta en el sistema nuevo y cambiado la
    contrasena, la importacion no debe devolverle la del beta."""
    existente = User.objects.create_user("sov_madrid", "nuevo@ejemplo.es", "clave-nueva-999")  # noqa: S106
    ruta = archivo_volcado(_volcado(usuarios=[_usuario_beta()]))

    _importar(ruta)

    existente.refresh_from_db()
    assert existente.check_password("clave-nueva-999"), (
        "la importacion ha pisado la contrasena actual con la del beta"
    )


@pytest.mark.django_db
def test_dry_run_no_escribe_nada(archivo_volcado):
    ruta = archivo_volcado(_volcado(
        usuarios=[_usuario_beta()], afiliados=[_afiliado_beta()],
    ))

    salida = _importar(ruta, "--dry-run")

    assert User.objects.filter(username="sov_madrid").count() == 0
    assert Afiliado.objects.count() == 0
    assert "1" in salida


@pytest.mark.django_db
def test_un_afiliado_de_baja_recibe_fecha_de_baja(archivo_volcado):
    """El beta no tenia `fecha_baja`: es posterior. Sin rellenarla al importar,
    esos afiliados quedarian fuera del plazo de conservacion para siempre."""
    ruta = archivo_volcado(_volcado(
        usuarios=[_usuario_beta()],
        afiliados=[_afiliado_beta(estado="BAJA")],
    ))

    _importar(ruta)

    assert _buscar(NUM_AFILIADO).fecha_baja is not None


@pytest.mark.django_db
def test_un_afiliado_con_datos_invalidos_no_aborta_la_importacion(archivo_volcado):
    """Cuatro anios de datos reales traen sorpresas. Que una fila mal formada
    tire toda la migracion obligaria a limpiar el volcado a ciegas."""
    ruta = archivo_volcado(_volcado(
        usuarios=[_usuario_beta()],
        afiliados=[
            _afiliado_beta(pk=1, num_afiliado="AAAA", nombre_apellidos="Malo"),
            _afiliado_beta(pk=2, num_afiliado="999999"),
        ],
    ))

    salida = _importar(ruta)

    assert _buscar("999999") is not None, "el bueno debe entrar"
    assert "AAAA" not in salida, "no se vuelcan datos personales en la salida"
    assert "1" in salida


@pytest.mark.django_db
def test_avisa_de_los_afiliados_que_no_ha_podido_importar(archivo_volcado):
    """Si los descarta en silencio, alguien creera que la migracion esta
    completa cuando falta gente por el camino."""
    ruta = archivo_volcado(_volcado(
        usuarios=[_usuario_beta()],
        afiliados=[_afiliado_beta(num_afiliado="NOPE")],
    ))

    salida = _importar(ruta).lower()

    assert "no se" in salida or "descart" in salida or "error" in salida


@pytest.mark.django_db
def test_un_afiliado_sin_su_sindicato_no_se_pierde_en_silencio(archivo_volcado):
    """Referencia a un usuario que no viene en el volcado. Importarlo bajo otro
    sindicato seria mucho peor que no importarlo."""
    ruta = archivo_volcado(_volcado(
        usuarios=[_usuario_beta(pk=1)],
        afiliados=[_afiliado_beta(pk=1, usuario_pk=99)],
    ))

    salida = _importar(ruta).lower()

    assert Afiliado.objects.count() == 0
    assert "sindicato" in salida


@pytest.mark.django_db
def test_un_archivo_que_no_existe_lo_dice_claro():
    with pytest.raises(CommandError, match="no existe|No such|encontrar"):
        call_command("importar_desde_beta", "no_existe.json", stdout=StringIO())


@pytest.mark.django_db
def test_un_json_corrupto_lo_dice_claro(tmp_path):
    ruta = tmp_path / "roto.json"
    ruta.write_text("{esto no es json", encoding="utf-8")

    with pytest.raises(CommandError, match="JSON|leer|formato"):
        call_command("importar_desde_beta", str(ruta), stdout=StringIO())


@pytest.mark.django_db
def test_no_importa_cuentas_de_administrador(archivo_volcado):
    """Un superusuario del beta no tiene segundo factor configurado aqui, y el
    admin lo exige. Importarlo crearia una cuenta con todos los privilegios que
    no puede entrar, y que nadie recordaria revisar. Las de administracion se
    crean a mano con `activar_2fa`."""
    ruta = archivo_volcado(_volcado(usuarios=[
        {**_usuario_beta(pk=1, username="admin_beta", email="admin@ejemplo.es"),
         "fields": {**_usuario_beta()["fields"], "username": "admin_beta",
                    "is_superuser": True, "is_staff": True}},
    ]))

    salida = _importar(ruta).lower()

    assert not User.objects.filter(username="admin_beta").exists()
    assert "administrador" in salida or "superusuario" in salida


@pytest.mark.django_db
def test_la_salida_es_solo_ascii(archivo_volcado):
    """Consola de Windows en cp1252: mismo motivo que en los demas comandos."""
    ruta = archivo_volcado(_volcado(
        usuarios=[_usuario_beta()], perfiles=[_perfil_beta()],
        afiliados=[_afiliado_beta()],
    ))

    _importar(ruta).encode("cp1252")


@pytest.mark.django_db
def test_la_importacion_queda_auditada(archivo_volcado, caplog):
    """Entran datos personales de golpe en el sistema: tiene que constar."""
    ruta = archivo_volcado(_volcado(
        usuarios=[_usuario_beta()], afiliados=[_afiliado_beta()],
    ))

    with caplog.at_level("INFO", logger="auditoria"):
        _importar(ruta)

    registros = " ".join(r.getMessage() for r in caplog.records)
    assert "afiliados.cargados" in registros
    assert NOMBRE_AFILIADO not in registros, "el registro no lleva datos personales"


@pytest.mark.django_db
def test_una_lengua_invalida_se_rechaza(archivo_volcado):
    """El volcado real trae 344 afiliados con lenguas inexistentes y 407 con un
    codigo de federacion en `estado`. No se corrigen aqui: el comando no
    inventa datos. Esas filas se limpian en el Excel antes de subirlas."""
    ruta = archivo_volcado(_volcado(
        usuarios=[_usuario_beta()], afiliados=[_afiliado_beta(lengua="J")],
    ))

    _importar(ruta)

    assert Afiliado.objects.count() == 0


@pytest.mark.django_db
def test_se_conserva_la_fecha_de_alta_original(archivo_volcado):
    """`fecha_creacion` es `auto_now_add`, asi que al guardar se pondria la de
    hoy y todos los afiliados figurarian como dados de alta el dia de la
    migracion. Es la antiguedad de cada persona en el sindicato: no se
    recupera despues."""
    ruta = archivo_volcado(_volcado(
        usuarios=[_usuario_beta()],
        afiliados=[_afiliado_beta(fecha_creacion="2024-03-15T09:00:00Z")],
    ))

    _importar(ruta)

    assert _buscar(NUM_AFILIADO).fecha_creacion.year == 2024


@pytest.mark.django_db
def test_el_sindicato_y_la_persona_llegan_desde_la_cuenta(archivo_volcado):
    """El `perfilsindicato` del beta NO guarda ni el nombre del sindicato ni
    quien lo solicito, aunque su formulario de alta pedia ambos: acabaron en
    `first_name` y `last_name` de la cuenta. Sin recogerlos de ahi, los 39
    perfiles migrados quedarian anonimos y el administrador no sabria quien es
    quien.

    El reparto va al reves de lo que sugieren los nombres de Django: el
    sindicato esta en `last_name`. Comprobado sobre el volcado real (39 de 56
    `last_name` contienen SOV, CGT o federacion, frente a 1 de los
    `first_name`), y esta prueba lo fija para que nadie lo "arregle"."""
    volcado = _volcado(usuarios=[_usuario_beta()], perfiles=[_perfil_beta()])
    volcado[0]["fields"]["last_name"] = "SOV Madrid"
    volcado[0]["fields"]["first_name"] = "Ana Ejemplo"
    ruta = archivo_volcado(volcado)

    _importar(ruta)

    perfil = PerfilSindicato.objects.get(usuario__username="sov_madrid")
    assert perfil.nombre_identificativo == "SOV Madrid"
    assert perfil.persona_contacto == "Ana Ejemplo"
