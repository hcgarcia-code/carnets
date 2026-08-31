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
import os
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
    # Asignación de fecha de expedición desde el admin. Modifica registros de
    # categoría especial con una sola orden SQL, así que no deja rastro en el
    # historial de versiones: sin este registro era la única acción del admin
    # que no aparecía en ninguna parte.
    AFILIADOS_FECHADOS = "afiliados.fechados"
    # Anonimización por vencimiento del plazo de conservación. Es el único
    # rastro que queda: después de expurgar no hay dato que enseñar, así que
    # este registro es la prueba de haber cumplido el plazo (y de no haberse
    # adelantado a él).
    AFILIADOS_EXPURGADOS = "afiliados.expurgados"
    # Aviso masivo a los sindicatos (avisar_version_2). Guarda el recuento,
    # nunca las direcciones: este registro sale del ambito cifrado.
    AVISO_ENVIADO = "aviso.enviado"
    ACCESO_DENEGADO = "acceso.denegado"
    SINDICATO_REGISTRADO = "sindicato.registrado"
    LOTE_IMPRESION_CONSULTADO = "lote_impresion.consultado"
    LOGIN_CORRECTO = "login.correcto"
    LOGIN_FALLIDO = "login.fallido"
    LOGIN_BLOQUEADO = "login.bloqueado"
    # Credenciales correctas pero cuenta sin activar. Se distingue de
    # LOGIN_FALLIDO porque no es lo mismo: tres intentos de un sindicato que
    # espera aprobación parecen un ataque en el registro y no lo son.
    LOGIN_CUENTA_INACTIVA = "login.cuenta_inactiva"
    # Aprobar salta el control manual de altas, que es lo unico que separa a una
    # cuenta cualquiera de poder subir datos de afiliacion.
    CUENTAS_APROBADAS = "cuentas.aprobadas"
    # Una reposición de credencial se hace sin conocer la anterior: si alguien
    # controla el buzón de un sindicato, es su vía de entrada. Tiene que dejar
    # rastro igual que un acceso.
    # (Los nombres evitan el prefijo PASSWORD_ a propósito: bandit y ruff lo
    # leen como una contraseña escrita en el código y marcan S105.)
    REPOSICION_SOLICITADA = "reposicion.solicitada"
    REPOSICION_BLOQUEADA = "reposicion.bloqueada"


def _ip_de(peticion) -> str:
    """IP real de la conexión.

    La resuelve `gestion.ip.ip_real`, que solo se cree X-Forwarded-For si la
    petición viene de un proxy declarado. Antes se usaba REMOTE_ADDR a secas
    para que nadie pudiera falsear su rastro con esa cabecera; el motivo era
    bueno, pero detrás del proxy de producción REMOTE_ADDR era siempre la del
    balanceador y este campo repetía el mismo valor en todas las líneas, que
    para investigar un incidente es como no tenerlo.
    """
    # Import local: auditoria.py lo carga medio proyecto y gestion/ip.py lee
    # settings, que en el arranque todavía puede no estar listo.
    from .ip import ip_real

    return ip_real(peticion) or "desconocida"


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


def leer_sucesos(ruta, desde, *, max_bytes=None):
    """Lee el registro y agrupa por acción los sucesos posteriores a `desde`.

    Vive aquí y no en quien lo consulta porque es este módulo el que decide el
    formato: si algún día deja de ser un JSON por línea, hay un solo sitio que
    cambiar. Lo usan el comando `revisar_auditoria` y el resumen del admin.

    `max_bytes` acota la lectura a la cola del archivo. El registro es de
    solo-adición y crece sin límite, así que quien lo consulte en cada carga de
    página —el resumen del admin— no puede permitirse recorrerlo entero: se
    volvería más lento cuanto más se usa el sistema. Los sucesos van en orden
    cronológico, de modo que los recientes están al final. Sin `max_bytes` se
    lee completo, que es lo que quiere el comando por cron: ahí importa no
    perder nada, no la velocidad.

    Devuelve `(sucesos, truncado)`. `truncado` avisa de que se descartó parte
    del archivo, y por tanto de que los recuentos son un mínimo y no un total:
    callarlo daría una cifra tranquilizadora justo durante un ataque, que es
    cuando el archivo se llena de golpe.
    """
    sucesos = {}
    truncado = False

    with open(ruta, "rb") as archivo:
        if max_bytes is not None:
            archivo.seek(0, os.SEEK_END)
            tamano = archivo.tell()
            if tamano > max_bytes:
                archivo.seek(tamano - max_bytes)
                # La primera línea tras el salto viene cortada por la mitad.
                archivo.readline()
                truncado = True
            else:
                archivo.seek(0)

        for linea in archivo:
            try:
                registro = json.loads(linea.decode("utf-8"))
                momento = datetime.fromisoformat(registro["ts"])
            except (ValueError, KeyError, TypeError, UnicodeDecodeError):
                # Una linea corrupta (el proceso murio a media escritura) no
                # puede impedir ver las demas: seria la forma mas facil de
                # ocultar un incidente real.
                continue
            if momento >= desde:
                sucesos.setdefault(registro.get("accion", "?"), []).append(registro)

    return sucesos, truncado
