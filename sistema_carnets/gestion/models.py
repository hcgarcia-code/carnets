from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models
from simple_history.models import HistoricalRecords

from .crypto import CampoTextoCifrado


class PerfilSindicato(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    # Texto libre que declara quién se está dando de alta ("CGT Rama Metal
    # Barcelona"). El username por sí solo no basta para que el administrador
    # sepa a qué sindicato aprobar: es la única pista con la que decide.
    nombre_identificativo = models.CharField(
        max_length=255, blank=True,
        verbose_name="Sindicato o rama que declara ser (para aprobar el alta)",
    )
    acuerdo_aceptado = models.BooleanField(
        default=False, verbose_name="¿Ha aceptado el acuerdo de protección de datos?",
    )
    fecha_aceptacion = models.DateTimeField(
        null=True, blank=True, verbose_name="Fecha y hora de la firma",
    )
    ip_aceptacion = models.GenericIPAddressField(
        null=True, blank=True, verbose_name="Dirección IP de la firma",
    )

    def __str__(self):
        return f"Perfil de {self.usuario.username}"


class Afiliado(models.Model):
    LENGUA_CHOICES = [('A', 'Castellano'), ('C', 'Catalán')]
    ESTADO_CHOICES = [('ALTA', 'Alta'), ('BAJA', 'Baja')]

    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_IMPRESO = 'IMPRESO'
    ESTADO_IMPRESION_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente de imprimir'),
        (ESTADO_IMPRESO, 'Impreso'),
    ]

    sindicato_usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='afiliados')

    confederacion_territorial = models.CharField(
        max_length=2, validators=[RegexValidator(r'^\d{2}$', 'Debe ser de 2 dígitos.')],
    )
    federacion_local = models.CharField(
        max_length=5, validators=[RegexValidator(r'^\d{5}$', 'Debe ser de 5 dígitos.')],
    )
    federacion_sectorial = models.CharField(
        max_length=2, validators=[RegexValidator(r'^\d{2}$', 'Debe ser de 2 dígitos.')],
    )
    sindicato_codigo = models.CharField(
        max_length=3, validators=[RegexValidator(r'^\d{3}$', 'Debe ser de 3 dígitos.')],
    )
    # Cifrados en reposo: identifican a una persona concreta como afiliada a un
    # sindicato, que es dato de categoría especial (RGPD Art. 9). Ver crypto.py.
    num_afiliado = CampoTextoCifrado(
        max_length=6, validators=[RegexValidator(r'^\d{6}$', 'Debe ser de 6 dígitos.')],
    )

    nombre_apellidos = CampoTextoCifrado(max_length=255)
    lengua = models.CharField(max_length=1, choices=LENGUA_CHOICES)
    estado = models.CharField(max_length=50, choices=ESTADO_CHOICES)

    fecha_expedicion = models.DateField(null=True, blank=True)
    notas_historicas = CampoTextoCifrado(
        blank=True, null=True, help_text="Registro de reemisiones históricas.",
    )

    estado_impresion = models.CharField(
        max_length=10,
        choices=ESTADO_IMPRESION_CHOICES,
        default=ESTADO_PENDIENTE,
        verbose_name="Estado de impresión",
    )
    fecha_envio_imprenta = models.DateTimeField(
        null=True, blank=True, verbose_name="Fecha de envío a imprenta",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True)
    history = HistoricalRecords()

    def __str__(self):
        # Sin nombre ni número de afiliado a propósito. Django guarda str(obj)
        # en django_admin_log.object_repr cada vez que alguien crea, cambia o
        # borra un afiliado desde el admin, y esa tabla no está cifrada, no se
        # purga y viaja en todos los backups: incluir aquí los datos personales
        # dejaría una copia en claro de justo lo que cifra CampoTextoCifrado.
        # En pantalla los datos se siguen viendo (list_display y el formulario);
        # lo que no se hace es dejarlos escritos en la base de datos.
        return f"Afiliado #{self.pk} (sindicato {self.sindicato_codigo})"

    @property
    def fecha_expedicion_mmyy(self):
        if self.fecha_expedicion:
            return self.fecha_expedicion.strftime('%m/%y')
        return ""


class RegistroSubida(models.Model):
    sindicato = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subidas')
    fecha = models.DateTimeField(auto_now_add=True)
    cantidad_afiliados = models.IntegerField()
    nombre_archivo = models.CharField(max_length=255)

    def __str__(self):
        fecha = self.fecha.strftime('%d/%m/%Y')
        return f"{self.sindicato.username} - {self.cantidad_afiliados} afiliados ({fecha})"


class Notificacion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    mensaje = models.CharField(max_length=500)
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Notificación para {self.usuario.username} ({self.fecha_creacion:%d/%m/%Y %H:%M})"
