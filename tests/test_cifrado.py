"""TDD: cifrado en reposo de los datos personales del afiliado (RGPD Art. 9).

La afiliación sindical es dato de categoría especial: si alguien se lleva una
copia del archivo de base de datos o de un backup, los nombres y números de
afiliado NO deben poder leerse.

El test central de este archivo es
`test_columna_en_bd_no_contiene_el_nombre_en_claro`: comprueba con SQL crudo
lo que hay realmente escrito en disco. Sin él, un cifrado que silenciosamente
no cifrase nada seguiría pasando todos los demás tests.
"""

import base64
from io import StringIO

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import connection
from django.test import RequestFactory

from gestion.admin import AfiliadoAdmin
from gestion.crypto import ErrorDeDescifrado, cifrar, descifrar, generar_clave
from gestion.models import Afiliado

pytestmark = pytest.mark.django_db

NOMBRE_REAL = "María Fernández Ruiz-Gómez"
NUM_AFILIADO_REAL = "480915"

_CLAVE_PRUEBAS = base64.b64encode(bytes(range(32))).decode()
_CLAVE_ANTIGUA = base64.b64encode(bytes(range(32, 64))).decode()


@pytest.fixture(autouse=True)
def claves_de_prueba(settings):
    """Clave fija para las pruebas (nunca una clave real de producción)."""
    settings.CARNETS_ENCRYPTION_KEYS = f"pruebas:{_CLAVE_PRUEBAS}"


# Proveedor de claves de mentira, en el papel del que hablaría con un KMS.
# Cuenta las veces que se le pregunta: si se le preguntase en cada campo
# descifrado, un proveedor real haría una llamada de red por fila.
_llamadas_al_proveedor = {"n": 0}


def proveedor_de_prueba():
    _llamadas_al_proveedor["n"] += 1
    return f"kms:{_CLAVE_ANTIGUA}"


def _crear_usuario(username="sindicato_cifrado"):
    return User.objects.create_user(username=username, password="clave-segura-123")  # noqa: S106


def _crear_afiliado(**overrides):
    datos = {
        "confederacion_territorial": "01",
        "federacion_local": "12345",
        "federacion_sectorial": "02",
        "sindicato_codigo": "003",
        "num_afiliado": NUM_AFILIADO_REAL,
        "nombre_apellidos": NOMBRE_REAL,
        "lengua": "A",
        "estado": "ALTA",
    }
    datos.update(overrides)
    if "sindicato_usuario" not in datos:
        # Solo se crea si no lo dio el llamante: setdefault lo crearía siempre
        # y chocaría con el username unico.
        datos["sindicato_usuario"] = _crear_usuario()
    afiliado = Afiliado(**datos)
    afiliado.full_clean(exclude=["sindicato_usuario"])
    afiliado.save()
    return afiliado


def _leer_columna_cruda(tabla, columna, pk=None):
    """Lee el valor tal cual está escrito en la BD, sin pasar por el ORM."""
    with connection.cursor() as cur:
        if pk is None:
            cur.execute(f'SELECT "{columna}" FROM "{tabla}"')  # noqa: S608 - nombres del propio modelo
            return [fila[0] for fila in cur.fetchall()]
        cur.execute(
            f'SELECT "{columna}" FROM "{tabla}" WHERE "id" = %s',  # noqa: S608
            [pk],
        )
        return cur.fetchone()[0]


# --- Primitivas de cifrado ---

def test_cifrar_y_descifrar_es_ida_y_vuelta():
    assert descifrar(cifrar(NOMBRE_REAL)) == NOMBRE_REAL


def test_el_texto_cifrado_no_deja_ver_el_original():
    cifrado = cifrar(NOMBRE_REAL)
    assert NOMBRE_REAL not in cifrado
    assert "Fernández" not in cifrado


def test_cifrar_dos_veces_da_resultados_distintos():
    # Cifrado no determinista: dos afiliados con el mismo nombre no producen
    # el mismo texto cifrado, así que no se puede deducir nada comparando filas.
    assert cifrar(NOMBRE_REAL) != cifrar(NOMBRE_REAL)


def test_descifrar_detecta_manipulacion_del_texto_cifrado():
    version, clave_id, cuerpo = cifrar(NOMBRE_REAL).split("$")
    crudo = bytearray(base64.b64decode(cuerpo))
    crudo[-1] ^= 0x01  # un solo bit alterado
    manipulado = f"{version}${clave_id}${base64.b64encode(bytes(crudo)).decode()}"
    with pytest.raises(ErrorDeDescifrado):
        descifrar(manipulado)


