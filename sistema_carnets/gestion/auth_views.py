from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.http import HttpResponse

INTENTOS_MAXIMOS = 5
VENTANA_BLOQUEO_SEGUNDOS = 5 * 60


def _clave_intentos(request, username: str) -> str:
    # Se usa REMOTE_ADDR (la IP real de la conexión TCP) y no cabeceras como
    # X-Forwarded-For, que el cliente puede falsificar libremente para
    # esquivar el límite. Se combina con el usuario objetivo para no
    # bloquear cuentas legítimas que comparten IP con un atacante que está
    # probando contra OTRA cuenta.
    ip = request.META.get('REMOTE_ADDR', 'desconocida')
    usuario_normalizado = (username or '').strip().lower()[:150]
    return f"login_intentos:{ip}:{usuario_normalizado}"


class LoginConLimiteDeIntentos(LoginView):
    """LoginView con bloqueo temporal tras varios intentos fallidos.

    Sin este control, un atacante puede probar credenciales sin límite
    (fuerza bruta / credential stuffing). Tras INTENTOS_MAXIMOS fallos para
    el mismo par (IP, usuario), se devuelve 429 durante VENTANA_BLOQUEO_SEGUNDOS
    sin ni siquiera comprobar la contraseña.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            username = request.POST.get('username', '')
            clave = _clave_intentos(request, username)
            if cache.get(clave, 0) >= INTENTOS_MAXIMOS:
                return HttpResponse(
                    "Demasiados intentos fallidos. Inténtalo de nuevo en unos minutos.",
                    status=429,
                )
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        username = self.request.POST.get('username', '')
        clave = _clave_intentos(self.request, username)
        cache.set(clave, cache.get(clave, 0) + 1, VENTANA_BLOQUEO_SEGUNDOS)
        return super().form_invalid(form)

    def form_valid(self, form):
        clave = _clave_intentos(self.request, form.cleaned_data.get('username', ''))
        cache.delete(clave)
        return super().form_valid(form)
