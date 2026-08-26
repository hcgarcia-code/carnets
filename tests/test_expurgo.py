"""Expurgado de afiliados de baja: el plazo de conservacion, ejecutable.

La EIPD fija que los datos de un afiliado se anonimizan tres anios despues de
su baja (RGPD Art. 5.1.e, limitacion del plazo de conservacion, y Art. 17,
derecho de supresion). Estaba escrito y no era ejecutable: `Afiliado` tenia
`estado` con ALTA/BAJA pero ningun sello de CUANDO paso a baja, asi que no
habia desde que contar. El procedimiento de la EIPD consultaba un campo
`fecha_cancelacion` que no existia en el modelo.

Dos piezas, y la segunda es la que de verdad importa:

1. `fecha_baja`, que se sella solo al pasar a BAJA.
2. `expurgar_afiliados`, que anonimiza la fila **y todo su historial**.

Sin lo segundo el expurgado seria teatro: `HistoricalRecords()` guarda una
copia de cada version del afiliado para siempre, asi que anonimizar la fila
viva deja el nombre anterior intacto en `gestion_historicalafiliado`. Cifrado,
si, pero recuperable con la clave: exactamente el dato que se acaba de
prometer suprimir.
"""

from datetime import timedelta
from io import StringIO

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

from gestion.crypto import MARCA_NO_DESCIFRABLE
from gestion.models import Afiliado

NOMBRE = "Maria Ejemplo Apellido"
NUM_AFILIADO = "123456"


def _usuario(nombre="sindicato_expurgo"):
    return User.objects.create_user(username=nombre, password="clave-segura-123")  # noqa: S106


def _crear_afiliado(usuario=None, **overrides):
    datos = {
        "confederacion_territorial": "01",
        "federacion_local": "12345",
        "federacion_sectorial": "02",
        "sindicato_codigo": "003",
        "num_afiliado": NUM_AFILIADO,
        "nombre_apellidos": NOMBRE,
        "lengua": "A",
        "estado": "ALTA",
        "sindicato_usuario": usuario or _usuario(),
    }
    datos.update(overrides)
    afiliado = Afiliado(**datos)
    afiliado.full_clean(exclude=["sindicato_usuario"])
    afiliado.save()
    return afiliado


def _dar_de_baja(afiliado, hace_anios=0):
    afiliado.estado = "BAJA"
    afiliado.save()
    if hace_anios:
        # Se retrasa la fecha a mano en vez de esperar tres anios.
        Afiliado.objects.filter(pk=afiliado.pk).update(
            fecha_baja=timezone.now() - timedelta(days=365 * hace_anios),
        )
        afiliado.refresh_from_db()
    return afiliado


# --- 1. El sello de la fecha de baja ---

@pytest.mark.django_db
def test_un_afiliado_de_alta_no_tiene_fecha_de_baja():
    assert _crear_afiliado().fecha_baja is None


@pytest.mark.django_db
def test_pasar_a_baja_sella_la_fecha():
    """Es el unico momento en que se puede saber la fecha. Si no se captura
    aqui, se pierde para siempre y el afiliado queda inexpurgable."""
    afiliado = _crear_afiliado()

    afiliado.estado = "BAJA"
    afiliado.save()

    assert afiliado.fecha_baja is not None


@pytest.mark.django_db
def test_una_baja_que_llega_por_excel_tambien_lleva_fecha():
    """La subida de Excel no pasa por save(): construye los objetos y los
    persiste con bulk_create_with_history. Un afiliado que ya viene de BAJA en
    el archivo tiene que sellarse igual, o toda esa via queda sin plazo."""
    afiliado = Afiliado(
        sindicato_usuario=_usuario(),
        confederacion_territorial="01",
        federacion_local="12345",
        federacion_sectorial="02",
        sindicato_codigo="003",
        num_afiliado=NUM_AFILIADO,
        nombre_apellidos=NOMBRE,
        lengua="A",
        estado="BAJA",
    )

    afiliado.full_clean(exclude=["sindicato_usuario"])

    assert afiliado.fecha_baja is not None, (
        "full_clean es el punto por el que pasa la carga de Excel: si no sella "
        "aqui, los afiliados subidos como BAJA nunca se podran expurgar."
    )


