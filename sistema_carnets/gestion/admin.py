from datetime import timedelta

import pandas as pd
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Max, Q
from django.http import HttpResponse
from django.utils import timezone
from simple_history.admin import SimpleHistoryAdmin

from .auditoria import ACCIONES, registrar
from .auth_views import AdminConLimiteDeIntentos
from .models import Afiliado, Notificacion, PerfilSindicato, RegistroSubida
from .resumen import DIAS_SIN_ACTIVIDAD, resumen_operativo
from .services import marcar_como_impresos_y_notificar


class SitioAdminCarnets(AdminConLimiteDeIntentos):
    """El sitio del admin: segundo factor, limite de intentos y resumen en la portada.

    El resumen va aqui dentro y no en una vista aparte a proposito. Una vista con
    `@staff_member_required` comprueba `is_active and is_staff` y nada mas: seria
    alcanzable con la contrasena sola, pegada a un admin que exige segundo
    factor. El indice pasa por `admin_view()` -> `has_permission()`, que en
    OTPAdminSite incluye `is_verified()`.

    No se audita la consulta de la portada: aqui no se descifra nada, solo hay
    recuentos. Registrar cada visita a `/admin/` llenaria de ruido el archivo que
    tiene que servir para encontrar quien miro datos personales.
    """

    index_template = 'gestion/admin_indice.html'

    def index(self, request, extra_context=None):
        # Se reparten aqui y no en la plantilla porque se pintan en dos sitios
        # distintos: las alertas en caja roja arriba, lo pendiente como lista de
        # enlaces. Separarlo en el HTML obligaria a recorrer la lista dos veces
        # con un `if` dentro de cada vuelta.
        avisos = resumen_operativo()
        return super().index(request, {
            **(extra_context or {}),
            'alertas': [a for a in avisos if a['nivel'] == 'alerta'],
            'pendientes': [a for a in avisos if a['nivel'] != 'alerta'],
        })

# El admin exige segundo factor. Es el unico sitio donde los datos personales
# se descifran y se ven en claro: el panel de la imprenta consulta con
# `.values()` sin los nombres, el registro de auditoria no los escribe y la
# base de datos los guarda cifrados. Todo eso se sostiene sobre la contrasena
# del administrador, asi que si se filtra, se entrega el archivo entero de
# afiliacion sindical (dato de categoria especial, RGPD Art. 9).
#
# La clase ademas limita los intentos de acceso: la vista de login del admin es
# la de Django y aceptaba intentos sin cuenta ni rastro (ver auth_views.py).
#
# Se reemplaza la clase del sitio ya existente en vez de crear uno nuevo para
# no tener que reescribir el register() de cada modelo ni la ruta de urls.py.
#
# Para darse de alta: `manage.py activar_2fa <usuario>`. Sin ejecutarlo antes,
# el admin queda inaccesible (el comando funciona desde la consola del
# servidor, asi que no es un bloqueo del que no se pueda salir).
admin.site.__class__ = SitioAdminCarnets


# --- ACCIÓN 1: Poner fecha a los carnets ---
# permissions=["change"]: sin esto Django ofrece la accion a cualquier cuenta
# de staff que llegue al listado, aunque solo tenga permiso de ver.
@admin.action(description="1. Asignar fecha de expedición (Día de hoy)", permissions=["change"])
def asignar_fecha_hoy(modeladmin, request, queryset):
    # Los identificadores se leen ANTES de actualizar: el queryset puede venir
    # de un filtro sobre fecha_expedicion, y en ese caso dejaría de casar con
    # las mismas filas justo después de escribirlas.
    identificadores = list(queryset.values_list('pk', flat=True))

    # Toma todos los afiliados que hayas seleccionado y les pone la fecha actual
    filas_actualizadas = queryset.update(fecha_expedicion=timezone.now().date())

    # `update()` no pasa por save(), así que no deja versión en el historial de
    # django-simple-history. Sin este registro, la acción modificaba campos de
    # registros de categoría especial sin aparecer en ninguno de los dos
    # rastros: era la única de las tres acciones del admin en esa situación.
    registrar(
        ACCIONES.AFILIADOS_FECHADOS,
        peticion=request,
        cantidad=filas_actualizadas,
        ids=identificadores,
    )

    modeladmin.message_user(
        request, f"Éxito: Se ha asignado la fecha a {filas_actualizadas} carnets.",
    )


