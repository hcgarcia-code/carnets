"""Cifrado en reposo de datos personales (RGPD Art. 9).

La afiliación sindical es dato de categoría especial: quien consiga una copia
del archivo de base de datos o de un backup no debe poder leer nombres ni
números de afiliado. Este módulo cifra esos campos a nivel de columna, de modo
que lo que se escribe en disco es texto cifrado y el descifrado ocurre solo en
memoria, al leer desde el ORM.

Algoritmo: AES-256-GCM (cifrado autenticado). GCM detecta cualquier
manipulación del texto cifrado, así que además de confidencialidad da
integridad: nadie puede alterar un nombre editando la BD sin que salte el
error.

Formato almacenado:  v1$<id_de_clave>$<base64(nonce || texto_cifrado)>

El identificador de clave viaja con el dato, así que se pueden tener varias
claves vivas a la vez: la primera de la lista es la que cifra, y las demás se
conservan solo para poder descifrar lo guardado antes de la última rotación.
Eso es lo que permite rotar claves trimestralmente sin reescribir toda la BD
de golpe.

Origen de las claves: el proveedor
---------------------------------
De dónde salen las claves lo decide `settings.CARNETS_KEY_PROVIDER`, la ruta
de un invocable sin argumentos que devuelve la cadena
`id:clave_base64,id:clave_base64` (la primera es la activa).

Por defecto es `proveedor_desde_entorno`, que la lee del `.env`: suficiente
para desarrollo local, NO para datos reales. En producción el material
criptográfico debe custodiarlo un KMS/HSM (AWS KMS, Azure Key Vault, HashiCorp
Vault), que es el único punto que lo guarda y el que audita cada acceso.

Cambiar de uno a otro es cambiar un ajuste: ni este módulo ni el resto de la
aplicación se enteran. En `deploy/claves_y_kms.md` hay implementaciones
completas y copiables para los tres proveedores.

El resultado del proveedor se cachea en memoria a propósito: un proveedor de
KMS hace una llamada de red, y sin caché se invocaría una vez por cada campo
descifrado (miles de veces en una sola búsqueda del admin). Como consecuencia,
tras rotar claves hay que reiniciar el proceso para que las lea.

ponytail: mientras el proveedor activo sea el del entorno, la clave está tan
protegida como el propio `.env` del servidor, que es menos de lo que exige el
Art. 32 RGPD. Sustituirlo por el del KMS antes de tratar datos reales.
"""

import base64
import logging
import os
from functools import lru_cache

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.exceptions import FieldError, ImproperlyConfigured
from django.core.signals import setting_changed
from django.core.validators import MaxLengthValidator
from django.db import models
from django.dispatch import receiver
from django.utils.functional import cached_property
from django.utils.module_loading import import_string

VERSION_FORMATO = "v1"
TAMANO_CLAVE_BYTES = 32  # AES-256
TAMANO_NONCE_BYTES = 12  # tamaño recomendado para GCM
SEPARADOR = "$"


logger = logging.getLogger(__name__)

MARCA_NO_DESCIFRABLE = "⟨no descifrable⟩"


class ErrorDeDescifrado(Exception):
    """El texto cifrado no se pudo descifrar: clave desconocida o manipulado."""


class TextoNoDescifrable(str):
    """Ocupa el lugar de un valor que no se pudo descifrar.

    Es un str para que la aplicación pueda seguir mostrando el registro (una
    fila ilegible no debe impedir ver las demás), pero de un tipo propio para
    poder reconocerlo con certeza al escribir y negarse a guardarlo encima del
    dato original. Un usuario que teclee ese mismo texto produce un str normal,
    así que no hay forma de confundirlos.
    """


def generar_clave() -> str:
    """Devuelve una clave AES-256 nueva, en base64, lista para el .env o el KMS."""
    return base64.b64encode(os.urandom(TAMANO_CLAVE_BYTES)).decode()


