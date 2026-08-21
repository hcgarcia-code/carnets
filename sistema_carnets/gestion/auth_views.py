from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.http import HttpResponse

from .auditoria import ACCIONES, registrar

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
                # Un bloqueo es la señal de un ataque en curso: es lo primero
                # que se mira al investigar un incidente.
                registrar(ACCIONES.LOGIN_BLOQUEADO, peticion=request, usuario=username)
                return HttpResponse(
                    "Demasiados intentos fallidos. Inténtalo de nuevo en unos minutos.",
                    status=429,
                )
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        username = self.request.POST.get('username', '')
        clave = _clave_intentos(self.request, username)
        cache.set(clave, cache.get(clave, 0) + 1, VENTANA_BLOQUEO_SEGUNDOS)
        # Solo el usuario intentado: la contraseña no se registra nunca, ni
        # siquiera fallida (suele ser la de otra cuenta, o la buena con una errata).
        registrar(ACCIONES.LOGIN_FALLIDO, peticion=self.request, usuario=username)
        return super().form_invalid(form)

    def form_valid(self, form):
        username = form.cleaned_data.get('username', '')
        clave = _clave_intentos(self.request, username)
        cache.delete(clave)
        registrar(ACCIONES.LOGIN_CORRECTO, peticion=self.request, usuario=username)
        return super().form_valid(form)
