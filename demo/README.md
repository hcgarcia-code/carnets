# Entorno de demostración (pruebas de usabilidad)

Arranca la aplicación con datos de prueba para recorrerla a mano, **sin tocar la
base de datos de desarrollo ni la de producción**: todo vive en
`demo/db_demo.sqlite3`, que está en `.gitignore` y se puede borrar cuando quieras.

## Puesta en marcha

### Linux / macOS

Desde un clon recién hecho, sin nada preparado:

```bash
cd carnets

# 1. Entorno virtual y dependencias (solo la primera vez)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Archivo .env con una SECRET_KEY generada al vuelo (solo la primera vez).
#    Sin SECRET_KEY la aplicación no arranca. El .env nunca se sube a git.
cat > .env <<EOF
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(50))')
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost,testserver
EOF

# 3. Base de datos de demo y datos de prueba (solo la primera vez)
export DATABASE_NAME="$PWD/demo/db_demo.sqlite3"
python sistema_carnets/manage.py migrate
python demo/preparar_demo.py

# 4. Arrancar el servidor
python sistema_carnets/manage.py runserver 127.0.0.1:8000 --insecure
```

En arranques posteriores basta con los pasos 4 y las dos líneas de entorno:

```bash
cd carnets
source venv/bin/activate
export DATABASE_NAME="$PWD/demo/db_demo.sqlite3"
python sistema_carnets/manage.py runserver 127.0.0.1:8000 --insecure
```

### Windows (PowerShell)

```powershell
cd carnets

python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Crear el .env a mano con, al menos: SECRET_KEY, DEBUG=False y
# ALLOWED_HOSTS=127.0.0.1,localhost,testserver  (ver .env.example)

$env:DATABASE_NAME = "$PWD\demo\db_demo.sqlite3"
python sistema_carnets\manage.py migrate
python demo\preparar_demo.py
python sistema_carnets\manage.py runserver 127.0.0.1:8000 --insecure
```

Luego abre <http://127.0.0.1:8000/login/> en el navegador.

> `--insecure` sirve los archivos estáticos (el CSS del panel de administración y
> el PDF del acuerdo legal) con `DEBUG=False`. Es solo para pruebas locales: en
> producción los sirve el servidor web tras un `collectstatic`.

## Usuarios de prueba

| Usuario | Contraseña | Para qué |
|---|---|---|
| `sindicato_prueba` | `Demo.Carnets.2026` | Recorrido normal de un sindicato |
| `admin_prueba` | `Demo.Carnets.2026` | Panel de administración (`/admin/`) |

Son credenciales **de demostración**, deliberadamente visibles. Nunca deben
existir en el servidor real.

## Archivos Excel de ejemplo

`preparar_demo.py` genera dos archivos para probar los dos caminos:

- **`ejemplo_correcto.xlsx`** (6 filas válidas) → se guarda entero, aviso verde.
- **`ejemplo_con_errores.xlsx`** (5 filas, 2 con formato inválido) → **no se
  guarda nada**, aviso rojo indicando fila y columna:

  > No se ha guardado ningún afiliado: 2 fila(s) tienen errores de formato.
  > Corrige el archivo y vuelve a subirlo. Detalle: Fila 3: columna
  > Confederacion: Debe ser de 2 dígitos.; Fila 5: columna Lengua: Valor 'Z' no
  > es una opción válida.

## Recorrido sugerido

1. `/subir-datos/` sin sesión → debe mandarte al login.
2. Login con contraseña incorrecta → aviso de credenciales.
3. Login correcto → pantalla del **acuerdo RGPD** (obligatoria).
4. Intenta ir a `/subir-datos/` sin firmar → te devuelve al acuerdo.
5. Firma el acuerdo → llegas a la pantalla de carga.
6. Sube `ejemplo_con_errores.xlsx` → no se guarda nada, aviso con fila y columna.
7. Sube `ejemplo_correcto.xlsx` → se guardan los 6 afiliados.
8. Sube un archivo que no sea `.xlsx` → rechazo por formato.
9. `/notificaciones/` → bandeja del sindicato.
10. `/admin/` con `admin_prueba` → listado de afiliados, filtros y buscador.

## Reiniciar la demo desde cero

```bash
rm demo/db_demo.sqlite3        # Windows: del demo\db_demo.sqlite3
```

y repite los pasos 1 y 2.