@lru_cache(maxsize=4)
def _parsear_claves(configuracion: str) -> tuple[tuple[str, bytes], ...]:
    """Convierte 'id:base64,id:base64' en (('id', clave_en_bytes), ...).

    Se cachea por el texto de configuración, de modo que cambiarlo (en las
    pruebas, o tras una rotación) invalida la entrada anterior por sí solo.
    """
    claves = []
    for trozo in configuracion.split(","):
        trozo = trozo.strip()
        if not trozo:
            continue
        if ":" not in trozo:
            raise ImproperlyConfigured(
                "CARNETS_ENCRYPTION_KEYS mal formado: se esperaba 'id:clave_base64'.",
            )
        clave_id, _, clave_b64 = trozo.partition(":")
        clave_id = clave_id.strip()
        if SEPARADOR in clave_id:
            raise ImproperlyConfigured(
                f"El identificador de clave no puede contener '{SEPARADOR}': {clave_id!r}.",
            )
        try:
            clave = base64.b64decode(clave_b64.strip(), validate=True)
        except (ValueError, TypeError) as exc:
            raise ImproperlyConfigured(
                f"La clave de cifrado {clave_id!r} no es base64 válido.",
            ) from exc
        if len(clave) != TAMANO_CLAVE_BYTES:
            raise ImproperlyConfigured(
                f"La clave de cifrado {clave_id!r} debe ser de {TAMANO_CLAVE_BYTES} "
                f"bytes (AES-256); tiene {len(clave)}.",
            )
        claves.append((clave_id, clave))

    if not claves:
        # Sin claves NO se guarda en claro: se para. Guardar datos personales
        # sin cifrar por un despiste de configuración es el peor fallo posible.
        raise ImproperlyConfigured(
            "No hay claves de cifrado configuradas (CARNETS_ENCRYPTION_KEYS). "
            "Genera una con: python -c \"from gestion.crypto import generar_clave; "
            "print(generar_clave())\"",
        )
    return tuple(claves)


PROVEEDOR_POR_DEFECTO = "gestion.crypto.proveedor_desde_entorno"

# Resultado del proveedor, cacheado para no repetir la llamada (que en un KMS
# es de red) en cada campo que se descifra. Se vacía solo cuando cambian los
# ajustes implicados, de modo que las pruebas puedan sustituir el proveedor.
_configuracion_cacheada: str | None = None


def proveedor_desde_entorno() -> str:
    """Proveedor por defecto: lee las claves de la configuración (vía .env).

    Vale para desarrollo local. Para datos reales debe sustituirse por un
    proveedor de KMS: ver deploy/claves_y_kms.md.
    """
    return getattr(settings, "CARNETS_ENCRYPTION_KEYS", "") or ""


def limpiar_cache_de_claves(**_kwargs) -> None:
    """Olvida las claves cacheadas; se volverán a pedir al proveedor."""
    global _configuracion_cacheada
    _configuracion_cacheada = None
    _parsear_claves.cache_clear()


@receiver(setting_changed)
def _al_cambiar_los_ajustes(sender, setting, **kwargs):
    if setting in ("CARNETS_ENCRYPTION_KEYS", "CARNETS_KEY_PROVIDER"):
        limpiar_cache_de_claves()


def _configuracion_de_claves() -> str:
    global _configuracion_cacheada
    if _configuracion_cacheada is None:
        ruta = getattr(settings, "CARNETS_KEY_PROVIDER", "") or PROVEEDOR_POR_DEFECTO
        try:
            proveedor = import_string(ruta)
        except ImportError as exc:
            raise ImproperlyConfigured(
                f"CARNETS_KEY_PROVIDER apunta a {ruta!r}, que no se puede importar.",
            ) from exc
        _configuracion_cacheada = proveedor() or ""
    return _configuracion_cacheada


def _claves() -> tuple[tuple[str, bytes], ...]:
    return _parsear_claves(_configuracion_de_claves())


def clave_activa_id() -> str:
    """Identificador de la clave con la que se cifra ahora mismo."""
    return _claves()[0][0]


def cifrar(texto: str) -> str:
    """Cifra un texto y devuelve la cadena a almacenar en la base de datos."""
    clave_id, clave = _claves()[0]  # la primera es la activa
    nonce = os.urandom(TAMANO_NONCE_BYTES)
    cifrado = AESGCM(clave).encrypt(nonce, texto.encode("utf-8"), None)
    cuerpo = base64.b64encode(nonce + cifrado).decode()
    return f"{VERSION_FORMATO}{SEPARADOR}{clave_id}{SEPARADOR}{cuerpo}"