# --- ACCIÓN 2: Generar Excel para la máquina ---
# La mas sensible de las tres: saca a un archivo descargable los datos
# personales descifrados de los afiliados seleccionados.
@admin.action(description="2. Descargar Excel para Máquina de Carnets", permissions=["change"])
def exportar_imprenta(modeladmin, request, queryset):
    # "Select all N" del listado selecciona TODO lo que cumpla el filtro
    # actual, esté ya impreso o no: si el admin no ha filtrado antes por
    # "Pendiente de imprimir", una selección de varias páginas arrastra
    # afiliados ya enviados. Reprocesarlos pisaría su fecha_envio_imprenta
    # original y generaría una notificación de reenvío falsa al sindicato.
    # La acción se defiende sola en vez de confiar en que se aplicó el filtro.
    seleccionados = queryset.count()
    queryset = queryset.filter(estado_impresion=Afiliado.ESTADO_PENDIENTE)
    ya_impresos = seleccionados - queryset.count()

    if not queryset.exists():
        modeladmin.message_user(
            request,
            "Los afiliados seleccionados ya estaban impresos: no se ha generado ningún Excel.",
            level=messages.WARNING,
        )
        return None

    datos = []
    identificadores = []
    # Recorremos los afiliados seleccionados y extraemos sus datos exactos
    for afiliado in queryset:
        identificadores.append(afiliado.pk)
        datos.append({
            'Confederacion': afiliado.confederacion_territorial,
            'Fed_Local': afiliado.federacion_local,
            'Fed_Sectorial': afiliado.federacion_sectorial,
            'Sindicato': afiliado.sindicato_codigo,
            'Num_Afiliado': afiliado.num_afiliado,
            'Nombre_Apellidos': afiliado.nombre_apellidos,
            'Fecha_Expedicion': afiliado.fecha_expedicion_mmyy,  # Columna movida aquí
            'Lengua': afiliado.lengua,
            # La columna de Estado ha sido eliminada
        })

    # Usamos Pandas para crear el archivo Excel en la memoria del servidor
    df = pd.DataFrame(datos)
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="carnets_para_imprimir.xlsx"'

    # Enviamos el archivo al navegador para que se descargue
    df.to_excel(response, index=False, engine='openpyxl')

    # Se marca como impreso y se notifica a cada sindicato solo DESPUÉS de que
    # el Excel se ha generado correctamente, para no notificar en falso si
    # algo falla antes de llegar aquí.
    marcar_como_impresos_y_notificar(queryset)

    # Es la operación más sensible de la aplicación: saca de golpe los datos
    # personales de muchos afiliados a un archivo descargable. Tiene que quedar
    # constancia de quién lo hizo y sobre cuántos registros.
    registrar(
        ACCIONES.AFILIADOS_EXPORTADOS,
        peticion=request,
        cantidad=len(identificadores),
        ids=identificadores,
    )

    if ya_impresos:
        modeladmin.message_user(
            request,
            f"Se han omitido {ya_impresos} afiliado(s) que ya estaban impresos. "
            f"Exportados {len(identificadores)}.",
            level=messages.WARNING,
        )

    return response


