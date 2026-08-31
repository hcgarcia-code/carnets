from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, PasswordResetView
from django.core.cache import cache
from django.http import HttpResponse
from django_otp.admin import OTPAdminSite

from .auditoria import ACCIONES, registrar
from .ip import ip_real

INTENTOS_MAXIMOS = 5
VENTANA_BLOQUEO_SEGUNDOS = 5 * 60

# Más holgado que el del login porque aquí cada intento cuesta un correo, no una
# comprobación de contraseña: el daño no es adivinar la clave sino inundar el
# buzón de un sindicato con reposiciones que él no ha pedido.
PETICIONES_RECUPERACION_MAXIMAS = 5
VENTANA_RECUPERACION_SEGUNDOS = 15 * 60


def _clave_intentos(request, username: str) -> str:
    # La IP la resuelve gestion.ip.ip_real, que solo se cree X-Forwarded-For si
    # la petición viene de un proxy declarado: así el cliente no puede
    # falsificarla para esquivar el límite, pero detrás del proxy de producción
    # deja de ser siempre la misma. Se combina con el usuario objetivo para no
    # bloquear cuentas legítimas que comparten IP con un atacante que está
    # probando contra OTRA cuenta.
    ip = ip_real(request) or 'desconocida'
    usuario_normalizado = (username or '').strip().lower()[:150]
    return f"login_intentos:{ip}:{usuario_normalizado}"


MENSAJE_CUENTA_INACTIVA = (
    "Tu usuario y tu contraseña son correctos, pero la cuenta todavía no está "
    "activa: un administrador tiene que aprobarla. Recibirás un correo en cuanto "
    "lo haga. Si llevas más de un par de días esperando, escribe a "
    "soporte-carnets@cgt.org.es."
)


def _cuenta_pendiente_de_activar(request, username: str) -> bool:
    """¿El intento es de una cuenta real, sin activar, y con la clave correcta?

    `ModelBackend` rechaza a los usuarios con `is_active=False` ANTES de mirar
    la contraseña, así que el formulario nunca llega a `confirm_login_allowed` y
    cae en el error genérico: la pantalla decía "usuario o contraseña
    incorrectos" a quien los tenía correctos. Quien acaba de registrarse lo
    reintenta, y acaba bloqueándose solo por insistir en algo que no depende
    de él.

    Se exige que la contraseña sea CORRECTA, y esa es la parte importante. Con
    solo acertar el nombre de usuario, esta pantalla sería un comprobador
    público de qué sindicatos están dados de alta —y qué sindicatos usan el
    sistema es precisamente lo que se protege al escribir a cada uno por
    separado en vez de meterlos a todos en el mismo `To:`. Acertar la
    contraseña es la prueba de que la cuenta es suya.
    """
    if not username:
        return False
    usuario = User.objects.filter(username=username).first()
    if usuario is None or usuario.is_active:
        return False
    return usuario.check_password(request.POST.get('password', ''))


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
        # El intento cuenta pase lo que pase, también el de una cuenta sin
        # activar: el limitador no distingue casos a propósito, y complicarlo
        # es justo lo que abrió el agujero del login del admin.
        cache.set(clave, cache.get(clave, 0) + 1, VENTANA_BLOQUEO_SEGUNDOS)

        # Una marca propia y no `form.add_error`: el error genérico de Django
        # también vive en `non_field_errors`, así que la plantilla no podría
        # distinguir el suyo del nuestro y acabaría enseñando el de Django, que
        # habla de mayúsculas y manda al sitio equivocado.
        self.cuenta_inactiva = _cuenta_pendiente_de_activar(self.request, username)
        if self.cuenta_inactiva:
            registrar(ACCIONES.LOGIN_CUENTA_INACTIVA, peticion=self.request, usuario=username)
        else:
            # Solo el usuario intentado: la contraseña no se registra nunca, ni
            # siquiera fallida (suele ser la de otra cuenta, o la buena con una errata).
            registrar(ACCIONES.LOGIN_FALLIDO, peticion=self.request, usuario=username)

        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['cuenta_inactiva'] = getattr(self, 'cuenta_inactiva', False)
        contexto['mensaje_cuenta_inactiva'] = MENSAJE_CUENTA_INACTIVA
        return contexto

    def form_valid(self, form):
        username = form.cleaned_data.get('username', '')
        clave = _clave_intentos(self.request, username)
        cache.delete(clave)
        registrar(ACCIONES.LOGIN_CORRECTO, peticion=self.request, usuario=username)
        return super().form_valid(form)


