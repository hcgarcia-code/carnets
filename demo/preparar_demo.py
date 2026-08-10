"""Prepara un entorno de demostración para probar la usabilidad.

Crea usuarios de prueba y genera dos archivos Excel de ejemplo (uno correcto y
otro con errores deliberados) para poder recorrer la aplicación a mano.

NO toca la base de datos de desarrollo: se ejecuta contra la que indique la
variable de entorno DATABASE_NAME.
"""

import os
import sys
from pathlib import Path

import django

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / 'sistema_carnets'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sistema_carnets.settings')
django.setup()

import pandas as pd  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402

DEMO = Path(__file__).resolve().parent

# Contraseñas de demostración, visibles a propósito: este entorno es local y
# desechable, nunca debe usarse en producción.
USUARIOS = [
    ('sindicato_prueba', 'Demo.Carnets.2026', False),
    ('admin_prueba', 'Demo.Carnets.2026', True),
]

for username, password, es_admin in USUARIOS:
    User.objects.filter(username=username).delete()
    if es_admin:
        User.objects.create_superuser(username=username, password=password)
    else:
        User.objects.create_user(username=username, password=password)
    print(f"Usuario creado: {username} / {password}{'  (superusuario)' if es_admin else ''}")

COLUMNAS = [
    'Confederacion', 'Fed_Local', 'Fed_Sectorial', 'Sindicato',
    'Num_Afiliado', 'Nombre_Apellidos', 'Lengua', 'Estado',
]

NOMBRES = [
    'Ana García Ruiz', 'Luis Martín Soto', 'Marta Pérez Vidal',
    'Jordi Puig Blanch', 'Carmen Díaz Nieto', 'Iker Sáez Otero',
]


def fila(num, nombre, **cambios):
    base = {
        'Confederacion': '01 - Territorial Centro',
        'Fed_Local': '12345 - Local Madrid',
        'Fed_Sectorial': '02 - Sector Servicios',
        'Sindicato': '003 - Sindicato Comercio',
        'Num_Afiliado': str(num),
        'Nombre_Apellidos': nombre,
        'Lengua': 'A',
        'Estado': 'ALTA',
    }
    base.update(cambios)
    return base


# 1) Archivo correcto: debe guardarse entero.
correcto = [
    fila(100001 + i, nombre, Lengua='C' if i % 3 == 0 else 'A')
    for i, nombre in enumerate(NOMBRES)
]
pd.DataFrame(correcto, columns=COLUMNAS).to_excel(
    DEMO / 'ejemplo_correcto.xlsx', index=False, engine='openpyxl',
)
print(f"Excel correcto: demo/ejemplo_correcto.xlsx ({len(correcto)} filas)")

# 2) Archivo con errores deliberados en filas distintas: no debe guardar NADA.
#    Fila 3 del Excel -> Confederacion no numérica.
#    Fila 5 del Excel -> Lengua fuera de las opciones válidas.
#    Fila 6 del Excel -> Num_Afiliado con menos de 6 dígitos.
con_errores = [
    fila(200001, NOMBRES[0]),
    fila(200002, NOMBRES[1], Confederacion='XX - Codigo mal'),
    fila(200003, NOMBRES[2]),
    fila(200004, NOMBRES[3], Lengua='Z'),
    fila(12, NOMBRES[4]),
]
pd.DataFrame(con_errores, columns=COLUMNAS).to_excel(
    DEMO / 'ejemplo_con_errores.xlsx', index=False, engine='openpyxl',
)
print(f"Excel con errores: demo/ejemplo_con_errores.xlsx ({len(con_errores)} filas, 3 erróneas)")