@pytest.mark.django_db
def test_volver_a_dar_de_alta_borra_la_fecha():
    """Una reafiliacion reinicia el plazo: conservar la fecha de la baja
    anterior acabaria anonimizando a alguien que esta afiliado ahora mismo."""
    afiliado = _dar_de_baja(_crear_afiliado())

    afiliado.estado = "ALTA"
    afiliado.save()

    assert afiliado.fecha_baja is None


@pytest.mark.django_db
def test_una_segunda_grabacion_no_mueve_la_fecha():
    """Cualquier edicion posterior (corregir la lengua, por ejemplo) volveria a
    poner el reloj a cero y el plazo no venceria nunca."""
    afiliado = _dar_de_baja(_crear_afiliado(), hace_anios=4)
    fecha = afiliado.fecha_baja

    afiliado.lengua = "C"
    afiliado.save()
    afiliado.refresh_from_db()

    assert afiliado.fecha_baja == fecha


# --- 2. El expurgado ---

@pytest.mark.django_db
def test_una_baja_antigua_se_anonimiza():
    afiliado = _dar_de_baja(_crear_afiliado(), hace_anios=4)

    call_command("expurgar_afiliados", stdout=StringIO())

    afiliado.refresh_from_db()
    assert NOMBRE not in afiliado.nombre_apellidos
    assert afiliado.num_afiliado != NUM_AFILIADO


@pytest.mark.django_db
def test_el_historial_tambien_se_anonimiza():
    """La prueba que justifica el comando entero.

    simple_history guarda una copia de cada version. Anonimizar solo la fila
    viva deja el nombre original en el historial, y ahi sigue estando el dato
    que se acaba de declarar suprimido.
    """
    afiliado = _crear_afiliado()
    afiliado.nombre_apellidos = "Maria Ejemplo Corregido"
    afiliado.save()  # ya van dos versiones en el historial
    _dar_de_baja(afiliado, hace_anios=4)

    call_command("expurgar_afiliados", stdout=StringIO())

    nombres = [v.nombre_apellidos for v in Afiliado.history.filter(id=afiliado.pk)]
    assert nombres, "el afiliado tenia historial: si sale vacio la prueba no comprueba nada"
    assert all(NOMBRE not in n for n in nombres), (
        f"queda el nombre original en el historial: {nombres}"
    )


@pytest.mark.django_db
def test_lo_anonimizado_queda_cifrado_como_todo_lo_demas():
    """El comando anonimiza con queryset.update(), no con save().

    Que `update()` pase por el cifrado del campo es una suposicion que hay que
    comprobar, y su fallo seria silencioso: si escribiera en claro, al leer
    despues no habria texto cifrado que descifrar y el campo devolveria el
    marcador de "no descifrable". Ese marcador tampoco contiene el nombre
    original, asi que las demas pruebas de este archivo pasarian igual mientras
    la fila queda envenenada: a partir de ahi cualquier intento de guardar ese
    afiliado revienta con ErrorDeDescifrado.
    """
    afiliado = _dar_de_baja(_crear_afiliado(), hace_anios=4)

    call_command("expurgar_afiliados", stdout=StringIO())

    with connection.cursor() as cur:
        cur.execute(
            'SELECT "nombre_apellidos" FROM "gestion_afiliado" WHERE "id" = %s',
            [afiliado.pk],
        )
        crudo = cur.fetchone()[0]
        cur.execute(
            'SELECT "nombre_apellidos" FROM "gestion_historicalafiliado" WHERE "id" = %s',
            [afiliado.pk],
        )
        historicos = [fila[0] for fila in cur.fetchall()]

    assert crudo.startswith("v1$"), f"escrito sin cifrar en la fila viva: {crudo!r}"
    assert historicos, "el afiliado tenia historial"
    for valor in historicos:
        assert valor.startswith("v1$"), f"escrito sin cifrar en el historial: {valor!r}"

    afiliado.refresh_from_db()
    assert MARCA_NO_DESCIFRABLE not in afiliado.nombre_apellidos