def test_sin_claves_configuradas_falla_en_vez_de_guardar_en_claro(settings):
    # El peor fallo posible sería guardar en claro sin avisar: debe reventar.
    settings.CARNETS_ENCRYPTION_KEYS = ""
    with pytest.raises(Exception):  # noqa: B017 - lo que no vale es que pase sin error
        cifrar(NOMBRE_REAL)


def test_generar_clave_produce_claves_de_256_bits():
    assert len(base64.b64decode(generar_clave())) == 32
    assert generar_clave() != generar_clave()


# --- Lo que hay realmente escrito en disco ---

def test_columna_en_bd_no_contiene_el_nombre_en_claro():
    afiliado = _crear_afiliado()
    crudo = _leer_columna_cruda("gestion_afiliado", "nombre_apellidos", pk=afiliado.pk)
    assert NOMBRE_REAL not in str(crudo)
    assert "Fernández" not in str(crudo)


def test_columna_en_bd_no_contiene_el_numero_de_afiliado_en_claro():
    afiliado = _crear_afiliado()
    crudo = _leer_columna_cruda("gestion_afiliado", "num_afiliado", pk=afiliado.pk)
    assert NUM_AFILIADO_REAL not in str(crudo)


def test_el_historial_de_auditoria_tambien_esta_cifrado():
    # django-simple-history duplica los campos en su tabla: de nada sirve
    # cifrar el afiliado si su historial guarda el nombre en claro.
    _crear_afiliado()
    tabla_historial = Afiliado.history.model._meta.db_table
    valores = _leer_columna_cruda(tabla_historial, "nombre_apellidos")
    assert valores, "el historial deberia tener al menos una fila"
    for valor in valores:
        assert NOMBRE_REAL not in str(valor)


def test_leer_desde_el_orm_devuelve_el_texto_en_claro():
    afiliado = _crear_afiliado()
    recuperado = Afiliado.objects.get(pk=afiliado.pk)
    assert recuperado.nombre_apellidos == NOMBRE_REAL
    assert recuperado.num_afiliado == NUM_AFILIADO_REAL


def test_notas_historicas_tambien_se_cifran():
    nota = "Reemision 2024 por perdida"
    afiliado = _crear_afiliado(notas_historicas=nota)
    crudo = _leer_columna_cruda("gestion_afiliado", "notas_historicas", pk=afiliado.pk)
    assert "Reemision" not in str(crudo)
    assert Afiliado.objects.get(pk=afiliado.pk).notas_historicas == nota


# --- Rotación de claves (RGPD: rotación trimestral) ---

def test_lo_cifrado_con_la_clave_anterior_sigue_leyendose_tras_rotar(settings):
    settings.CARNETS_ENCRYPTION_KEYS = f"antigua:{_CLAVE_ANTIGUA}"
    cifrado_con_la_antigua = cifrar(NOMBRE_REAL)

    # Se rota: la nueva clave pasa a ser la activa, la antigua se conserva
    # solo para poder descifrar lo que ya estaba guardado.
    settings.CARNETS_ENCRYPTION_KEYS = f"nueva:{_CLAVE_PRUEBAS},antigua:{_CLAVE_ANTIGUA}"

    assert descifrar(cifrado_con_la_antigua) == NOMBRE_REAL
    assert cifrar(NOMBRE_REAL).startswith("v1$nueva$")


# --- Proveedor de claves (el seam por el que entra el KMS) ---

def test_se_usan_las_claves_que_da_el_proveedor(settings):
    settings.CARNETS_KEY_PROVIDER = "tests.test_cifrado.proveedor_de_prueba"
    cifrado = cifrar(NOMBRE_REAL)
    assert cifrado.startswith("v1$kms$")
    assert descifrar(cifrado) == NOMBRE_REAL


def test_al_proveedor_solo_se_le_pregunta_una_vez(settings):
    # Con un KMS de verdad cada consulta es una llamada de red. Sin caché, una
    # sola búsqueda en el admin dispararía miles.
    settings.CARNETS_KEY_PROVIDER = "tests.test_cifrado.proveedor_de_prueba"
    _llamadas_al_proveedor["n"] = 0

    for _ in range(5):
        descifrar(cifrar(NOMBRE_REAL))

    assert _llamadas_al_proveedor["n"] == 1


def test_cambiar_de_proveedor_descarta_las_claves_cacheadas(settings):
    settings.CARNETS_KEY_PROVIDER = "tests.test_cifrado.proveedor_de_prueba"
    assert cifrar(NOMBRE_REAL).startswith("v1$kms$")

    settings.CARNETS_KEY_PROVIDER = "gestion.crypto.proveedor_desde_entorno"
    assert cifrar(NOMBRE_REAL).startswith("v1$pruebas$")


