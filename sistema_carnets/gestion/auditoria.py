"""Registro de auditoría de accesos a datos personales (RGPD Art. 30).

django-simple-history deja constancia de los CAMBIOS en los datos, pero no de
las LECTURAS. Para datos de categoría especial —y la afiliación sindical lo
es— hay que poder demostrar también quién consultó o exportó qué, y cuándo:
sin esto, alguien con acceso al admin puede llevarse los expedientes de todos
los afiliados sin dejar el menor rastro.

Regla que gobierna este módulo: **aquí no se escriben datos personales**.
Se registra quién, cuándo, desde dónde, qué operación y sobre cuántos
registros; nunca el nombre ni el número de afiliado. Un registro de auditoría
con los datos dentro sería una segunda copia sin cifrar de lo que se acaba de
cifrar, y ampliaría la superficie expuesta en vez de reducirla. Hay un test
que lo comprueba.

Inmutabilidad
-------------
Un archivo local lo puede editar quien tenga acceso al servidor, así que por sí
solo no vale como prueba. Estos registros están pensados para enviarse a un
destino externo de solo-adición: el módulo se limita a emitirlos con estructura
de JSON por el logger 'auditoria', y de dónde acaban depende de la
configuración de LOGGING. Ver deploy/auditoria_centralizada.md.
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("auditoria")

# Número máximo de identificadores que se listan en un registro. Por encima de
# esto se guarda solo el recuento: una exportación de miles de afiliados haría
# ilegible el log sin aportar nada que el recuento no diga ya.
MAX_IDS_LISTADOS = 100

# Longitud máxima de cualquier texto que acabe en un registro. Buena parte de
# esos textos los elige quien hace la petición (el usuario tecleado en el
# login, por ejemplo), y sin tope una sola petición puede escribir megabytes:
# se llena el disco del log —que es justo lo que hay que poder conservar como
# prueba— y a partir de ahí deja de registrarse nada. El limitador de intentos
# de login recorta a 150 por este mismo motivo.
MAX_LONGITUD_TEXTO = 200
MARCA_RECORTE = "…[recortado]"


def _acotar(valor):
    """Recorta un texto demasiado largo para que no desborde el registro."""
    if not isinstance(valor, str) or len(valor) <= MAX_LONGITUD_TEXTO:
        return valor
    return valor[:MAX_LONGITUD_TEXTO] + MARCA_RECORTE


class ACCIONES:
    """Nombres de las operaciones auditadas.

    Son constantes y no texto suelto para que buscar todos los accesos de un
    tipo en el sistema centralizado sea una consulta exacta.
    """

    AFILIADOS_CONSULTADOS = "afiliados.consultados"
    AFILIADO_ABIERTO = "afiliado.abierto"
    AFILIADOS_EXPORTADOS = "afiliados.exportados"
    AFILIADOS_CARGADOS = "afiliados.cargados"
    # Anonimización por vencimiento del plazo de conservación. Es el único
    # rastro que queda: después de expurgar no hay dato que enseñar, así que
    # este registro es la prueba de haber cumplido el plazo (y de no haberse
    # adelantado a él).
    AFILIADOS_EXPURGADOS = "afiliados.expurgados"
    ACCESO_DENEGADO = "acceso.denegado"
    SINDICATO_REGISTRADO = "sindicato.registrado"
    LOTE_IMPRESION_CONSULTADO = "lote_impresion.consultado"
    LOGIN_CORRECTO = "login.correcto"
    LOGIN_FALLIDO = "login.fallido"
    LOGIN_BLOQUEADO = "login.bloqueado"
    # Una reposición de credencial se hace sin conocer la anterior: si alguien
    # controla el buzón de un sindicato, es su vía de entrada. Tiene que dejar
    # rastro igual que un acceso.
    # (Los nombres evitan el prefijo PASSWORD_ a propósito: bandit y ruff lo
    # leen como una contraseña escrita en el código y marcan S105.)
    REPOSICION_SOLICITADA = "reposicion.solicitada"
    REPOSICION_BLOQUEADA = "reposicion.bloqueada"


def _ip_de(peticion) -> str:
    """IP real de la conexión.

    Se usa REMOTE_ADDR y no X-Forwarded-For por el mismo motivo que en el
    limitador de intentos de login: la cabecera la pone el cliente y es
    falsificable, así que cualquiera podría falsear su propio rastro.
    """
    if peticion is None:
        return "desconocida"
    return peticion.META.get("REMOTE_ADDR", "desconocida")


def _usuario_de(peticion, usuario) -> str:
    if usuario is not None:
        return str(usuario)
    if peticion is None:
        return "desconocido"
    actual = getattr(peticion, "user", None)
    if actual is None or not getattr(actual, "is_authenticated", False):
        return "anonimo"
    return actual.get_username()


def registrar(accion, *, peticion=None, usuario=None, cantidad=None, ids=None, **detalles):
    """Emite un registro de auditoría.

    No pasar nunca nombres, números de afiliado ni contraseñas en `detalles`:
    este registro sale del ámbito cifrado.
    """
    registro = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "accion": accion,
        "usuario": _acotar(_usuario_de(peticion, usuario)),
        "ip": _ip_de(peticion),
    }
    if cantidad is not None:
        registro["cantidad"] = cantidad
    if ids:
        # Siempre como texto: así el mismo afiliado se busca igual en el
        # sistema centralizado venga la acción de donde venga (unas traen el
        # identificador de la URL, que es una cadena, y otras la clave primaria,
        # que es un entero).
        listados = [str(i) for i in ids]
        if len(listados) <= MAX_IDS_LISTADOS:
            registro["ids"] = listados
        else:
            registro["ids_omitidos"] = len(listados)
    registro.update({clave: _acotar(valor) for clave, valor in detalles.items()})

    logger.info(json.dumps(registro, ensure_ascii=False, sort_keys=True))
