import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Afiliado, PerfilSindicato

# 1. LA PANTALLA DEL ACUERDO LEGAL
@login_required
def acuerdo_legal(request):
    # Buscamos el perfil del usuario (o lo creamos automáticamente si es nuevo)
    perfil, created = PerfilSindicato.objects.get_or_create(usuario=request.user)
    
    # Si ya lo ha aceptado previamente, lo enviamos directo a subir datos
    if perfil.acuerdo_aceptado:
        return redirect('subir_excel')

    # Si hace clic en el botón de "Aceptar" (POST)
    if request.method == 'POST':
        perfil.acuerdo_aceptado = True
        perfil.fecha_aceptacion = timezone.now()
        
        # Capturamos la dirección IP por motivos legales
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        perfil.ip_aceptacion = ip
        perfil.save()
        
        messages.success(request, "Acuerdo firmado correctamente. Ya puedes subir los datos de afiliación.")
        return redirect('subir_excel')
        
    return render(request, 'gestion/acuerdo_legal.html')

# 2. LA PÁGINA DE SUBIDA (AHORA CON BLOQUEADOR)
@login_required
def cargar_datos_sindicato(request):
    # EL BLOQUEADOR LEGAL: Si no ha firmado, lo expulsamos a la pantalla del acuerdo
    perfil, created = PerfilSindicato.objects.get_or_create(usuario=request.user)
    if not perfil.acuerdo_aceptado:
        return redirect('acuerdo_legal')

    # Si ya ha firmado, le dejamos procesar el Excel
    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        excel_file = request.FILES['archivo_excel']
        try:
            df = pd.read_excel(excel_file)
            afiliados_creados = 0
            
            for index, fila in df.iterrows():
                cod_confed = str(fila['Confederacion']).split('-')[0].strip()
                cod_fed_local = str(fila['Fed_Local']).split('-')[0].strip()
                cod_fed_sec = str(fila['Fed_Sectorial']).split('-')[0].strip()
                cod_sindicato = str(fila['Sindicato']).split('-')[0].strip()
                num_afiliado_limpio = str(fila['Num_Afiliado']).zfill(6)
                
                Afiliado.objects.create(
                    sindicato_usuario=request.user,
                    confederacion_territorial=cod_confed,
                    federacion_local=cod_fed_local,
                    federacion_sectorial=cod_fed_sec,
                    sindicato_codigo=cod_sindicato,
                    num_afiliado=num_afiliado_limpio,
                    nombre_apellidos=str(fila['Nombre_Apellidos']),
                    lengua=str(fila['Lengua']).strip(),
                    estado=str(fila['Estado']).strip()
                )
                afiliados_creados += 1
                
            messages.success(request, f"¡Éxito! Se han procesado y guardado {afiliados_creados} afiliados correctamente.")
        except Exception as e:
            messages.error(request, f"Hubo un error procesando el archivo. Detalle técnico: {str(e)}")
            
    return render(request, 'gestion/subir_excel.html')