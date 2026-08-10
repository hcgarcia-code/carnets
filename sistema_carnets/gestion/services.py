from django.utils import timezone

from .models import Afiliado, Notificacion


def marcar_como_impresos_y_notificar(queryset):
    """Marca los afiliados del queryset como impresos y notifica a cada sindicato.

    Agrupa por sindicato_usuario para que cada notificación solo contenga el
    recuento de SUS PROPIOS afiliados: nunca se interpola texto libre del
    afiliado (p. ej. nombre_apellidos) en el mensaje, precisamente para que un
    dato malicioso introducido en un campo de texto no tenga forma de llegar
    al mensaje de notificación de otro sindicato ni del propio.

    Devuelve el número de afiliados marcados como impresos.
    """
    afiliados = list(queryset.select_related('sindicato_usuario'))
    if not afiliados:
        return 0

    ahora = timezone.now()
    usuarios_por_id = {}
    conteo_por_usuario_id = {}
    for afiliado in afiliados:
        afiliado.estado_impresion = Afiliado.ESTADO_IMPRESO
        afiliado.fecha_envio_imprenta = ahora
        usuario = afiliado.sindicato_usuario
        usuarios_por_id[usuario.id] = usuario
        conteo_por_usuario_id[usuario.id] = conteo_por_usuario_id.get(usuario.id, 0) + 1

    Afiliado.objects.bulk_update(afiliados, ['estado_impresion', 'fecha_envio_imprenta'])

    fecha_legible = ahora.strftime('%d/%m/%Y %H:%M')
    notificaciones = [
        Notificacion(
            usuario=usuarios_por_id[usuario_id],
            mensaje=(
                f"Tu paquete de {conteo} afiliado(s) ha sido enviado a imprenta "
                f"y descargado el {fecha_legible}."
            ),
        )
        for usuario_id, conteo in conteo_por_usuario_id.items()
    ]
    Notificacion.objects.bulk_create(notificaciones)

    return len(afiliados)