class AdminConLimiteDeIntentos(OTPAdminSite):
    """El sitio del admin, con el mismo límite de intentos que el de sindicatos.

    django-otp cubre el segundo factor, que es la defensa principal: acertar la
    contraseña no basta para entrar. Pero la vista de acceso del admin es la de
    Django y aceptaba intentos sin cuenta y sin dejar rastro —los eventos
    `login.fallido` los emite LoginConLimiteDeIntentos, que solo cubre
    `/login/`—, de modo que la única cuenta que ve los datos personales en claro
    tenía un oráculo de contraseña ilimitado y silencioso.

    El contador se comparte con el login de sindicatos a propósito: es el mismo
    modelo `User`, así que llevar dos cuentas separadas le daría al atacante el
    doble de intentos sobre la misma credencial.

    Se envuelve `login()` y no `has_permission()`: el segundo factor tiene que
    seguir aplicándose exactamente igual, y aquí solo se añade el límite delante.
    """

    def login(self, request, extra_context=None):
        if request.method != 'POST':
            return super().login(request, extra_context)

        username = request.POST.get('username', '')
        clave = _clave_intentos(request, username)
        if cache.get(clave, 0) >= INTENTOS_MAXIMOS:
            registrar(
                ACCIONES.LOGIN_BLOQUEADO, peticion=request, usuario=username, vista='admin',
            )
            return HttpResponse(
                "Demasiados intentos fallidos. Inténtalo de nuevo en unos minutos.",
                status=429,
            )

        respuesta = super().login(request, extra_context)

        # El resultado se deduce del código de respuesta, NO de `request.user`.
        #
        # Mirar `request.user.is_authenticated` parecía natural y era un agujero:
        # quien envía el formulario puede traer ya sesión de OTRA cuenta —le
        # basta una cuenta de sindicato corriente—, y entonces sale cierto pase
        # lo que pase con las credenciales tecleadas. Con eso, el límite no
        # contaba nada y la auditoría no escribía nada: intentos ilimitados y
        # silenciosos contra la única cuenta que descifra datos personales.
        #
        # En un POST solo `form_valid` puede redirigir, porque es lo único que
        # llama a `auth_login()`. Así que 302 es un acierto y 200 (formulario
        # reenseñado) es un fallo, con sesión previa o sin ella.
        if respuesta.status_code in (301, 302):
            cache.delete(clave)
            registrar(
                ACCIONES.LOGIN_CORRECTO, peticion=request, usuario=username, vista='admin',
            )
        elif respuesta.status_code == 200:
            # Solo el formulario reenseñado cuenta como intento. Un 403 de CSRF
            # no llega a comprobar credenciales, y contarlo dejaría que una
            # petición forzada desde otro sitio gastara el cupo del administrador.
            cache.set(clave, cache.get(clave, 0) + 1, VENTANA_BLOQUEO_SEGUNDOS)
            registrar(
                ACCIONES.LOGIN_FALLIDO, peticion=request, usuario=username, vista='admin',
            )

        return respuesta


class RecuperarPasswordConLimite(PasswordResetView):
    """Reposición de contraseña por correo, acotada.

    Django ya resuelve bien las dos partes delicadas y no hay que tocarlas:
    responde igual exista o no la dirección (si no, este formulario sería un
    comprobador público de qué sindicatos están dados de alta), y solo
    considera cuentas con `is_active`, de modo que un alta pendiente de
    aprobación no puede activarse por esta vía.

    Lo que falta añadir es el límite: sin él, cualquiera puede pedir mil
    reposiciones para la dirección de un sindicato y dejarle el buzón
    inservible, que es justo cuando más falta le hace leerlo.

    El límite va por IP y no por dirección de correo a propósito: contarlo por
    dirección permitiría a un atacante bloquear a una víctima concreta sin más
    que agotar su cupo.
    """

    def _clave(self, request) -> str:
        # Este es el limitador al que más le duele que la IP sea la del proxy:
        # como cuenta SOLO por IP, con un valor constante el cupo pasaba a ser
        # de cinco peticiones cada cuarto de hora para todo el sitio. Con 51
        # sindicatos recién avisados de una dirección nueva, el sexto que
        # pidiera su contraseña se llevaba un 429 sin haber hecho nada.
        ip = ip_real(request) or "desconocida"
        return f"recuperacion_intentos:{ip}"

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST":
            clave = self._clave(request)
            if cache.get(clave, 0) >= PETICIONES_RECUPERACION_MAXIMAS:
                registrar(ACCIONES.REPOSICION_BLOQUEADA, peticion=request)
                return HttpResponse(
                    "Demasiadas solicitudes de recuperación desde esta conexión. "
                    "Inténtalo de nuevo más tarde.",
                    status=429,
                )
            cache.set(clave, cache.get(clave, 0) + 1, VENTANA_RECUPERACION_SEGUNDOS)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # No se registra la dirección: es dato de contacto de una persona y el
        # registro de auditoría está construido para no contener datos
        # personales. Basta con saber que se pidió, desde dónde y cuándo.
        registrar(ACCIONES.REPOSICION_SOLICITADA, peticion=self.request)
        return super().form_valid(form)
