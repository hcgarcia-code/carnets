"""Desde dónde llega una petición. Una sola respuesta para todo el proyecto.

Había dos formas de averiguarlo y ninguna acertaba detrás de un proxy inverso:

- `REMOTE_ADDR` a secas, en los limitadores de intentos y en la auditoría. El
  motivo escrito era bueno —`X-Forwarded-For` la pone el cliente y es
  falsificable— pero deja de valer cuando delante hay un proxy que REESCRIBE la
  cabecera. En producción `REMOTE_ADDR` era siempre la del balanceador, así que
  el limitador de reposición de contraseña, que se clava solo en la IP, pasó a
  ser de cinco peticiones cada cuarto de hora para TODO el sitio, y el campo
  `ip` de la auditoría repetía el mismo valor en cada línea: inservible para
  investigar un incidente, que es justo para lo que se guarda.

- `X-Forwarded-For` tomando la PRIMERA entrada, al firmar el acuerdo legal. Esa
  es precisamente la que puede escribir el cliente, de modo que la constancia
  de la firma guardaba un valor elegido por quien firmaba.

La regla de aquí resuelve las dos:

1. La cabecera solo se cree si la petición viene de un proxy declarado en
   `settings.PROXIES_DE_CONFIANZA`. Sin esa lista —el valor por defecto, y lo
   normal en local— se ignora por completo y se usa `REMOTE_ADDR`, que es el
   comportamiento seguro de antes.
2. Dentro de la cabecera se recorre de DERECHA A IZQUIERDA. La última entrada
   la añade el proxy en el que confiamos; las de la izquierda las puede haber
   escrito cualquiera. Leer por la izquierda es lo que hace falsificable el
   dato.

En PythonAnywhere: `PROXIES_DE_CONFIANZA=10.0.0.0/8` en el .env.
"""

import ipaddress

from django.conf import settings

# Tope de entradas que se miran en la cabecera. La escribe quien hace la
# petición, así que sin límite basta con mandar una lista larguísima para que
# cada acceso obligue a analizarla entera. Se recorre por la derecha, que es
# donde está la que nos interesa, así que el tope no descarta nada útil.
MAX_ENTRADAS_CABECERA = 32


def _redes_de_confianza():
    """Convierte PROXIES_DE_CONFIANZA en redes. Ignora lo que no sepa leer.

    Un dedazo en el .env no puede dejar el sitio sin servir: se descarta esa
    entrada y se sigue con las demás.
    """
    redes = []
    for entrada in getattr(settings, "PROXIES_DE_CONFIANZA", []) or []:
        try:
            redes.append(ipaddress.ip_network(str(entrada).strip(), strict=False))
        except ValueError:
            continue
    return redes


def _es_de_confianza(direccion, redes):
    try:
        ip = ipaddress.ip_address(direccion)
    except ValueError:
        return False
    return any(ip in red for red in redes)


def _es_una_ip(direccion):
    try:
        ipaddress.ip_address(direccion)
    except ValueError:
        return False
    return True


def ip_real(peticion):
    """IP del cliente, o None si no se puede determinar.

    Devuelve None y no un texto de relleno para que cada sitio decida: la
    auditoría escribe "desconocida", y `ip_aceptacion` —que es un campo de tipo
    IP— guarda un nulo en vez de reventar al validar.
    """
    if peticion is None:
        return None

    remota = (peticion.META.get("REMOTE_ADDR") or "").strip()
    redes = _redes_de_confianza()

    # La petición no viene de un proxy nuestro: la cabecera no vale nada.
    if not redes or not _es_de_confianza(remota, redes):
        return remota or None

    cabecera = peticion.META.get("HTTP_X_FORWARDED_FOR") or ""
    candidatas = [trozo.strip() for trozo in cabecera.split(",") if trozo.strip()]

    # De derecha a izquierda: la última la puso el proxy en el que confiamos.
    for direccion in reversed(candidatas[-MAX_ENTRADAS_CABECERA:]):
        if _es_una_ip(direccion) and not _es_de_confianza(direccion, redes):
            return direccion

    return remota or None