def descifrar(almacenado: str) -> str:
    """Descifra un valor leído de la base de datos.

    Lanza ErrorDeDescifrado si el formato no es el esperado, si la clave con la
    que se cifró ya no está configurada, o si el texto cifrado fue manipulado.
    """
    partes = almacenado.split(SEPARADOR)
    if len(partes) != 3 or partes[0] != VERSION_FORMATO:
        raise ErrorDeDescifrado(
            "El valor almacenado no tiene el formato de un dato cifrado "
            f"({VERSION_FORMATO}$id$datos).",
        )
    _, clave_id, cuerpo = partes

    for identificador, clave in _claves():
        if identificador != clave_id:
            continue
        try:
            crudo = base64.b64decode(cuerpo, validate=True)
        except (ValueError, TypeError) as exc:
            raise ErrorDeDescifrado("El cuerpo del dato cifrado no es base64 válido.") from exc
        nonce, cifrado = crudo[:TAMANO_NONCE_BYTES], crudo[TAMANO_NONCE_BYTES:]
        try:
            return AESGCM(clave).decrypt(nonce, cifrado, None).decode("utf-8")
        except InvalidTag as exc:
            # GCM ha detectado que el dato no es auténtico: o se manipuló la
            # base de datos, o la clave no es la que se usó para cifrarlo.
            raise ErrorDeDescifrado(
                f"El dato cifrado con la clave {clave_id!r} está manipulado o corrupto.",
            ) from exc

    raise ErrorDeDescifrado(
        f"El dato está cifrado con la clave {clave_id!r}, que no está configurada. "
        "Si se acaba de rotar la clave, la anterior debe seguir en "
        "CARNETS_ENCRYPTION_KEYS para poder leer lo ya guardado.",
    )


class CampoTextoCifrado(models.TextField):
    """Campo de texto que se guarda cifrado y se lee descifrado.

    En la base de datos es una columna TEXT con el texto cifrado; el código de
    la aplicación lo usa como si fuera un campo de texto normal.

    Dos consecuencias que conviene tener presentes:

    1. No se puede filtrar ni ordenar por él en SQL. El cifrado es no
       determinista (nonce distinto en cada escritura), así que el mismo nombre
       produce textos cifrados distintos y un WHERE nunca casaría. Para evitar
       que eso se traduzca en un "no hay resultados" silencioso —que se leería
       como "esa persona no existe"— cualquier búsqueda por este campo falla de
       forma explícita.
    2. `max_length` deja de aplicarse solo: TextField no valida longitud. Se
       añade el validador a mano para no perder la validación que había con
       CharField (sin ella, un Excel podría colar un nombre de megabytes).
    """

    # Lookups que sí tienen sentido sobre texto cifrado: los que no miran el
    # contenido. El resto se rechaza en vez de devolver cero resultados.
    LOOKUPS_PERMITIDOS = frozenset({"isnull"})

    @cached_property
    def validators(self):
        base = list(super().validators)
        if self.max_length is not None:
            base.append(MaxLengthValidator(self.max_length))
        return base

    def get_lookup(self, lookup_name):
        if lookup_name not in self.LOOKUPS_PERMITIDOS:
            raise FieldError(
                f"No se puede usar '{lookup_name}' sobre {self.name!r}: es un campo "
                "cifrado y su contenido no es consultable desde SQL. Filtra en "
                "Python tras leer, o añade un índice ciego si hace falta buscar "
                "por él de forma habitual.",
            )
        return super().get_lookup(lookup_name)

    def get_prep_value(self, value):
        if isinstance(value, TextoNoDescifrable):
            # Guardarlo escribiría el marcador encima del texto cifrado
            # original y destruiría el dato de forma irreversible.
            raise ErrorDeDescifrado(
                f"Se intenta guardar en {self.name!r} un valor que no se pudo "
                "descifrar al leerlo. Escribirlo destruiría el dato original. "
                "Vuelve a poner la clave que falta en la configuración antes de "
                "tocar este registro.",
            )
        value = super().get_prep_value(value)
        if value is None:
            return None
        return cifrar(str(value))

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        try:
            return descifrar(value)
        except ErrorDeDescifrado as exc:
            # No se propaga la excepción: la conversión ocurre mientras se leen
            # las filas, así que un solo registro ilegible abortaría la consulta
            # entera y dejaría inservible el listado completo del admin, sin
            # forma siquiera de averiguar cuál es el registro afectado. Se
            # devuelve un marcador —que no se puede volver a guardar— para que
            # las demás filas se sigan viendo y la rota quede señalada.
            logger.error(
                "No se pudo descifrar %s: %s", self.name, exc,
            )
            return TextoNoDescifrable(MARCA_NO_DESCIFRABLE)
