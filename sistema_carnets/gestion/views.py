import logging

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.utils import timezone

from .models import Afiliado, PerfilSindicato

logger = logging.getLogger(__name__)

EXCEL_EXTENSIONS_PERMITIDAS = ('.xlsx',)
TAMANO_MAXIMO_EXCEL_BYTES = 5 * 1024 * 1024  # 5 MB
COLUMNAS_REQUERIDAS = [
    'Confederacion', 'Fed_Local', 'Fed_Sectorial', 'Sindicato',
    'Num_Afiliado', 'Nombre_Apellidos', 'Lengua', 'Estado',
]


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
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        perfil.ip_aceptacion = ip
        perfil.save()

        messages.success(
            request, "Acuerdo firmado correctamente. Ya puedes subir los datos de afiliación.",
        )
        return redirect('subir_excel')

    return render(request, 'gestion/acuerdo_legal.html')


def _formatear_error_validacion(error: ValidationError) -> str:
    if hasattr(error, 'message_dict'):
        return '; '.join(
            f"{campo}: {', '.join(msgs)}" for campo, msgs in error.message_dict.items()
        )
    return '; '.join(error.messages)


def archivo_excel_valido(nombre_archivo: str, tamano_bytes: int) -> tuple[bool, str]:
    """Valida la extensión y el tamaño de un archivo subido antes de procesarlo.

    Devuelve (es_valido, mensaje_de_error). mensaje_de_error es "" si es válido.
    """
    nombre = (nombre_archivo or '').lower()
    if not nombre.endswith(EXCEL_EXTENSIONS_PERMITIDAS):
        return False, "Formato de archivo no permitido. Sube un archivo .xlsx."
    if tamano_bytes > TAMANO_MAXIMO_EXCEL_BYTES:
        return False, "El archivo supera el tamaño máximo permitido (5 MB)."
    return True, ""


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

        # Validación estricta del archivo antes de procesarlo: extensión y tamaño.
        es_valido, mensaje_error = archivo_excel_valido(excel_file.name, excel_file.size)
        if not es_valido:
            messages.error(request, mensaje_error)
            return render(request, 'gestion/subir_excel.html')

        try:
            df = pd.read_excel(excel_file)
        except Exception:
            logger.exception("Error leyendo el archivo Excel subido por %s", request.user)
            messages.error(
                request,
                "No se pudo leer el archivo. Verifica que sea un Excel válido "
                "con la plantilla oficial.",
            )
            return render(request, 'gestion/subir_excel.html')

        columnas_faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
        if columnas_faltantes:
            messages.error(
                request,
                f"Faltan columnas obligatorias en el archivo: {', '.join(columnas_faltantes)}.",
            )
            return render(request, 'gestion/subir_excel.html')

        afiliados_creados = 0
        errores = []

        for index, fila in df.iterrows():
            numero_fila = index + 2  # +1 por índice base 0, +1 por la fila de cabecera
            try:
                afiliado = Afiliado(
                    sindicato_usuario=request.user,
                    confederacion_territorial=str(fila['Confederacion']).split('-')[0].strip(),
                    federacion_local=str(fila['Fed_Local']).split('-')[0].strip(),
                    federacion_sectorial=str(fila['Fed_Sectorial']).split('-')[0].strip(),
                    sindicato_codigo=str(fila['Sindicato']).split('-')[0].strip(),
                    num_afiliado=str(fila['Num_Afiliado']).split('.')[0].zfill(6),
                    nombre_apellidos=str(fila['Nombre_Apellidos']).strip(),
                    lengua=str(fila['Lengua']).strip(),
                    estado=str(fila['Estado']).strip(),
                )
                afiliado.full_clean()
                afiliado.save()
                afiliados_creados += 1
            except ValidationError as e:
                errores.append(f"Fila {numero_fila}: {_formatear_error_validacion(e)}")
            except (KeyError, ValueError, TypeError):
                errores.append(f"Fila {numero_fila}: datos incompletos o con formato incorrecto.")

        if afiliados_creados:
            messages.success(
                request,
                f"¡Éxito! Se han procesado y guardado {afiliados_creados} afiliados correctamente.",
            )

        if errores:
            resumen = "; ".join(errores[:10])
            extra = f" (y {len(errores) - 10} más)" if len(errores) > 10 else ""
            messages.error(
                request,
                f"{len(errores)} fila(s) no se pudieron guardar por errores de "
                f"validación: {resumen}{extra}",
            )

    return render(request, 'gestion/subir_excel.html')


# 3. NOTIFICACIONES DEL SINDICATO
@login_required
def listar_notificaciones(request):
    # request.user.notificaciones usa el related_name del FK: cada sindicato
    # solo puede ver, por construcción, sus propias notificaciones. No se
    # acepta ningún identificador desde la petición (GET/POST) para evitar
    # que un usuario pueda pedir las notificaciones de otro (IDOR).
    if request.method == 'POST':
        request.user.notificaciones.filter(leida=False).update(leida=True)
        return redirect('notificaciones')

    notificaciones = request.user.notificaciones.all()
    return render(request, 'gestion/notificaciones.html', {'notificaciones': notificaciones})
