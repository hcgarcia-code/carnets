import logging

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, transaction
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from simple_history.utils import bulk_create_with_history

from .auditoria import ACCIONES, registrar
from .forms import RegistroSindicatoForm
from .models import Afiliado, PerfilSindicato, RegistroSubida

logger = logging.getLogger(__name__)

GRUPO_IMPRENTA = "Imprenta"

INTENTOS_REGISTRO_MAXIMOS = 5
VENTANA_REGISTRO_SEGUNDOS = 60 * 60

EXCEL_EXTENSIONS_PERMITIDAS = ('.xlsx',)
TAMANO_MAXIMO_EXCEL_BYTES = 5 * 1024 * 1024  # 5 MB
# Un .xlsx de pocos MB puede contener cientos de miles de filas (se comprime muy
# bien): el límite de tamaño por sí solo no acota el trabajo que genera la
# subida. Este tope evita que una sola petición agote memoria/CPU del servidor.
MAX_FILAS_EXCEL = 10_000
COLUMNAS_REQUERIDAS = [
    'Confederacion', 'Fed_Local', 'Fed_Sectorial', 'Sindicato',
    'Num_Afiliado', 'Nombre_Apellidos', 'Lengua', 'Estado',
]

# Traduce el nombre interno del campo del modelo al nombre de la columna tal
# como aparece en la cabecera del Excel, para que el aviso de error sea
# accionable por el sindicato sin conocer el modelo de datos.
CAMPO_A_COLUMNA_EXCEL = {
    'confederacion_territorial': 'Confederacion',
    'federacion_local': 'Fed_Local',
    'federacion_sectorial': 'Fed_Sectorial',
    'sindicato_codigo': 'Sindicato',
    'num_afiliado': 'Num_Afiliado',
    'nombre_apellidos': 'Nombre_Apellidos',
    'lengua': 'Lengua',
    'estado': 'Estado',
}


