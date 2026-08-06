# Estado del Proyecto — App CarnetsCGT

_Última actualización: 2026-08-06_

## 1. Resumen

Se ha tomado la aplicación Django `sistema_carnets` (gestión de altas/bajas de afiliados sindicales mediante carga de Excel) y se ha llevado a un estado funcional, con entorno de desarrollo reproducible y una primera pasada de blindaje de seguridad. Antes de esta intervención **el proyecto no arrancaba**: tenía un error estructural y un `SyntaxError` que impedían ejecutar `manage.py` o cualquier comando de Django.

## 2. Hallazgo crítico (requiere decisión del usuario)

**`sistema_carnets/db.sqlite3` estaba commiteado en el historial de git** (commit `f33a63b "Add files via upload"`) y contiene datos reales:
- Un afiliado real: nombre completo y número de afiliado.
- Hashes de contraseña de 2 usuarios reales, incluyendo un superusuario.

Se ha sacado el archivo del tracking (`git rm --cached` + `.gitignore`), por lo que **no se seguirá exponiendo hacia adelante**. Pero como el repositorio ya fue empujado a `origin`, los datos **siguen presentes en el historial de git remoto** hasta que se reescriba el historial (`git filter-repo` / `BFG`) y se haga `force-push`. Esto es una operación destructiva sobre una rama compartida y no se ha ejecutado sin confirmación explícita. Recomendación: coordinar una ventana para reescribir el historial y rotar las contraseñas de esos 2 usuarios (por si acaso).

## 3. Corrección estructural crítica

`manage.py` define `DJANGO_SETTINGS_MODULE = 'sistema_carnets.settings'`, lo que requiere el layout estándar de Django: una carpeta de proyecto (con `manage.py`) que contiene un **subpaquete** con el mismo nombre (`settings.py`, `urls.py`, `wsgi.py`, `asgi.py`). En el repositorio original, esos 5 archivos estaban sueltos junto a `manage.py`, sin el subpaquete — probablemente se aplanó la estructura al subir los archivos por la interfaz web de GitHub.

Efecto: cualquier comando de Django (`manage.py check`, `runserver`, `test`, etc.) fallaba con `ModuleNotFoundError: No module named 'sistema_carnets'`.

**Corrección:** se movieron `__init__.py`, `settings.py`, `urls.py`, `wsgi.py`, `asgi.py` a `sistema_carnets/sistema_carnets/` (con `git mv`, conservando el historial). Esto también corrige `BASE_DIR`, que ahora apunta correctamente a la carpeta del proyecto (donde vive `db.sqlite3`).

## 4. Medidas de seguridad implementadas

1. **`SECRET_KEY` vacío → variable de entorno.** El código original tenía `SECRET_KEY = ` (línea vacía, `SyntaxError`). Ahora se carga con `python-dotenv` desde `.env` (`os.environ['SECRET_KEY']`, sin valor por defecto: si falta, la app falla explícitamente en vez de arrancar insegura). Se generó una clave nueva con `django.core.management.utils.get_random_secret_key()` para el `.env` local (no versionado).
2. **`DEBUG` y `ALLOWED_HOSTS` movidos a `.env`**, con valores por defecto seguros para desarrollo local (`DEBUG=False`, `ALLOWED_HOSTS=127.0.0.1,localhost`).
3. **`bandit -r .`**: 0 hallazgos (antes no podía ni ejecutarse por el `SyntaxError`).
4. **Inyección SQL**: revisado todo el acceso a base de datos — se hace exclusivamente vía el ORM de Django (`Afiliado.objects.create/get_or_create`, `queryset.update`, etc.), que parametriza las consultas automáticamente. No hay `.raw()`, `cursor.execute()` ni concatenación de strings para SQL en ningún punto del código. Se añadió un test de regresión que falla si alguien introduce SQL crudo en el futuro.
5. **Path traversal**: revisado el manejo de archivos. El Excel subido se procesa **en memoria** (`pd.read_excel(excel_file)`), nunca se escribe a disco con un nombre derivado del input del usuario, y los dos archivos estáticos servidos (`texto_afiliacion.pdf`, `plantilla_sindicatos.xls`) usan rutas fijas en las plantillas, no rutas construidas dinámicamente. No hay riesgo de path traversal. Test de regresión incluido.
6. **Validación estricta de la carga de Excel** (`gestion/views.py::cargar_datos_sindicato`):
   - Se rechaza cualquier archivo que no termine en `.xlsx` (antes se aceptaba cualquier archivo, solo el `accept=".xlsx"` del `<input>` HTML lo sugería, que es trivial de saltarse).
   - Se rechaza cualquier archivo mayor a 5 MB (antes no había límite → riesgo de denegación de servicio).
   - Se valida que existan todas las columnas requeridas antes de procesar filas.
   - **Cada fila ahora pasa por `Afiliado.full_clean()` antes de guardarse.** Antes se usaba `Afiliado.objects.create(...)` directamente, que en Django **no ejecuta los validadores del modelo** (los `RegexValidator` definidos en `models.py` nunca se estaban aplicando realmente). Ahora una fila con datos mal formados se rechaza con un mensaje claro por fila, en vez de guardarse sin validar o tumbar toda la carga.
   - Corregido un bug de saneamiento: `pandas` a veces lee columnas numéricas como float (p. ej. `num_afiliado` "2568" se leía como `"2568.0"`), lo que rompía el `zfill(6)`. Se sanea quitando el `.0` antes de rellenar con ceros.
