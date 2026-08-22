import pandas as pd
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils import timezone
from django_otp.admin import OTPAdminSite
from simple_history.admin import SimpleHistoryAdmin

from .auditoria import ACCIONES, registrar
from .models import Afiliado, PerfilSindicato, RegistroSubida
from .services import marcar_como_impresos_y_notificar

# El admin exige segundo factor. Es el unico sitio donde los datos personales
# se descifran y se ven en claro: el panel de la imprenta consulta con
# `.values()` sin los nombres, el registro de auditoria no los escribe y la
# base de datos los guarda cifrados. Todo eso se sostiene sobre la contrasena
# del administrador, asi que si se filtra, se entrega el archivo entero de
# afiliacion sindical (dato de categoria especial, RGPD Art. 9).
#
# Se reemplaza la clase del sitio ya existente en vez de crear uno nuevo para
# no tener que reescribir el register() de cada modelo ni la ruta de urls.py.
#
# Para darse de alta: `manage.py activar_2fa <usuario>`. Sin ejecutarlo antes,
# el admin queda inaccesible (el comando funciona desde la consola del
# servidor, asi que no es un bloqueo del que no se pueda salir).
admin.site.__class__ = OTPAdminSite


# --- ACCIÓN 1: Poner fecha a los carnets ---
@admin.action(description="1. Asignar fecha de expedición (Día de hoy)")
def asignar_fecha_hoy(modeladmin, request, queryset):
    # Toma todos los afiliados que hayas seleccionado y les pone la fecha actual
    filas_actualizadas = queryset.update(fecha_expedicion=timezone.now().date())
    modeladmin.message_user(
        request, f"Éxito: Se ha asignado la fecha a {filas_actualizadas} carnets.",
    )


# --- ACCIÓN 2: Generar Excel para la máquina ---
@admin.action(description="2. Descargar Excel para Máquina de Carnets")
def exportar_imprenta(modeladmin, request, queryset):
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
    readonly_fields = ('estado_impresion', 'fecha_envio_imprenta')
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
admin.site.register(PerfilSindicato)


@admin.register(RegistroSubida)
class RegistroSubidaAdmin(admin.ModelAdmin):
    list_display = ('sindicato', 'fecha', 'cantidad_afiliados', 'nombre_archivo')
    list_filter = ('sindicato',)
    readonly_fields = ('sindicato', 'fecha', 'cantidad_afiliados', 'nombre_archivo')

    def has_add_permission(self, request):
        # Solo se crean automáticamente al subir un Excel, nunca a mano.
        return False


@admin.action(description="Aprobar las cuentas de sindicato seleccionadas")
def aprobar_cuentas(modeladmin, request, queryset):
    # Solo activa las que de verdad estaban inactivas: evita que el mensaje de
    # éxito infle el recuento con cuentas que ya estaban aprobadas de antes.
    activadas = queryset.filter(is_active=False).update(is_active=True)
    modeladmin.message_user(request, f"{activadas} cuenta(s) activada(s).")


admin.site.unregister(User)


@admin.register(User)
class UsuarioAdmin(UserAdmin):
    # El alta autoservicio (ver forms.RegistroSindicatoForm) crea la cuenta
    # inactiva a propósito: aquí es donde se revisa y se aprueba. is_active y
    # el nombre que la propia cuenta declaró al registrarse son justo lo que
    # hace falta para decidir; el UserAdmin de Django por defecto no muestra
    # ninguno de los dos en el listado.
    list_display = (*UserAdmin.list_display, 'is_active', 'sindicato_declarado')
    list_filter = (*UserAdmin.list_filter, 'is_active')
    actions = [aprobar_cuentas]

    @admin.display(description="Sindicato/rama declarado al darse de alta")
    def sindicato_declarado(self, usuario):
        return getattr(getattr(usuario, 'perfil', None), 'nombre_identificativo', '') or '—'