@pytest.mark.django_db
def test_una_baja_reciente_no_se_toca():
    """El plazo existe porque los datos hacen falta durante el (conflictos
    laborales). Expurgar antes de tiempo incumple igual que expurgar tarde."""
    afiliado = _dar_de_baja(_crear_afiliado(), hace_anios=1)

    call_command("expurgar_afiliados", stdout=StringIO())

    afiliado.refresh_from_db()
    assert afiliado.nombre_apellidos == NOMBRE


@pytest.mark.django_db
def test_un_afiliado_de_alta_no_se_toca_por_antiguo_que_sea():
    afiliado = _crear_afiliado()
    Afiliado.objects.filter(pk=afiliado.pk).update(
        fecha_creacion=timezone.now() - timedelta(days=365 * 10),
    )

    call_command("expurgar_afiliados", stdout=StringIO())

    afiliado.refresh_from_db()
    assert afiliado.nombre_apellidos == NOMBRE


@pytest.mark.django_db
def test_una_baja_sin_fecha_no_se_expurga_pero_se_avisa():
    """Filas anteriores a que existiera `fecha_baja`. No se puede saber cuando
    caducan, asi que no se tocan; pero callarlo las dejaria invisibles para
    siempre, que es justo el incumplimiento que este comando viene a cerrar."""
    afiliado = _dar_de_baja(_crear_afiliado())
    Afiliado.objects.filter(pk=afiliado.pk).update(fecha_baja=None)
    salida = StringIO()

    call_command("expurgar_afiliados", stdout=salida)

    afiliado.refresh_from_db()
    assert afiliado.nombre_apellidos == NOMBRE, "sin fecha no hay plazo que vencer"
    assert "sin fecha" in salida.getvalue().lower()


@pytest.mark.django_db
def test_dry_run_no_cambia_nada():
    """Se destruyen datos de forma irreversible: hay que poder ver a cuantos
    afecta antes de lanzarlo."""
    afiliado = _dar_de_baja(_crear_afiliado(), hace_anios=4)
    salida = StringIO()

    call_command("expurgar_afiliados", "--dry-run", stdout=salida)

    afiliado.refresh_from_db()
    assert afiliado.nombre_apellidos == NOMBRE
    assert "1" in salida.getvalue()


@pytest.mark.django_db
def test_el_plazo_se_puede_ajustar():
    afiliado = _dar_de_baja(_crear_afiliado(), hace_anios=2)

    call_command("expurgar_afiliados", "--anios", "1", stdout=StringIO())

    afiliado.refresh_from_db()
    assert afiliado.nombre_apellidos != NOMBRE


@pytest.mark.django_db
def test_queda_registrado_en_auditoria(caplog):
    """La EIPD lo exige: cada expurgado anotado. Es tambien la unica prueba de
    haber cumplido el plazo, porque despues de expurgar no queda nada que
    ensenar."""
    afiliado = _dar_de_baja(_crear_afiliado(), hace_anios=4)

    with caplog.at_level("INFO", logger="auditoria"):
        call_command("expurgar_afiliados", stdout=StringIO())

    registros = " ".join(r.getMessage() for r in caplog.records)
    assert "afiliados.expurgados" in registros
    assert NOMBRE not in registros, "el registro de auditoria no lleva datos personales"
    assert str(afiliado.pk) in registros


@pytest.mark.django_db
def test_la_fecha_de_baja_no_se_puede_editar_a_mano_en_el_admin():
    """Es el reloj del que depende una operacion irreversible. Un dedazo en el
    anio al editar un afiliado adelantaria su anonimizacion, y no hay vuelta
    atras. La rellena el modelo; a mano no se toca."""
    from django.contrib import admin as django_admin

    from gestion.models import Afiliado as ModeloAfiliado

    opciones = django_admin.site._registry[ModeloAfiliado]

    assert "fecha_baja" in opciones.readonly_fields


@pytest.mark.django_db
def test_la_salida_es_solo_ascii():
    """Consola de Windows en cp1252: mismo motivo que en los demas comandos, y
    aqui reventaria DESPUES de haber anonimizado, que es irreversible."""
    _dar_de_baja(_crear_afiliado(), hace_anios=4)
    salida = StringIO()

    call_command("expurgar_afiliados", stdout=salida)

    salida.getvalue().encode("cp1252")
