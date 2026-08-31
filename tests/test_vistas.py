"""Tests de las vistas principales: firma del acuerdo legal y carga de Excel.

Cubren el recorrido HTTP completo (petición -> respuesta) de las dos vistas más
importantes de la aplicación, que hasta ahora solo estaban probadas de forma
indirecta. Además de la funcionalidad, verifican propiedades de seguridad clave:

- Todas las rutas exigen sesión iniciada.
- No se puede subir datos sin haber firmado antes el acuerdo RGPD.
- Los afiliados creados quedan siempre asignados al sindicato autenticado
  (aislamiento estricto entre sindicatos).
- El registro legal de consentimiento captura fecha e IP, tomando la primera
  IP de X-Forwarded-For cuando la petición llega tras un proxy.
"""

import io

import pandas as pd
import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from django.urls import reverse

from gestion.models import Afiliado, PerfilSindicato, RegistroSubida
from gestion.views import MAX_FILAS_EXCEL

pytestmark = pytest.mark.django_db

COLUMNAS = [
    'Confederacion', 'Fed_Local', 'Fed_Sectorial', 'Sindicato',
    'Num_Afiliado', 'Nombre_Apellidos', 'Lengua', 'Estado',
]


def _crear_usuario(username='sindicato_a'):
    # Contraseña fija solo para usuarios de prueba, no es un secreto real.
    return User.objects.create_user(username=username, password='clave-segura-123')  # noqa: S106


def _firmar_acuerdo(usuario):
    return PerfilSindicato.objects.create(usuario=usuario, acuerdo_aceptado=True)


def _fila_valida(**overrides):
    # Los códigos llegan en el formato real de la plantilla oficial
    # ("01 - Descripción"); la vista se queda con la parte anterior al guion.
    fila = {
        'Confederacion': '01 - Territorial',
        'Fed_Local': '12345 - Local',
        'Fed_Sectorial': '02 - Sectorial',
        'Sindicato': '003 - Sindicato',
        'Num_Afiliado': '123456',
        'Nombre_Apellidos': 'Nombre Apellido',
        'Lengua': 'A',
        'Estado': 'ALTA',
    }
    fila.update(overrides)
    return fila


