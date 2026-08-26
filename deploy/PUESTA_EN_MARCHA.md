# Puesta en marcha del 2.0, paso a paso

Guía completa para levantar el sistema en PythonAnywhere sustituyendo al beta.
Cada paso dice **qué escribir**, **qué debe salir** y **qué hacer si sale otra
cosa**.

Se asume que ya tienes el `beta.json` descargado (ver
[`migrar_desde_beta.md`](migrar_desde_beta.md)).

---

## Antes de nada: tres avisos que te ahorran un mal día

**1. La clave de cifrado no se puede perder.** Los nombres y números de
afiliado se guardan cifrados. Si pierdes la clave, esos datos son
irrecuperables — no hay forma de descifrarlos, ni tú ni nadie. Guárdala en dos
sitios distintos antes de seguir.

**2. Activa el segundo factor ANTES de recargar la web.** Si recargas primero,
el admin exigirá un segundo factor que aún no existe y te quedas fuera de tu
propio sistema. Se recupera desde la consola, pero mejor no pasar por ahí. Es
el paso 9 y está donde está por ese motivo.

**3. El plan gratuito de PythonAnywhere no basta.** Dos cosas del sistema no
funcionan en él:

| Necesitas | Por qué |
|---|---|
| **Correo saliente** | El plan gratuito solo permite conexiones a una lista blanca de sitios. Sin correo, **la recuperación de contraseña no funciona** y las alertas de auditoría no llegan |
| **Tareas programadas** | El gratuito da una sola tarea diaria; hacen falta tres (auditoría cada hora, copia diaria, expurgado trimestral) |

Puedes levantarlo en el gratuito para probar, pero sabiendo que esas dos cosas
quedan muertas.

---

## Paso 0 — Reunir lo que hace falta

Ten a mano, en un archivo de texto que borrarás después:

- [ ] Usuario y contraseña de PythonAnywhere
- [ ] El archivo `beta.json`
- [ ] La dirección de correo del administrador
- [ ] Datos del servidor SMTP (servidor, puerto, usuario, contraseña)
- [ ] Un teléfono con una app de autenticación (Google Authenticator, Aegis, FreeOTP…)

---

## Paso 1 — Guardar una copia del beta antes de tocarlo

Vas a sustituir la aplicación que está en marcha. Si algo sale mal, esto es la
vuelta atrás.

En una **consola bash** de PythonAnywhere:

```bash
cd ~
tar czf copia_beta_antes_del_2.tar.gz sistema_carnets
ls -lh copia_beta_antes_del_2.tar.gz
```

**Debe salir:** un archivo de varios MB.

Descárgalo desde la pestaña **Files** y guárdalo fuera del servidor.

---

## Paso 2 — Traer el código nuevo

Sigues en la consola bash:

```bash
cd ~
mv sistema_carnets sistema_carnets_beta_viejo
git clone https://github.com/hcgarcia-code/carnets.git carnets
cd carnets
git checkout rgpd/plazo-de-conservacion
```

> Cuando la rama esté fusionada en `main`, sáltate el `git checkout`.

**Debe salir:** `Switched to a new branch 'rgpd/plazo-de-conservacion'`.

**Comprueba que está todo:**

```bash
ls sistema_carnets/manage.py && ls deploy/
```

---

## Paso 3 — Crear el entorno e instalar dependencias

```bash
mkvirtualenv --python=/usr/bin/python3.12 carnets2
pip install -r ~/carnets/requirements.txt
```

**Debe salir:** `Successfully installed …` con una lista larga.

**Si dice que `carnets2` ya existe**, usa `workon carnets2` y sigue.

Apunta la ruta del entorno, la necesitas en el paso 7:

```bash
echo $VIRTUAL_ENV
```

---

## Paso 4 — Generar las claves

Dos claves distintas. **No las confundas.**

```bash
python -c "import secrets; print('SECRET_KEY =', secrets.token_urlsafe(64))"
python -c "import base64,os; print('CLAVE_CIFRADO =', base64.b64encode(os.urandom(32)).decode())"
```