# --- CONFIGURACIÓN DEL PANEL VISUAL ---
class AfiliadoAdmin(SimpleHistoryAdmin):
    # Columnas que ves en la pantalla
    list_display = (
        'sindicato_codigo', 'num_afiliado', 'nombre_apellidos', 'estado',
        'fecha_expedicion_mmyy', 'estado_impresion',
    )
    # Filtros laterales
    list_filter = ('sindicato_codigo', 'estado', 'lengua', 'estado_impresion')
    # Buscador superior. Los campos van cifrados en la BD, así que la búsqueda
    # no puede hacerla SQL: se resuelve en get_search_results (ver abajo).
    search_fields = ('num_afiliado', 'nombre_apellidos')
    # Estos campos solo deben cambiar a través de la acción de exportación,
    # nunca editados a mano desde el formulario del admin.
    # fecha_baja va aquí por un motivo distinto: la rellena sola el modelo al
    # pasar a BAJA y es el reloj desde el que cuenta el plazo de conservación
    # (ver expurgar_afiliados). Editable a mano, un dedazo en el año adelanta
    # una anonimización que es irreversible.
    readonly_fields = ('estado_impresion', 'fecha_envio_imprenta', 'fecha_baja')
    # Conectamos las acciones que hemos creado arriba
    actions = [asignar_fecha_hoy, exportar_imprenta]

    # Ver estos datos ya es acceder a información de categoría especial, aunque
    # no se modifique nada: queda registrado. Se anota DESPUÉS de que la vista
    # de Django haya comprobado los permisos, porque es ella quien lanza
    # PermissionDenied. Anotarlo antes haría que un intento rechazado —que no
    # llega a ver ni un dato— quedase escrito igual que una consulta real, y al
    # investigar un incidente no habría forma de distinguirlos.
    def changelist_view(self, request, extra_context=None):
        try:
            respuesta = super().changelist_view(request, extra_context)
        except PermissionDenied:
            registrar(ACCIONES.ACCESO_DENEGADO, peticion=request, vista='afiliados.listado')
            raise
        registrar(ACCIONES.AFILIADOS_CONSULTADOS, peticion=request)
        return respuesta

    def change_view(self, request, object_id, form_url='', extra_context=None):
        try:
            respuesta = super().change_view(request, object_id, form_url, extra_context)
        except PermissionDenied:
            registrar(
                ACCIONES.ACCESO_DENEGADO, peticion=request,
                vista='afiliado.ficha', ids=[object_id],
            )
            raise
        registrar(ACCIONES.AFILIADO_ABIERTO, peticion=request, ids=[object_id])
        return respuesta

    def get_search_results(self, request, queryset, search_term):
        """Busca por nombre o número de afiliado descifrando en memoria.

        El buscador por defecto del admin genera un WHERE ... LIKE sobre la
        columna, y esas columnas guardan texto cifrado: nunca encontraría nada.
        Aquí se descifra fila a fila y se compara en Python.

        ponytail: es un recorrido O(n) sobre los afiliados en cada búsqueda.
        Con el volumen actual (~3.000 afiliados) son unas décimas de segundo y
        se prefiere eso a añadir estructuras extra. Si la tabla crece a decenas
        de miles, el siguiente paso es un índice ciego (HMAC determinista del
        valor normalizado) en una columna aparte, que permite buscar por
        igualdad exacta sin descifrar ni exponer el contenido.
        """
        if not search_term:
            return queryset, False

        termino = search_term.strip().casefold()
        coincidencias = [
            afiliado.pk
            for afiliado in queryset.only('id', 'num_afiliado', 'nombre_apellidos')
            if termino in (afiliado.nombre_apellidos or '').casefold()
            or termino in (afiliado.num_afiliado or '')
        ]
        return queryset.filter(pk__in=coincidencias), False


admin.site.register(Afiliado, AfiliadoAdmin)