def test_un_proveedor_que_no_existe_falla_con_un_mensaje_claro(settings):
    settings.CARNETS_KEY_PROVIDER = "gestion.crypto.proveedor_que_no_existe"
    with pytest.raises(ImproperlyConfigured, match="CARNETS_KEY_PROVIDER"):
        cifrar(NOMBRE_REAL)


def test_reencriptar_pasa_los_datos_antiguos_a_la_clave_activa(settings):
    # Sin esto, la clave antigua nunca se podría retirar: mientras quede una
    # fila cifrada con ella, borrarla dejaria ese dato irrecuperable.
    settings.CARNETS_ENCRYPTION_KEYS = f"antigua:{_CLAVE_ANTIGUA}"
    afiliado = _crear_afiliado()
    assert _leer_columna_cruda(
        "gestion_afiliado", "nombre_apellidos", pk=afiliado.pk,
    ).startswith("v1$antigua$")

    settings.CARNETS_ENCRYPTION_KEYS = f"nueva:{_CLAVE_PRUEBAS},antigua:{_CLAVE_ANTIGUA}"
    call_command("reencriptar_afiliados", stdout=StringIO())

    crudo = _leer_columna_cruda("gestion_afiliado", "nombre_apellidos", pk=afiliado.pk)
    assert crudo.startswith("v1$nueva$")
    assert Afiliado.objects.get(pk=afiliado.pk).nombre_apellidos == NOMBRE_REAL

    historial = _leer_columna_cruda(Afiliado.history.model._meta.db_table, "nombre_apellidos")
    assert all(str(v).startswith("v1$nueva$") for v in historial)


def test_reencriptar_en_seco_no_escribe_nada(settings):
    settings.CARNETS_ENCRYPTION_KEYS = f"antigua:{_CLAVE_ANTIGUA}"
    afiliado = _crear_afiliado()

    settings.CARNETS_ENCRYPTION_KEYS = f"nueva:{_CLAVE_PRUEBAS},antigua:{_CLAVE_ANTIGUA}"
    salida = StringIO()
    call_command("reencriptar_afiliados", "--dry-run", stdout=salida)

    assert _leer_columna_cruda(
        "gestion_afiliado", "nombre_apellidos", pk=afiliado.pk,
    ).startswith("v1$antigua$")
    assert "Simulación" in salida.getvalue()


# --- Validaciones que NO deben perderse al cambiar el tipo de campo ---

def test_se_conserva_el_limite_de_longitud_del_nombre():
    # Regresión: un TextField no valida max_length por sí solo. Sin esta
    # comprobación, un Excel podría colar un nombre de megabytes.
    with pytest.raises(ValidationError) as e:
        _crear_afiliado(nombre_apellidos="A" * 256)
    assert "nombre_apellidos" in e.value.message_dict


def test_se_conserva_el_formato_del_numero_de_afiliado():
    with pytest.raises(ValidationError) as e:
        _crear_afiliado(num_afiliado="12")
    assert "num_afiliado" in e.value.message_dict


# --- El admin debe seguir siendo usable ---

def test_el_buscador_del_admin_encuentra_por_nombre():
    afiliado = _crear_afiliado()
    _crear_afiliado(
        sindicato_usuario=_crear_usuario("otro_sindicato"),
        nombre_apellidos="Otra Persona Distinta",
        num_afiliado="111111",
    )

    admin_obj = AfiliadoAdmin(Afiliado, AdminSite())
    peticion = RequestFactory().get("/admin/gestion/afiliado/")
    peticion.user = afiliado.sindicato_usuario
    resultado, _ = admin_obj.get_search_results(peticion, Afiliado.objects.all(), "Fernández")

    assert list(resultado.values_list("pk", flat=True)) == [afiliado.pk]


def test_el_buscador_del_admin_encuentra_por_numero_de_afiliado():
    afiliado = _crear_afiliado()
    _crear_afiliado(
        sindicato_usuario=_crear_usuario("otro_sindicato"),
        nombre_apellidos="Otra Persona Distinta",
        num_afiliado="111111",
    )

    admin_obj = AfiliadoAdmin(Afiliado, AdminSite())
    peticion = RequestFactory().get("/admin/gestion/afiliado/")
    peticion.user = afiliado.sindicato_usuario
    resultado, _ = admin_obj.get_search_results(
        peticion, Afiliado.objects.all(), NUM_AFILIADO_REAL,
    )

    assert list(resultado.values_list("pk", flat=True)) == [afiliado.pk]