Copia las dos salidas a tu archivo temporal.

> **La segunda es la crítica.** Cifra los nombres y números de afiliado.
> Guárdala también en un gestor de contraseñas o un papel en la caja fuerte del
> sindicato. Si se pierde, los datos de los 3918 afiliados quedan ilegibles
> para siempre.

---

## Paso 5 — Escribir el `.env`

```bash
cd ~/carnets
nano .env
```

Pega esto y **sustituye lo que está entre `<>`**:

```
SECRET_KEY=<la primera clave del paso 4>
DEBUG=False
ALLOWED_HOSTS=carnetscgt.eu.pythonanywhere.com

CARNETS_ENCRYPTION_KEYS=k1:<la segunda clave del paso 4>

CACHE_BACKEND=django.core.cache.backends.db.DatabaseCache
CACHE_LOCATION=cache_carnets

SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO:https

AUDITORIA_LOG_PATH=/home/carnetscgt/auditoria.jsonl

EMAIL_HOST=<tu servidor smtp>
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<usuario del correo>
EMAIL_HOST_PASSWORD=<contraseña del correo>
DEFAULT_FROM_EMAIL=<direccion desde la que se envia>
```

Guarda con **Ctrl+O**, Enter, y sal con **Ctrl+X**.

**Detalles que importan:**

- El `k1:` delante de la clave de cifrado **es obligatorio**. Es el
  identificador de la clave y permite rotarla más adelante sin reescribir la
  base de datos.
- `DEBUG=False` sin excepciones. Con `True`, cualquier error muestra la
  configuración entera, incluidas las claves.
- `SECURE_PROXY_SSL_HEADER` hace falta porque PythonAnywhere termina el HTTPS
  antes de llegar a tu aplicación. Sin esto, Django cree que la conexión es
  insegura y entra en un bucle de redirecciones.

**Cierra el archivo a los demás:**

```bash
chmod 600 .env
```

---

## Paso 6 — Preparar la base de datos

```bash
cd ~/carnets
python sistema_carnets/manage.py migrate
python sistema_carnets/manage.py createcachetable
```

**Debe salir:** una lista de `Applying … OK`.

La segunda orden crea la tabla que usa la caché. **Es obligatoria**: los
límites de intentos de acceso guardan ahí su cuenta, y sin una caché compartida
entre procesos el límite se multiplica por el número de trabajadores y se
reinicia solo. El sistema se niega a desplegarse sin ella.

---

## Paso 7 — Configurar la web

En el navegador, pestaña **Web** de PythonAnywhere.

**7.1 — Virtualenv**

En *Virtualenv*, escribe la ruta que apuntaste en el paso 3
(`/home/carnetscgt/.virtualenvs/carnets2`).

**7.2 — Archivo WSGI**

Pincha en el enlace del *WSGI configuration file*, borra todo lo que haya y pon:

