from django.http import HttpResponse

# Content-Security-Policy. Django no la trae, y anadir django-csp por una sola
# cabecera fija seria una dependencia por nada.
#
# Hoy no hay ningun punto por donde inyectar HTML (ninguna plantilla usa
# |safe, mark_safe ni autoescape off), asi que esto no tapa ningun agujero
# conocido: es la red de debajo si alguien anade manana una plantilla que si lo
# tenga. Lo que aporta es script-src 'self': un <script> inyectado no se
# ejecutaria por no venir de un archivo del propio sitio, que convierte un XSS
# explotable en uno inerte.
#
# style-src si lleva 'unsafe-inline' porque las plantillas tienen sus estilos
# en bloques <style> dentro del HTML. Es una concesion real, pero un estilo
# inyectado hace mucho menos dano que un script.
#
# Sin origenes externos en ninguna directiva: la aplicacion no usa CDN ni
# fuentes de terceros, y asi anadir uno obliga a pasar por aqui.
POLITICA_CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "form-action 'self'",
    # Equivalente moderno de X-Frame-Options: DENY, que ya se envia. Se ponen
    # los dos porque no todos los navegadores atienden a la misma.
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "object-src 'none'",
])


class CabeceraCSPMiddleware:
    """Anade la Content-Security-Policy a todas las respuestas."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        # setdefault y no asignacion directa: si una vista concreta necesita
        # alguna vez su propia politica, la suya manda.
        respuesta.setdefault("Content-Security-Policy", POLITICA_CSP)
        return respuesta

# Límite generoso por encima de TAMANO_MAXIMO_EXCEL_BYTES (5 MB, ver
# gestion/views.py) para dejar margen a la sobrecarga de multipart/form-data,
# pero muy por debajo de lo que se consideraría un intento de agotar memoria
# o disco del servidor.
TAMANO_MAXIMO_PETICION_BYTES = 10 * 1024 * 1024  # 10 MB


class LimiteTamanoPeticionMiddleware:
    """Rechaza pronto (413) peticiones cuyo Content-Length declarado supere
    el límite, antes de que el resto del stack de Django lea el cuerpo.

    Esto complementa (no sustituye) la validación de tamaño de archivo que
    ya hace la vista de carga de Excel: aquí se corta la conexión antes de
    bufferizar nada en memoria o disco.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        content_length = request.META.get('CONTENT_LENGTH')
        if content_length:
            try:
                tamano = int(content_length)
            except (TypeError, ValueError):
                tamano = None
            if tamano is not None and tamano > TAMANO_MAXIMO_PETICION_BYTES:
                return HttpResponse("Petición demasiado grande.", status=413)
        return self.get_response(request)