def _excel_subido(filas, columnas=COLUMNAS, nombre='afiliados.xlsx'):
    df = pd.DataFrame(filas, columns=columnas)
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine='openpyxl')
    return SimpleUploadedFile(
        nombre,
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


# --- Control de acceso: login obligatorio ---

def test_subir_excel_requiere_login(client):
    respuesta = client.get(reverse('subir_excel'))
    assert respuesta.status_code == 302
    assert reverse('login') in respuesta['Location']


def test_acuerdo_legal_requiere_login(client):
    respuesta = client.get(reverse('acuerdo_legal'))
    assert respuesta.status_code == 302
    assert reverse('login') in respuesta['Location']


# --- Bloqueo por acuerdo RGPD no firmado ---

def test_sin_acuerdo_firmado_redirige_al_acuerdo(client):
    usuario = _crear_usuario()
    client.force_login(usuario)
    respuesta = client.get(reverse('subir_excel'))
    assert respuesta.status_code == 302
    assert respuesta['Location'] == reverse('acuerdo_legal')


def test_acuerdo_legal_get_renderiza_si_no_aceptado(client):
    usuario = _crear_usuario()
    client.force_login(usuario)
    respuesta = client.get(reverse('acuerdo_legal'))
    assert respuesta.status_code == 200


def test_acuerdo_ya_aceptado_redirige_a_subir(client):
    usuario = _crear_usuario()
    _firmar_acuerdo(usuario)
    client.force_login(usuario)
    respuesta = client.get(reverse('acuerdo_legal'))
    assert respuesta.status_code == 302
    assert respuesta['Location'] == reverse('subir_excel')


# --- Registro legal del consentimiento (fecha + IP) ---

def test_aceptar_acuerdo_registra_consentimiento_fecha_e_ip(client):
    usuario = _crear_usuario()
    client.force_login(usuario)

    respuesta = client.post(reverse('acuerdo_legal'), REMOTE_ADDR='203.0.113.7')

    assert respuesta.status_code == 302
    assert respuesta['Location'] == reverse('subir_excel')
    perfil = PerfilSindicato.objects.get(usuario=usuario)
    assert perfil.acuerdo_aceptado is True
    assert perfil.fecha_aceptacion is not None
    assert perfil.ip_aceptacion == '203.0.113.7'


def test_acuerdo_ignora_la_cabecera_si_no_hay_proxy_declarado(client):
    """Sin `PROXIES_DE_CONFIANZA`, X-Forwarded-For no vale nada.

    Este test comprobaba antes lo contrario: que se guardaba la PRIMERA entrada
    de la cabecera. Esa es precisamente la que puede escribir el cliente, así
    que la constancia de la firma del acuerdo recogía un valor elegido por quien
    firmaba. Servida la aplicación sin proxy delante, lo correcto es no creerse
    la cabecera en absoluto.
    """
    usuario = _crear_usuario()
    client.force_login(usuario)

    client.post(
        reverse('acuerdo_legal'),
        HTTP_X_FORWARDED_FOR='198.51.100.23, 10.0.0.1',
        REMOTE_ADDR='10.0.0.1',
    )

    perfil = PerfilSindicato.objects.get(usuario=usuario)
    assert perfil.ip_aceptacion == '10.0.0.1'


def test_acuerdo_toma_la_ip_que_puso_el_proxy_y_no_la_del_cliente(client, settings):
    """Con un proxy declarado, se lee la cabecera por la DERECHA: la última
    entrada la añade el proxy en el que confiamos."""
    settings.PROXIES_DE_CONFIANZA = ['10.0.0.1']
    usuario = _crear_usuario()
    client.force_login(usuario)

    client.post(
        reverse('acuerdo_legal'),
        HTTP_X_FORWARDED_FOR='1.2.3.4, 198.51.100.23',
        REMOTE_ADDR='10.0.0.1',
    )

    perfil = PerfilSindicato.objects.get(usuario=usuario)
    assert perfil.ip_aceptacion == '198.51.100.23', 'se ha guardado la IP forjada'


# --- Carga de Excel: flujo funcional principal ---

def test_subir_excel_valido_crea_afiliados_y_registro(client):
    usuario = _crear_usuario()
    _firmar_acuerdo(usuario)
    client.force_login(usuario)

    archivo = _excel_subido([
        _fila_valida(Num_Afiliado='111111', Nombre_Apellidos='Ana Uno'),
        _fila_valida(Num_Afiliado='222222', Nombre_Apellidos='Beto Dos'),
    ])
    respuesta = client.post(reverse('subir_excel'), {'archivo_excel': archivo})

    assert respuesta.status_code == 200
    assert Afiliado.objects.count() == 2
    registro = RegistroSubida.objects.get()
    assert registro.cantidad_afiliados == 2
    assert registro.sindicato == usuario


def test_afiliados_creados_se_asignan_al_sindicato_autenticado(client):
    # Propiedad de aislamiento: un sindicato nunca puede crear afiliados a
    # nombre de otro. La vista ignora cualquier dato de propietario del Excel.
    usuario = _crear_usuario('sindicato_real')
    otro = _crear_usuario('sindicato_ajeno')
    _firmar_acuerdo(usuario)
    client.force_login(usuario)

    archivo = _excel_subido([_fila_valida()])
    client.post(reverse('subir_excel'), {'archivo_excel': archivo})

    assert Afiliado.objects.count() == 1
    assert Afiliado.objects.get().sindicato_usuario == usuario
    assert not Afiliado.objects.filter(sindicato_usuario=otro).exists()


def test_una_fila_con_formato_incorrecto_aborta_toda_la_subida(client):
    # Criterio "todo o nada": si UNA sola fila no cuadra con el formato
    # esperado, no se guarda ninguna. Así el sindicato corrige el archivo y lo
    # vuelve a subir entero, en vez de quedarse con una carga a medias que es
    # difícil de detectar y de deshacer.
    usuario = _crear_usuario()
    _firmar_acuerdo(usuario)
    client.force_login(usuario)

    archivo = _excel_subido([
        _fila_valida(Num_Afiliado='111111'),
        _fila_valida(Confederacion='XX - No numerica', Num_Afiliado='222222'),
    ])
    respuesta = client.post(reverse('subir_excel'), {'archivo_excel': archivo})

    assert Afiliado.objects.count() == 0
    assert RegistroSubida.objects.count() == 0
    mensajes = [str(m) for m in respuesta.context['messages']]
    assert any('Fila 3' in m for m in mensajes)  # 2ª fila de datos = fila 3 del Excel
    assert any('no se ha guardado' in m.lower() for m in mensajes)


def test_subida_valida_completa_se_guarda_entera(client):
    # La contrapartida del "todo o nada": si todas las filas son correctas,
    # se guardan todas.
    usuario = _crear_usuario()
    _firmar_acuerdo(usuario)
    client.force_login(usuario)

    archivo = _excel_subido([
        _fila_valida(Num_Afiliado='111111'),
        _fila_valida(Num_Afiliado='222222'),
        _fila_valida(Num_Afiliado='333333'),
    ])
    client.post(reverse('subir_excel'), {'archivo_excel': archivo})

    assert Afiliado.objects.count() == 3


def test_subir_excel_sin_acuerdo_no_crea_nada(client):
    usuario = _crear_usuario()
    client.force_login(usuario)  # sin firmar el acuerdo

    archivo = _excel_subido([_fila_valida()])
    respuesta = client.post(reverse('subir_excel'), {'archivo_excel': archivo})

    assert respuesta.status_code == 302
    assert respuesta['Location'] == reverse('acuerdo_legal')
    assert Afiliado.objects.count() == 0


def test_subir_excel_rechaza_extension_no_permitida(client):
    usuario = _crear_usuario()
    _firmar_acuerdo(usuario)
    client.force_login(usuario)

    malicioso = SimpleUploadedFile(
        'afiliados.csv', b'no soy un xlsx', content_type='text/csv',
    )
    respuesta = client.post(reverse('subir_excel'), {'archivo_excel': malicioso})

    assert respuesta.status_code == 200
    assert Afiliado.objects.count() == 0
    mensajes = [str(m) for m in respuesta.context['messages']]
    assert any('xlsx' in m.lower() for m in mensajes)


def test_subir_excel_rechaza_columnas_faltantes(client):
    usuario = _crear_usuario()
    _firmar_acuerdo(usuario)
    client.force_login(usuario)

    columnas_incompletas = [c for c in COLUMNAS if c != 'Num_Afiliado']
    fila = _fila_valida()
    del fila['Num_Afiliado']
    archivo = _excel_subido([fila], columnas=columnas_incompletas)
    respuesta = client.post(reverse('subir_excel'), {'archivo_excel': archivo})

    assert Afiliado.objects.count() == 0
    mensajes = [str(m) for m in respuesta.context['messages']]
    assert any('Num_Afiliado' in m for m in mensajes)


# --- Rendimiento y robustez de la carga masiva ---

def test_carga_masiva_no_hace_una_consulta_por_fila(client, django_assert_max_num_queries):
    # Con guardado fila a fila, 50 afiliados = 50 INSERT + overhead. Al insertar
    # por lotes el número de consultas deja de crecer con el número de filas.
    usuario = _crear_usuario()
    _firmar_acuerdo(usuario)
    client.force_login(usuario)

    filas = [
        _fila_valida(Num_Afiliado=str(100000 + i), Nombre_Apellidos=f'Afiliado {i}')
        for i in range(50)
    ]
    archivo = _excel_subido(filas)

    with django_assert_max_num_queries(15):
        client.post(reverse('subir_excel'), {'archivo_excel': archivo})

    assert Afiliado.objects.count() == 50


def test_rechaza_excel_con_demasiadas_filas(client):
    # Un .xlsx de pocos MB puede contener cientos de miles de filas: sin un
    # límite explícito, una sola subida podría agotar memoria/CPU del servidor.
    usuario = _crear_usuario()
    _firmar_acuerdo(usuario)
    client.force_login(usuario)

    filas = [
        _fila_valida(Num_Afiliado=str(100000 + i))
        for i in range(MAX_FILAS_EXCEL + 1)
    ]
    archivo = _excel_subido(filas)
    respuesta = client.post(reverse('subir_excel'), {'archivo_excel': archivo})

    assert Afiliado.objects.count() == 0
    mensajes = [str(m) for m in respuesta.context['messages']]
    assert any('filas' in m.lower() for m in mensajes)


def test_fallo_al_guardar_no_deja_afiliados_a_medias(client, monkeypatch):
    # La escritura debe ser atómica: si algo falla al persistir el lote, no
    # puede quedar media subida guardada (estado inconsistente para el sindicato).
    usuario = _crear_usuario()
    _firmar_acuerdo(usuario)
    client.force_login(usuario)

    def _falla(*args, **kwargs):
        raise DatabaseError("fallo simulado al insertar el lote")

    monkeypatch.setattr(RegistroSubida.objects, 'create', _falla)

    archivo = _excel_subido([
        _fila_valida(Num_Afiliado='111111'),
        _fila_valida(Num_Afiliado='222222'),
    ])
    respuesta = client.post(reverse('subir_excel'), {'archivo_excel': archivo})

    assert respuesta.status_code == 200
    assert Afiliado.objects.count() == 0
    assert RegistroSubida.objects.count() == 0
    mensajes = [str(m) for m in respuesta.context['messages']]
    assert any('no se pudo' in m.lower() or 'error' in m.lower() for m in mensajes)


def test_carga_masiva_conserva_el_historial_de_auditoria(client):
    # Regresión: el bulk_create de Django NO dispara señales y dejaría a los
    # afiliados sin registro en el historial (django-simple-history), perdiendo
    # la trazabilidad RGPD. Debe usarse bulk_create_with_history.
    usuario = _crear_usuario()
    _firmar_acuerdo(usuario)
    client.force_login(usuario)

    archivo = _excel_subido([
        _fila_valida(Num_Afiliado='111111'),
        _fila_valida(Num_Afiliado='222222'),
    ])
    client.post(reverse('subir_excel'), {'archivo_excel': archivo})

    assert Afiliado.objects.count() == 2
    assert Afiliado.history.count() == 2


# --- Calidad del aviso de error: fila y columna tal como las ve el usuario ---

def test_el_error_indica_la_fila_y_la_columna_del_excel(client):
    # El aviso debe ser accionable sin conocer el modelo interno: número de fila
    # tal como se ve en Excel y nombre de la columna tal como aparece en la
    # cabecera del archivo (p. ej. "Confederacion", no "confederacion_territorial").
    usuario = _crear_usuario()
    _firmar_acuerdo(usuario)
    client.force_login(usuario)

    archivo = _excel_subido([
        _fila_valida(Num_Afiliado='111111'),
        _fila_valida(Confederacion='XX - No numerica', Num_Afiliado='222222'),
    ])
    respuesta = client.post(reverse('subir_excel'), {'archivo_excel': archivo})

    aviso = ' '.join(str(m) for m in respuesta.context['messages'])
    assert 'Fila 3' in aviso
    assert 'Confederacion' in aviso
    assert 'confederacion_territorial' not in aviso  # nombre interno, no se muestra
    assert '2 dígitos' in aviso


def test_el_aviso_lista_todas_las_filas_con_error(client):
    # Si varias filas fallan, el usuario debe poder corregirlas todas de una vez.
    usuario = _crear_usuario()
    _firmar_acuerdo(usuario)
    client.force_login(usuario)

    archivo = _excel_subido([
        _fila_valida(Confederacion='XX - mala', Num_Afiliado='111111'),
        _fila_valida(Num_Afiliado='222222'),
        _fila_valida(Lengua='Z', Num_Afiliado='333333'),
    ])
    respuesta = client.post(reverse('subir_excel'), {'archivo_excel': archivo})

    aviso = ' '.join(str(m) for m in respuesta.context['messages'])
    assert 'Fila 2' in aviso   # 1ª fila de datos
    assert 'Fila 4' in aviso   # 3ª fila de datos
    assert 'Lengua' in aviso
    assert Afiliado.objects.count() == 0