```python
import os
import sys

ruta = '/home/carnetscgt/carnets/sistema_carnets'
if ruta not in sys.path:
    sys.path.insert(0, ruta)

os.environ['DJANGO_SETTINGS_MODULE'] = 'sistema_carnets.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Guarda con el botón verde.

> No hace falta cargar el `.env` aquí: la propia configuración lo lee al
> arrancar, y lo busca **en la raíz del repositorio** (`~/carnets/.env`), no
> dentro de `sistema_carnets/`. Por eso el paso 5 lo crea ahí.

**7.3 — Archivos estáticos**

En *Static files*, añade una fila:

| URL | Directory |
|---|---|
| `/static/` | `/home/carnetscgt/carnets/sistema_carnets/staticfiles` |

Y genera esos archivos en la consola:

```bash
cd ~/carnets
python sistema_carnets/manage.py collectstatic --noinput
```

**7.4 — Forzar HTTPS**

En la pestaña Web, marca **Force HTTPS**.

**Todavía no recargues.** Falta el paso 9.

---

## Paso 8 — Comprobar que la configuración es segura

```bash
cd ~/carnets
python sistema_carnets/manage.py check --deploy --fail-level WARNING
```

**Debe salir:** `System check identified no issues`.

**Si sale algún error, no sigas.** Está diseñado para pararte: significa que
algo de la configuración dejaría el sistema expuesto. Los más comunes:

| Mensaje | Qué falta |
|---|---|
| `security.W008` | `SECURE_SSL_REDIRECT=True` en el `.env` |
| `security.W012` / `W016` | `SESSION_COOKIE_SECURE` o `CSRF_COOKIE_SECURE` |
| `security.W004` | `SECURE_HSTS_SECONDS` |
| `security.W009` | La `SECRET_KEY` es corta: regenérala con el paso 4 |
| `gestion.E001` | Falta `createcachetable` o el `CACHE_BACKEND` del `.env` |
| `security.W018` | `DEBUG` no está en `False` |

---

## Paso 9 — Crear tu cuenta de administrador y el segundo factor

**Este es el paso que no puedes saltarte ni dejar para después.**

```bash
cd ~/carnets
python sistema_carnets/manage.py createsuperuser
```

Te pedirá usuario, correo y contraseña. **Usa una contraseña larga**: es la
única cuenta que ve los datos descifrados.

Ahora el segundo factor:

```bash
python sistema_carnets/manage.py activar_2fa <el usuario que acabas de crear>
```

**Debe salir:** una línea larga que empieza por `otpauth://`.

Cópiala. En tu teléfono, abre la app de autenticación y añade una cuenta
**pegando esa dirección** (todas admiten pegar un enlace `otpauth://`; si la
tuya no, usa la parte que va después de `secret=`).

**Comprueba que la app te muestra un código de 6 dígitos que cambia cada 30
segundos.** Si no lo ves, repite el comando antes de continuar: sin esto no
podrás entrar al admin.

---

## Paso 10 — Recargar y entrar

Pestaña **Web** → botón verde **Reload**.

Abre `https://carnetscgt.eu.pythonanywhere.com/admin/`.

**Debe pedirte:** usuario, contraseña **y** el código de 6 dígitos.

**Si dice "Error 500"**, mira el registro de errores en la pestaña Web
(*Error log*) y busca la última línea que empiece por el nombre de una
excepción.

**Si te pide el código y lo rechaza**, comprueba que la hora del teléfono es
correcta: los códigos dependen del reloj.

---

## Paso 11 — Importar las cuentas del beta

Sube `beta.json` con la pestaña **Files** a `/home/carnetscgt/`.

Primero en seco:

```bash
cd ~/carnets
python sistema_carnets/manage.py importar_desde_beta ~/beta.json --dry-run
```

**Debe salir:**

```
Cuentas de sindicato: 54
Perfiles: 39
Afiliados: 3918
Se omitirian 2 cuenta(s) de administrador…
```

Si cuadra, ahora de verdad:

```bash
python sistema_carnets/manage.py importar_desde_beta ~/beta.json
```

**Debe salir:** `Cuentas importadas: 54`, `Perfiles… 54`, `Afiliados
importados: 3511` y un aviso de 407 descartados.

Los 407 descartados son las filas con las columnas corridas. **Es lo esperado**:
esos afiliados entran después, con la tabla ya limpia (paso 12).

**Borra el volcado en cuanto termines:**

```bash
rm ~/beta.json
```

---

## Paso 12 — Subir la tabla de afiliados limpia

Entra en `https://carnetscgt.eu.pythonanywhere.com/` con una cuenta de
sindicato, o desde el admin, y sube el Excel corregido por la vía normal
(`/subir-datos/`).

El sistema valida fila a fila y **no guarda nada si alguna falla**, así que si
te dice que hay errores, corriges el archivo y lo vuelves a subir entero.

---

## Paso 13 — Programar las tres tareas

Pestaña **Tasks** de PythonAnywhere. Añade estas tres:

