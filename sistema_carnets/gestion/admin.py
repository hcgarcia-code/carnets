import pandas as pd
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from .models import Afiliado, PerfilSindicato

# --- ACCIÓN 1: Poner fecha a los carnets ---
@admin.action(description="1. Asignar fecha de expedición (Día de hoy)")
def asignar_fecha_hoy(modeladmin, request, queryset):
    # Toma todos los afiliados que hayas seleccionado y les pone la fecha actual
    filas_actualizadas = queryset.update(fecha_expedicion=timezone.now().date())
    modeladmin.message_user(request, f"Éxito: Se ha asignado la fecha a {filas_actualizadas} carnets.")

# --- ACCIÓN 2: Generar Excel para la máquina ---
@admin.action(description="2. Descargar Excel para Máquina de Carnets")
def exportar_imprenta(modeladmin, request, queryset):
    datos = []
    # Recorremos los afiliados seleccionados y extraemos sus datos exactos
    for afiliado in queryset:
        datos.append({
            'Confederacion': afiliado.confederacion_territorial,
            'Fed_Local': afiliado.federacion_local,
            'Fed_Sectorial': afiliado.federacion_sectorial,
            'Sindicato': afiliado.sindicato_codigo,
            'Num_Afiliado': afiliado.num_afiliado,
            'Nombre_Apellidos': afiliado.nombre_apellidos,
            'Fecha_Expedicion': afiliado.fecha_expedicion_mmyy,  # Columna movida aquí
            'Lengua': afiliado.lengua
            # La columna de Estado ha sido eliminada
        })
    
    # Usamos Pandas para crear el archivo Excel en la memoria del servidor
    df = pd.DataFrame(datos)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="carnets_para_imprimir.xlsx"'
    
    # Enviamos el archivo al navegador para que se descargue
    df.to_excel(response, index=False, engine='openpyxl')
    return response
    
    # Usamos Pandas para crear el archivo Excel en la memoria del servidor
    df = pd.DataFrame(datos)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="carnets_para_imprimir.xlsx"'
    
    # Enviamos el archivo al navegador para que se descargue
    df.to_excel(response, index=False, engine='openpyxl')
    return response

# --- CONFIGURACIÓN DEL PANEL VISUAL ---
class AfiliadoAdmin(admin.ModelAdmin):
    # Columnas que ves en la pantalla
    list_display = ('sindicato_codigo', 'num_afiliado', 'nombre_apellidos', 'estado', 'fecha_expedicion_mmyy')
    # Filtros laterales
    list_filter = ('sindicato_codigo', 'estado', 'lengua')
    # Buscador superior
    search_fields = ('num_afiliado', 'nombre_apellidos')
    # Conectamos las acciones que hemos creado arriba
    actions = [asignar_fecha_hoy, exportar_imprenta]

admin.site.register(Afiliado, AfiliadoAdmin)
admin.site.register(PerfilSindicato)