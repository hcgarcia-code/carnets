"""El backup nunca deja datos personales en claro en el disco.

El comando genera un `dumpdata`, que **lee a traves del ORM** y por tanto sale
con los nombres y numeros de afiliado ya descifrados. Ese texto en claro es
exactamente lo que el cifrado en reposo existe para evitar que quede escrito en
ningun sitio: si acaba en un archivo del servidor, el backup cifrado se
convierte en la via mas comoda para saltarse el cifrado de la base de datos.

La version anterior lo escribia en un temporal que **no leia nadie** (Vault
cifra desde memoria y a S3 sube el resultado), y lo borraba en la ultima linea
del camino de exito. Cualquier fallo intermedio --Vault caido, credenciales
caducadas, un corte de red con S3-- dejaba ese volcado en el disco
indefinidamente, y al ejecutarse desde cron se acumulaba uno por semana.
"""

import glob
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import CommandError, call_command

# Importado explicitamente para que patch() pueda resolver la ruta: los modulos
# de comandos no estan cargados hasta que Django los busca al invocarlos.
import gestion.management.commands.backup_a_s3_cifrado  # noqa: F401

MODULO = "gestion.management.commands.backup_a_s3_cifrado"


@pytest.fixture
def vault_y_s3(monkeypatch):
    """Sustituye Vault y S3 por dobles: ninguna prueba sale a la red."""
    monkeypatch.setenv("BACKUP_VAULT_ROLE_ID", "rol-de-prueba")
    monkeypatch.setenv("BACKUP_VAULT_SECRET_ID", "secreto-de-prueba")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "clave-de-prueba")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secreto-s3-de-prueba")

    vault = MagicMock()
    vault.secrets.transit.encrypt_data.return_value = {
        "data": {"ciphertext": "vault:v1:textoCifradoDePrueba=="},
    }
    s3 = MagicMock()
    s3.list_objects_v2.return_value = {}

    with patch(f"{MODULO}.hvac.Client", return_value=vault) as cliente_vault, \
         patch(f"{MODULO}.boto3.client", return_value=s3):
        yield {"vault": vault, "s3": s3, "cliente_vault": cliente_vault}


def _temporales_de_backup():
    return glob.glob(f"{tempfile.gettempdir()}/backup_carnets_*")


@pytest.mark.django_db
def test_no_escribe_el_volcado_en_claro_en_el_disco(vault_y_s3):
    """El dumpdata sale descifrado del ORM: no debe tocar el disco jamas.

    Se comprueba que ni siquiera se crea el archivo, en vez de que se borre al
    final: un archivo que se escribe y luego se limpia sigue estando en disco
    mientras dura el comando, y ahi es donde ocurren los fallos.
    """
    antes = set(_temporales_de_backup())

    call_command("backup_a_s3_cifrado", "--s3-bucket", "cubo", stdout=StringIO())

    assert set(_temporales_de_backup()) == antes

    # El comando ni siquiera dispone de las herramientas para escribirlo: no
    # importa tempfile ni abre nada en escritura. Comprobarlo sobre el codigo
    # fuente vale mas que observar el resultado, porque un archivo creado y
    # borrado dentro del comando pasaria la comprobacion de arriba y aun asi
    # habria estado en disco durante toda la ejecucion, que es cuando fallan
    # las cosas.
    fuente = Path(gestion.management.commands.backup_a_s3_cifrado.__file__).read_text(
        encoding="utf-8",
    )
    codigo = "\n".join(
        linea for linea in fuente.splitlines() if not linea.strip().startswith("#")
    )
    for prohibido in ("tempfile", "mkstemp", "NamedTemporary"):
        assert prohibido not in codigo, (
            f"El comando vuelve a usar {prohibido}: el volcado en claro no debe tocar el disco."
        )


@pytest.mark.django_db
def test_no_deja_nada_en_disco_cuando_vault_falla(vault_y_s3):
    """El caso que motivo el cambio: el fallo ocurre DESPUES de generar el
    volcado, que es justo cuando el texto en claro ya existe."""
    vault_y_s3["vault"].secrets.transit.encrypt_data.side_effect = RuntimeError("Vault caido")
    antes = set(_temporales_de_backup())

    with pytest.raises(RuntimeError):
        call_command("backup_a_s3_cifrado", "--s3-bucket", "cubo", stdout=StringIO())

    assert set(_temporales_de_backup()) == antes


@pytest.mark.django_db
def test_lo_que_sube_a_s3_es_el_texto_cifrado(vault_y_s3):
    """Comprobacion elemental pero que conviene fijar: si algun dia alguien
    cambia el Body por json_plaintext, el backup entero pasa a estar en claro
    en S3 sin que nada falle."""
    call_command("backup_a_s3_cifrado", "--s3-bucket", "cubo", stdout=StringIO())

    _, kwargs = vault_y_s3["s3"].put_object.call_args
    assert kwargs["Body"] == "vault:v1:textoCifradoDePrueba=="
    assert kwargs["ServerSideEncryption"] == "AES256"
    assert kwargs["Key"].endswith(".json.enc")


@pytest.mark.django_db
def test_dry_run_no_sube_nada(vault_y_s3):
    call_command("backup_a_s3_cifrado", "--s3-bucket", "cubo", "--dry-run", stdout=StringIO())

    vault_y_s3["s3"].put_object.assert_not_called()
    vault_y_s3["s3"].delete_object.assert_not_called()


@pytest.mark.django_db
def test_la_salida_es_solo_ascii(vault_y_s3):
    """La consola de Windows usa cp1252. Un caracter fuera de ese juego aborta
    el comando, y aqui lo haria DESPUES de haber subido ya el objeto a S3: el
    operador ve una traza de error y concluye que el backup fallo cuando en
    realidad esta hecho. Misma trampa que en preparar_pruebas."""
    salida = StringIO()

    call_command("backup_a_s3_cifrado", "--s3-bucket", "cubo", stdout=salida)

    salida.getvalue().encode("cp1252")


@pytest.mark.django_db
def test_exige_el_cubo_de_s3(vault_y_s3, monkeypatch):
    monkeypatch.delenv("BACKUP_S3_BUCKET", raising=False)

    with pytest.raises(CommandError, match="BACKUP_S3_BUCKET"):
        call_command("backup_a_s3_cifrado", stdout=StringIO())