class FiltroDeActividad(admin.SimpleListFilter):
    """Sindicatos que han dejado de cargar altas.

    Es la consulta que antes no se podía hacer: para saber quién lleva meses
    sin subir nada había que abrir los perfiles uno a uno. Un sindicato dormido
    no es un fallo técnico —nada falla— pero sí el aviso de que alguien dejó de
    usar el sistema y sus afiliados se están quedando sin carnet.
    """

    title = "actividad de cargas"
    parameter_name = "actividad"

    def lookups(self, request, model_admin):
        return (
            ("sin_cargas", "No ha subido nunca"),
            ("dormidos", f"Sin cargar en {DIAS_SIN_ACTIVIDAD} días"),
        )

    def queryset(self, request, queryset):
        if self.value() == "sin_cargas":
            return queryset.filter(usuario__subidas__isnull=True)
        if self.value() == "dormidos":
            # Se reutiliza `_ultima_carga`, que ya viene anotada de
            # PerfilSindicatoAdmin.get_queryset. Volver a anotar aquí un Max
            # sobre la misma relación añadiría un segundo JOIN sobre subidas y
            # duplicaría filas para el Count que va al lado. Este filtro solo
            # se usa en ese ModelAdmin, que es quien pone la anotación.
            limite = timezone.now() - timedelta(days=DIAS_SIN_ACTIVIDAD)
            return queryset.filter(
                Q(_ultima_carga__lt=limite) | Q(_ultima_carga__isnull=True),
            )
        return queryset


@admin.register(PerfilSindicato)
class PerfilSindicatoAdmin(admin.ModelAdmin):
    """La pantalla desde la que se decide a quién se aprueba y a quién se reclama.

    Estaba registrado a pelo, así que el listado solo enseñaba «Perfil de
    <usuario>»: para saber quién había pedido el alta, si había firmado el
    acuerdo o qué había cargado, había que abrir cada ficha. Los datos ya
    estaban en la base; lo que faltaba era enseñarlos.

    Aquí no se ve ningún dato de afiliado: los recuentos son agregados y el
    nombre del sindicato y la persona de contacto ya estaban en este formulario.
    """

    list_display = (
        'usuario', 'nombre_identificativo', 'persona_contacto',
        'cuenta_activa', 'acuerdo', 'num_cargas', 'ultima_carga',
    )
    list_filter = ('acuerdo_aceptado', 'usuario__is_active', FiltroDeActividad)
    # Solo campos sin cifrar: el buscador del admin genera un WHERE ... LIKE, y
    # sobre una columna cifrada nunca encontraría nada (ver CampoTextoCifrado).
    search_fields = ('usuario__username', 'nombre_identificativo', 'persona_contacto')
    # La firma del acuerdo es la constancia de un consentimiento: se sella sola
    # al aceptarlo (ver views.acuerdo_legal). Editable a mano deja de probar
    # nada, que es justo para lo que se guarda.
    readonly_fields = ('fecha_aceptacion', 'ip_aceptacion')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('usuario').annotate(
            _num_cargas=Count('usuario__subidas', distinct=True),
            _ultima_carga=Max('usuario__subidas__fecha'),
        )

    @admin.display(boolean=True, description="Cuenta aprobada", ordering='usuario__is_active')
    def cuenta_activa(self, perfil):
        # El alta autoservicio crea la cuenta inactiva y se aprueba a mano desde
        # el listado de usuarios: es el dato que más se consulta aquí.
        return perfil.usuario.is_active

    @admin.display(description="Acuerdo de protección de datos", ordering='acuerdo_aceptado')
    def acuerdo(self, perfil):
        if not perfil.acuerdo_aceptado:
            return "Sin firmar"
        if perfil.fecha_aceptacion:
            return f"Firmado el {timezone.localtime(perfil.fecha_aceptacion):%d/%m/%Y}"
        return "Firmado"

    @admin.display(description="Cargas", ordering='_num_cargas')
    def num_cargas(self, perfil):
        return perfil._num_cargas

    @admin.display(description="Última carga", ordering='_ultima_carga')
    def ultima_carga(self, perfil):
        if perfil._ultima_carga is None:
            return "Nunca"
        dias = (timezone.now() - perfil._ultima_carga).days
        fecha = timezone.localtime(perfil._ultima_carga)
        return f"{fecha:%d/%m/%Y} (hace {dias} día(s))"