7. **No se filtran detalles internos de excepciones al usuario final.** Antes, cualquier error (`except Exception as e`) se mostraba literalmente al usuario (`str(e)`), lo que puede revelar rutas internas, nombres de columnas esperadas de forma confusa, o detalles de la pila. Ahora los errores inesperados se registran con `logger.exception(...)` (lado servidor) y al usuario se le muestra un mensaje genérico.
8. **`db.sqlite3` y todos los `__pycache__/*.pyc` desatrackeados** de git (ver hallazgo crítico arriba) y añadidos a `.gitignore` junto con `venv/`, `.env`, `staticfiles/`.
9. **`DEFAULT_AUTO_FIELD` explícito** (`BigAutoField`), eliminando warnings del `system check` de Django y alineándolo con las migraciones ya generadas.

### Fuera de alcance (recomendaciones, no aplicadas)

- La IP capturada en `acuerdo_legal` se lee de `HTTP_X_FORWARDED_FOR`, que es un header controlable por el cliente si la app no está detrás de un proxy de confianza que lo sobrescriba. Si el despliegue final (PythonAnywhere u otro) no garantiza eso, conviene fijar `SECURE_PROXY_SSL_HEADER`/confiar solo en el proxy real.
- No hay límite de intentos de login (rate limiting). Django no lo trae de fábrica; se podría añadir `django-axes` o similar si hay preocupación por fuerza bruta sobre `/login/`.
- Los datos de afiliados (nombre, nº de afiliado) se guardan en texto plano en la base de datos, tal como indica `CLAUDE.md` que debería evaluarse cifrado en reposo para datos sensibles — no se ha implementado cifrado a nivel de campo en esta pasada; requeriría decidir una estrategia (cifrado de aplicación vs. cifrado de disco) con el usuario.

## 5. Estructura de archivos

```
carnets/
├── .env                  # Secretos reales (NO versionado)
├── .env.example           # Plantilla de variables de entorno (versionado, vacío)
├── .gitignore
├── CLAUDE.md               # Instrucciones del proyecto
├── conftest.py             # Inicializa Django para que pytest pueda importar los módulos de la app
├── estado_proyecto.md      # Este documento
├── pyproject.toml          # Config de bandit, ruff y pytest
├── requirements.txt
├── tests/
│   ├── __init__.py
│   └── test_seguridad.py   # 14 tests: config, validación de inputs, ausencia de SQL crudo
├── venv/                   # Entorno virtual (NO versionado)
└── sistema_carnets/        # Carpeta del proyecto Django (contiene manage.py)
    ├── manage.py
    ├── db.sqlite3           # Base de datos local (NO versionado desde ahora)
    ├── sistema_carnets/     # Paquete de configuración Django
    │   ├── __init__.py
    │   ├── settings.py       # Ahora carga SECRET_KEY/DEBUG/ALLOWED_HOSTS desde .env
    │   ├── urls.py
    │   ├── wsgi.py
    │   └── asgi.py
    └── gestion/              # App: afiliados y perfiles de sindicato
        ├── models.py          # Afiliado, PerfilSindicato (con RegexValidator por campo)
        ├── views.py           # acuerdo_legal, cargar_datos_sindicato (validación reforzada)
        ├── admin.py           # Acciones de admin: asignar fecha, exportar Excel para imprenta
        ├── apps.py
        ├── tests.py           # Stub vacío por defecto de Django (los tests reales están en /tests)
        ├── migrations/
        ├── static/documentos/ # Plantilla Excel y texto legal de afiliación
        └── templates/gestion/ # login, acuerdo_legal, subir_excel
```

## 6. Entorno de desarrollo

Esta sesión corrió en un contenedor Linux (no Windows), así que el entorno virtual se creó con los comandos equivalentes de Linux (`python3 -m venv venv`, `source venv/bin/activate`). Los comandos documentados en `CLAUDE.md` (PowerShell/CMD) funcionarán igual en tu máquina Windows local una vez que clones la rama, ya que toda la configuración vive en `requirements.txt` / `pyproject.toml`, no en el entorno.

Dependencias instaladas (`requirements.txt`):
- **Producción**: `Django==5.2.17`, `pandas==3.0.5`, `openpyxl==3.1.5`, `python-dotenv==1.2.2`
  (nota: el docstring original de `settings.py` menciona "Django 6.0.6", pero esa versión no existe todavía en PyPI — la última estable es la 5.2.17 LTS, totalmente compatible con el código actual).
- **Calidad/seguridad**: `pytest==9.1.1`, `ruff==0.16.1`, `bandit==1.9.4`

## 7. Verificación final

Ejecutados desde la raíz del repositorio, con el entorno virtual activado:

| Comando | Resultado |
|---|---|
| `pytest tests/ -v` | 14 passed — código de salida 0 |
| `ruff check .` | All checks passed! — código de salida 0 |
| `bandit -r . -c pyproject.toml` | No issues identified — código de salida 0 |
| `python sistema_carnets/manage.py check` | System check identified no issues (0 silenced) |

## 8. Próximos pasos sugeridos

1. Decidir y ejecutar la purga del historial de git para `db.sqlite3` (hallazgo crítico, sección 2).
2. Rotar las contraseñas de los usuarios `CONFEDERAL` y `sindicato_madrid` una vez purgado el historial.
3. Evaluar cifrado en reposo para los campos de datos personales de `Afiliado`, según lo que pide `CLAUDE.md`.
4. Revisar la confianza en `X-Forwarded-For` según el proveedor de despliegue final.
5. Añadir tests de integración de las vistas (`acuerdo_legal`, `cargar_datos_sindicato`) usando el cliente de pruebas de Django — requeriría añadir `pytest-django` o usar `manage.py test`, ya que no está entre las dependencias pedidas actualmente.