| Cuándo | Orden |
|---|---|
| Cada hora | `cd /home/carnetscgt/carnets && /home/carnetscgt/.virtualenvs/carnets2/bin/python sistema_carnets/manage.py revisar_auditoria` |
| Diaria, 03:30 | `cd /home/carnetscgt/carnets && /home/carnetscgt/.virtualenvs/carnets2/bin/python sistema_carnets/manage.py backup_a_s3_cifrado` |
| Diaria, 04:00 | `cd /home/carnetscgt/carnets && /home/carnetscgt/.virtualenvs/carnets2/bin/python sistema_carnets/manage.py expurgar_afiliados` |

**Sin estas tareas, tres controles que la documentación da por activos no se
ejecutan nunca**: la vigilancia del registro de accesos, las copias de
seguridad y el borrado de los datos cuyo plazo ha vencido.

La tercera está a diario en vez de trimestral porque PythonAnywhere no ofrece
esa frecuencia; ejecutarla a diario es inofensivo (los días que no hay nada
vencido, no hace nada).

> El backup necesita cuenta de S3 y Vault configurados. Si aún no los tienes,
> deja esa tarea para más adelante — pero anótalo, porque hasta entonces **no
> hay de dónde restaurar**.

---

## Paso 14 — Comprobación final

```bash
cd ~/carnets
python sistema_carnets/manage.py shell
```

Pega esto:

```python
from django.contrib.auth.models import User
from django.db import connection
from gestion.models import Afiliado, PerfilSindicato
print("cuentas:", User.objects.count())
print("perfiles con acuerdo firmado:", PerfilSindicato.objects.filter(acuerdo_aceptado=True).count())
print("afiliados:", Afiliado.objects.count())
with connection.cursor() as c:
    c.execute("SELECT COUNT(*) FROM gestion_afiliado WHERE nombre_apellidos NOT LIKE 'v1$%'")
    print("EN CLARO (debe ser 0):", c.fetchone()[0])
```

**La última línea tiene que dar 0.** Si da cualquier otra cosa, hay datos sin
cifrar y hay que parar y revisarlo.

Sal con `exit()`.

**Prueba también, desde el navegador:**

- [ ] Entrar con una cuenta de sindicato migrada, con su contraseña de siempre
- [ ] Que **no** le pida volver a firmar el acuerdo
- [ ] Pedir "¿Has olvidado tu contraseña?" y que llegue el correo
- [ ] Que el panel de imprenta solo muestre lotes ya enviados

---

## Paso 15 — Avisar a los sindicatos

Un correo corto a las 54 direcciones:

> El sistema de carnets se ha actualizado. **Tu usuario y tu contraseña son los
> mismos** y tus afiliados están ya cargados: no tienes que hacer nada.
>
> La dirección sigue siendo https://carnetscgt.eu.pythonanywhere.com
>
> Si olvidas la contraseña, ahora puedes recuperarla tú desde el enlace de la
> pantalla de acceso.

---

## Paso 16 — Retirar el beta

Cuando lleves unos días sin incidencias:

```bash
rm -rf ~/sistema_carnets_beta_viejo
```

Guarda el `.tar.gz` del paso 1 en un sitio seguro unos meses más, y bórralo
también después: **contiene todos los datos sin cifrar**.

---

## Si algo sale mal: volver atrás

```bash
cd ~
mv carnets carnets_fallido
mv sistema_carnets_beta_viejo sistema_carnets
```

Luego, en la pestaña Web, devuelve el virtualenv y el archivo WSGI a como
estaban y pulsa **Reload**. El beta vuelve a funcionar.

---

## Resumen de lo que no puedes saltarte

| # | Paso | Si te lo saltas |
|---|---|---|
| 4 | Guardar la clave de cifrado en dos sitios | Datos irrecuperables si la pierdes |
| 6 | `createcachetable` | El despliegue se detiene; el límite de intentos no funciona |
| 8 | `check --deploy` en verde | Sirves cookies y contraseñas sin protección |
| 9 | `activar_2fa` **antes** de recargar | Te quedas fuera de tu propio admin |
| 11 | `rm ~/beta.json` | Queda el fichero de afiliación en claro en el servidor |
| 13 | Las tres tareas | Tres controles figuran activos sin estarlo |
| 14 | Que "EN CLARO" dé 0 | Datos personales sin cifrar en la base |
