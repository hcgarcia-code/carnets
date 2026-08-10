from django.http import HttpResponse

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