# 0. ALTA AUTOSERVICIO DE SINDICATOS
def registro_sindicato(request):
    # Pública y sin login: es justo la puerta de entrada para quien todavía no
    # tiene cuenta. Por eso limitamos intentos por IP —sin login no hay usuario
    # al que asociar el límite— y por eso el formulario crea la cuenta INACTIVA
    # (ver RegistroSindicatoForm.save): que cualquiera pueda rellenar este
    # formulario no debe significar que cualquiera pueda ya subir datos.
    ip = request.META.get('REMOTE_ADDR', 'desconocida')
    clave_limite = f"registro_intentos:{ip}"

    if cache.get(clave_limite, 0) >= INTENTOS_REGISTRO_MAXIMOS:
        return HttpResponse(
            "Demasiadas solicitudes de alta desde esta conexión. Inténtalo más tarde.",
            status=429,
        )

    if request.method == 'POST':
        cache.set(clave_limite, cache.get(clave_limite, 0) + 1, VENTANA_REGISTRO_SEGUNDOS)
        form = RegistroSindicatoForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            registrar(ACCIONES.SINDICATO_REGISTRADO, peticion=request, usuario=usuario.username)
            messages.success(
                request,
                "Solicitud recibida. Un administrador debe activar tu cuenta antes "
                "de que puedas iniciar sesión.",
            )
            return redirect('login')
    else:
        form = RegistroSindicatoForm()

    return render(request, 'gestion/registro.html', {'form': form})


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
    """Describe un error de validación usando los nombres de columna del Excel.

    Los errores de Django llegan con el nombre interno del campo del modelo
    (p. ej. 'confederacion_territorial'); se traducen al nombre de la columna
    del archivo ('Confederacion') para que el sindicato sepa exactamente dónde
    mirar sin conocer el modelo de datos.
    """
    if hasattr(error, 'message_dict'):
        return '; '.join(
            f"columna {CAMPO_A_COLUMNA_EXCEL.get(campo, campo)}: {', '.join(msgs)}"
            for campo, msgs in error.message_dict.items()
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
    # La cuenta de la imprenta (grupo Imprenta, ver panel_imprenta) es de solo
    # lectura por diseño: si sus credenciales se filtran, el daño se limita a
    # ver números y sindicatos ya enviados, nunca a poder inyectar afiliados.
    if request.user.groups.filter(name=GRUPO_IMPRENTA).exists():
        raise PermissionDenied

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

        if len(df) > MAX_FILAS_EXCEL:
            messages.error(
                request,
                f"El archivo tiene {len(df)} filas y el máximo permitido es "
                f"{MAX_FILAS_EXCEL}. Divídelo en varios envíos.",
            )
            return render(request, 'gestion/subir_excel.html')

        afiliados_validos = []
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
                # Se excluye sindicato_usuario de la validación: no viene del
                # Excel sino de request.user (usuario autenticado, ya existente
                # en la BD), y validarlo dispararía una consulta por cada fila
                # solo para reconfirmar una clave foránea que sabemos válida.
                afiliado.full_clean(exclude=['sindicato_usuario'])
                afiliados_validos.append(afiliado)
            except ValidationError as e:
                errores.append(f"Fila {numero_fila}: {_formatear_error_validacion(e)}")
            except (KeyError, ValueError, TypeError):
                errores.append(f"Fila {numero_fila}: datos incompletos o con formato incorrecto.")

        # Criterio "todo o nada": basta con que UNA fila no cuadre con el
        # formato esperado para abortar la subida entera sin guardar nada. Es
        # preferible que el sindicato corrija el archivo y lo vuelva a enviar
        # completo antes que dejar una carga a medias, difícil de detectar y de
        # deshacer (y que induciría a resubir el archivo, duplicando las filas
        # que sí se habían guardado).
        if errores:
            resumen = "; ".join(errores[:10])
            extra = f" (y {len(errores) - 10} más)" if len(errores) > 10 else ""
            messages.error(
                request,
                f"No se ha guardado ningún afiliado: {len(errores)} fila(s) tienen "
                f"errores de formato. Corrige el archivo y vuelve a subirlo. "
                f"Detalle: {resumen}{extra}",
            )
            return render(request, 'gestion/subir_excel.html')

        if afiliados_validos:
            # Una sola transacción para el lote completo: si algo falla al
            # persistir, no queda ni un afiliado suelto ni un registro de subida
            # que no se corresponda con lo realmente guardado.
            try:
                with transaction.atomic():
                    # bulk_create_with_history (no el bulk_create normal): el
                    # bulk_create de Django no dispara señales y dejaría a los
                    # afiliados SIN registro en el historial de auditoría, que
                    # aquí es obligatorio (trazabilidad RGPD de datos personales).
                    bulk_create_with_history(afiliados_validos, Afiliado)
                    RegistroSubida.objects.create(
                        sindicato=request.user,
                        cantidad_afiliados=len(afiliados_validos),
                        nombre_archivo=excel_file.name,
                    )
            except DatabaseError:
                logger.exception(
                    "Error guardando el lote de afiliados de %s", request.user,
                )
                messages.error(
                    request,
                    "No se pudo guardar la subida por un error al acceder a los "
                    "datos. No se ha guardado ningún afiliado; inténtalo de nuevo.",
                )
                return render(request, 'gestion/subir_excel.html')

            # No se registra el nombre del archivo: lo elige quien sube, y es
            # habitual que lleve dentro el nombre de la persona
            # ("altas_maria_fernandez.xlsx"). Este registro sale del ámbito
            # cifrado y se conserva dos años, así que ahí no entran datos
            # personales. Si hace falta el nombre para una incidencia, está en
            # RegistroSubida, que se localiza por usuario y fecha.
            registrar(
                ACCIONES.AFILIADOS_CARGADOS,
                peticion=request,
                cantidad=len(afiliados_validos),
            )

            messages.success(
                request,
                f"¡Éxito! Se han procesado y guardado {len(afiliados_validos)} "
                f"afiliados correctamente.",
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


# 4. PANEL DE LA IMPRENTA
@login_required
def panel_imprenta(request):
    # La cuenta de la imprenta se crea a mano (no hay alta pública para ella,
    # a diferencia de los sindicatos) y se le añade al grupo 'Imprenta' desde
    # el admin. Sin pertenecer a ese grupo, cualquier otra cuenta autenticada
    # —incluido un sindicato— tiene acceso denegado.
    if not request.user.groups.filter(name=GRUPO_IMPRENTA).exists():
        registrar(ACCIONES.ACCESO_DENEGADO, peticion=request, vista='panel_imprenta')
        raise PermissionDenied

    # .values() en vez de instancias de Afiliado: así nombre_apellidos y
    # notas_historicas ni siquiera se leen de la base de datos, y no hay forma
    # de que una plantilla los muestre por descuido. Solo lo ya marcado como
    # IMPRESO: antes de que tú decidas enviarlo, la imprenta no debe saber ni
    # que esos números existen.
    lote = list(
        Afiliado.objects.filter(estado_impresion=Afiliado.ESTADO_IMPRESO)
        .values('sindicato_codigo', 'num_afiliado', 'fecha_envio_imprenta')
        .order_by('-fecha_envio_imprenta', 'sindicato_codigo'),
    )

    registrar(ACCIONES.LOTE_IMPRESION_CONSULTADO, peticion=request, cantidad=len(lote))

    return render(request, 'gestion/panel_imprenta.html', {'lote': lote})