@admin.register(RegistroSubida)
class RegistroSubidaAdmin(admin.ModelAdmin):
    list_display = ('sindicato', 'fecha', 'cantidad_afiliados', 'nombre_archivo')
    list_filter = ('sindicato',)
    readonly_fields = ('sindicato', 'fecha', 'cantidad_afiliados', 'nombre_archivo')
    # Navegación por año/mes/día, que es como se pregunta de verdad por esto
    # ("¿qué se subió en marzo?"). Django la construye sola desde el campo.
    date_hierarchy = 'fecha'

    def has_add_permission(self, request):
        # Solo se crean automáticamente al subir un Excel, nunca a mano.
        return False


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    """Qué se le ha dicho a cada sindicato y cuándo.

    Las genera el envío a imprenta. Se registran solo para poder consultarlas
    cuando un sindicato pregunta si se le avisó: escribir una a mano le diría
    que se imprimió algo que no se imprimió, así que no se pueden crear ni
    editar desde aquí.
    """

    list_display = ('usuario', 'fecha_creacion', 'leida', 'mensaje')
    list_filter = ('leida', 'fecha_creacion')
    search_fields = ('usuario__username',)
    readonly_fields = ('usuario', 'mensaje', 'leida', 'fecha_creacion')
    date_hierarchy = 'fecha_creacion'

    def has_add_permission(self, request):
        return False


# Aprobar salta el control manual de altas, que es lo unico que impide que
# una cuenta sin revisar empiece a subir datos de afiliacion.
@admin.action(description="Aprobar las cuentas de sindicato seleccionadas", permissions=["change"])
def aprobar_cuentas(modeladmin, request, queryset):
    # Solo activa las que de verdad estaban inactivas: evita que el mensaje de
    # éxito infle el recuento con cuentas que ya estaban aprobadas de antes.
    activadas = queryset.filter(is_active=False).update(is_active=True)
    modeladmin.message_user(request, f"{activadas} cuenta(s) activada(s).")


class RegistroSubidaInline(admin.TabularInline):
    """El historial de cargas del sindicato, en su propia ficha.

    Va sobre `User` y no sobre `PerfilSindicato` porque la clave ajena de
    RegistroSubida apunta a `User` (el perfil solo tiene un OneToOne, que no
    sirve para un inline).

    Solo lectura entera: un RegistroSubida es la constancia de qué entregó cada
    sindicato y cuándo. Escrito a mano dejaría de serlo.
    """

    model = RegistroSubida
    extra = 0
    can_delete = False
    fields = ('fecha', 'cantidad_afiliados', 'nombre_archivo')
    readonly_fields = fields
    # Sin esto, Django hace una consulta por cada carga para pintar el desplegable
    # de sindicato, aunque el campo no se muestre.
    ordering = ('-fecha',)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.unregister(User)


@admin.register(User)
class UsuarioAdmin(UserAdmin):
    # El alta autoservicio (ver forms.RegistroSindicatoForm) crea la cuenta
    # inactiva a propósito: aquí es donde se revisa y se aprueba. is_active y
    # el nombre que la propia cuenta declaró al registrarse son justo lo que
    # hace falta para decidir; el UserAdmin de Django por defecto no muestra
    # ninguno de los dos en el listado.
    list_display = (*UserAdmin.list_display, 'is_active', 'sindicato_declarado')
    # is_active ya viene en UserAdmin.list_filter; anadirlo lo dejaba dos veces
    # (Django no deduplica) y el panel lateral pintaba "Por activo" duplicado.
    list_filter = UserAdmin.list_filter
    actions = [aprobar_cuentas]

    def get_inlines(self, request, obj=None):
        # El alta de un usuario en el admin es un formulario en dos pasos: en el
        # primero todavía no hay fila a la que colgar el inline. Django lo
        # renderizaría contra un objeto sin guardar y revienta el formulario.
        if obj is None:
            return ()
        return (RegistroSubidaInline,)

    @admin.display(description="Sindicato/rama declarado al darse de alta")
    def sindicato_declarado(self, usuario):
        return getattr(getattr(usuario, 'perfil', None), 'nombre_identificativo', '') or '—'
