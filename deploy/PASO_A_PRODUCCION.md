# Pasar el 2.0 a la dirección principal

Llevar el sistema de la web de pruebas a la dirección definitiva, y jubilar el
beta.

Esta guía **no repite** lo que ya está escrito en otro sitio. Se apoya en:

| Para | Mira |
|---|---|
| Montar la aplicación de cero | `PUESTA_EN_MARCHA.md` |
| Traer cuentas y afiliados del beta | `migrar_desde_beta.md` |
| Los tres cron | `tareas_programadas.md` |

---

## Antes de nada: qué dirección es "la principal"

En PythonAnywhere la dirección principal de una cuenta **no se elige**: es
siempre `<usuario>.eu.pythonanywhere.com`. Con la cuenta `carnetscgt`, la
principal es:

```
carnetscgt.eu.pythonanywhere.com
```

**Y ahí es donde está ahora el beta.** No es una web libre a la que mudarse: es
la que hay que sustituir. Y como el beta corre sobre Python 3.10 y el 2.0 sobre
3.12, no basta con reconfigurarla: hay que borrarla y crearla de nuevo (paso 6).
Eso no toca ningún archivo.

> Si lo que quieres es otra dirección distinta (`carnets.eu.pythonanywhere.com`,
> por ejemplo), eso es **otra cuenta de PythonAnywhere**, no una opción dentro
> de la actual. Esta guía serviría igual, pero el beta se quedaría en pie y
> habría que apagarlo aparte.

---

## El orden, y por qué es ese

La aplicación web de la dirección principal **hay que recrearla**, porque el
beta corre sobre Python 3.10 y el 2.0 sobre 3.12, y esa versión no se puede
cambiar después de crear la web (paso 6).

Ahora bien, **borrar una aplicación web no borra archivos**. El código del beta,
su base de datos y sus virtualenvs se quedan en su carpeta. De ahí salen dos
cosas que simplifican el plan:

- **El volcado del beta puedes sacarlo cuando quieras**, también después de que
  su web deje de existir: el `dumpdata` se ejecuta desde una consola contra la
  carpeta del beta, no contra su web.
- **No hace falta "congelar" el beta desactivando cuentas.** Recrear la web *es*
  el corte: desde ese momento el beta no es alcanzable y nadie puede subir nada
  más ahí.

Lo que sí importa es que **los datos estén dentro antes de que los sindicatos
lleguen**. Si recreas la web primero e importas después, hay un rato en el que
entran y no encuentran a sus afiliados.

```
1. Decidir con qué base de datos se queda producción   ← lo que más se olvida
2. Volcado del beta
3. Configurar el correo
4. Importar en el 2.0        ← con el 2.0 todavía en prueba-carnetscgt
5. Comprobar
6. Recrear la web sobre 3.12 ← esto es el corte (y una caída de minutos)
7. Avisar a los sindicatos
8. Borrar el volcado y la base del beta
```

---

## Paso 1 — Decidir con qué base de datos se queda producción

**Esto es lo que el atajo hace urgente.** Si repuntas la dirección al proyecto
del 2.0, se lleva consigo *su* base de datos: la que has estado usando para
probar. Todo lo que haya ahí —cuentas de prueba, afiliados de ejemplo— pasa a
ser producción.

Mira qué tiene antes de decidir:

```bash
python sistema_carnets/manage.py shell -c "
from django.contrib.auth.models import User
from gestion.models import Afiliado, RegistroSubida
print('usuarios:', [(u.username, u.is_active, u.is_superuser) for u in User.objects.all()])
print('afiliados:', Afiliado.objects.count())
print('subidas:', RegistroSubida.objects.count())
"
```

Dos caminos:

- **Limpiar lo de prueba** y quedarte con esa base. Borra las cuentas de
  ejemplo desde el admin y, si hubiera afiliados de prueba, bórralos también
  —del admin, que aquí sí es lo correcto: son datos inventados, no una
  supresión del Art. 17—.
- **Empezar con una base vacía**: renombra el SQLite del 2.0, vuelve a correr
  `migrate`, `createcachetable`, `createsuperuser` y `activar_2fa`. Es más
  trabajo pero no deja nada de prueba por medio.

**Guarda la contraseña y el segundo factor del superusuario que vaya a quedar**,
porque es la única cuenta que descifra datos personales.

---

## Paso 2 — Sacar el volcado del beta

El procedimiento completo, con lo que trae de sucio el volcado real, está en
`migrar_desde_beta.md`. En corto, desde una consola Bash:

```bash
# Con el entorno y la carpeta del BETA
PYTHONPATH=/home/carnetscgt python manage.py dumpdata \
    auth.User gestion.PerfilSindicato gestion.Afiliado --indent 2 -o beta.json
```

**Ese archivo es el fichero de afiliación en claro.** No lo mandes por correo,
no lo dejes en Descargas y bórralo en cuanto termines (paso 8).

> **Sácalo en una franja de poco uso.** Lo que un sindicato suba al beta después
> de este volcado no aparecerá en el 2.0. No se pierde —el beta sigue en su
> carpeta hasta el paso 8— pero habría que repetirle la carga.

---

## Paso 3 — El correo, antes de seguir

La aplicación ya está montada: es la misma que la web de pruebas. Lo que falta
comprobar es el `.env`, que además de lo de `PUESTA_EN_MARCHA.md` necesita **las
tres variables de correo**:

```
DEFAULT_FROM_EMAIL=soporte-carnets@cgt.org.es
ADMINS_CORREOS=quien-vigila@cgt.org.es
EMAIL_HOST=...            # con EMAIL_HOST_USER y EMAIL_HOST_PASSWORD
```

Sin las dos primeras el sistema arranca igual y falla en silencio:

- **Sin `DEFAULT_FROM_EMAIL`**, los correos salen desde `webmaster@localhost` y
  el destino los rechaza. La reposición de contraseña —que el manual de usuario
  da como vía principal— deja de llegar, y ningún envío da error.
- **Sin `ADMINS_CORREOS`**, las alertas de `revisar_auditoria` (rachas de
  bloqueos, exportaciones de datos personales) se envían a nadie. El cron sigue
  corriendo y el aviso no existe.

Las dos cosas las detecta ahora el `check --deploy` (`gestion.E002` y
`gestion.E003`), así que:

```bash
python sistema_carnets/manage.py check --deploy --fail-level WARNING
```

**Tiene que decir `no issues`.** Si no, no sigas.

---

## Paso 4 — Importar el volcado

```bash
python sistema_carnets/manage.py importar_desde_beta beta.json --dry-run
python sistema_carnets/manage.py importar_desde_beta beta.json
```

Lee los avisos que saca. `migrar_desde_beta.md` explica qué hacer con las filas
sucias del volcado real (407 `estado` corruptos, que son las mismas filas que
los 344 `lengua` inválidos: un problema, no dos).

---

## Paso 5 — Comprobar antes de tocar la web

Con el 2.0 todavía en la dirección de pruebas:

```bash
python sistema_carnets/manage.py check --deploy --fail-level WARNING
```

Y en el navegador, entrando **con una cuenta real importada**:

- [ ] Entra con su usuario y su contraseña del beta (deben valer tal cual)
- [ ] Sus afiliados están ahí
- [ ] `/subir-datos/` ofrece la plantilla y la descarga
- [ ] `/ayuda/` y `/ayuda/manual/` se ven sin sesión
- [ ] "Salir" cierra la sesión de verdad
- [ ] **Pide una reposición de contraseña y comprueba que el correo llega.**
      Es lo único que no puedes verificar sin enviar de verdad, y es justo lo
      que va a usar medio mundo la primera semana

En la base de datos, que los datos entraron cifrados (`migrar_desde_beta.md`,
paso 5).

---

## Paso 6 — Recrear la aplicación web

**El beta corre sobre Python 3.10 y el 2.0 sobre 3.12**, y PythonAnywhere fija
la versión de Python **al crear** la aplicación web: no hay forma de cambiarla
después. Una web de 3.10 no puede usar un virtualenv de 3.12.

Bajar el 2.0 a 3.10 tampoco es camino: `pandas 3.0.5` exige Python >=3.11.

Así que hay que borrar la aplicación web y crearla de nuevo sobre 3.12.

> **Borrar una aplicación web en PythonAnywhere NO borra tus archivos.** El
> código del beta, su base de datos y sus virtualenvs se quedan donde están; lo
> que desaparece es la configuración de la web y su archivo WSGI. Por eso esto
> es seguro, y por eso el volcado del beta (paso 2) se puede seguir sacando
> desde una consola aunque su web ya no exista.

### Antes de borrar nada

**Copia a un archivo de texto el contenido del WSGI de `prueba-carnetscgt`.** Al
crear la web nueva, PythonAnywhere genera un WSGI en blanco y hay que pegarlo:
si no lo tienes copiado, te toca reescribirlo con la web principal caída.

Apunta también el resto de la configuración de `prueba-carnetscgt`:

| Campo | Valor |
|---|---|
| **Source code** | `/home/carnetscgt/carnets` |
| **Working directory** | `/home/carnetscgt/carnets` |
| **Virtualenv** | `entorno_sindicato` |
| **Static files** | `/static/` → `/home/carnetscgt/carnets/sistema_carnets/staticfiles` |

### Los pasos

1. Pestaña **Web** → `carnetscgt.eu.pythonanywhere.com` → **Delete this web app**
2. **Add a new web app** → mismo dominio → **Manual configuration** →
   **Python 3.12**

   Manual configuration, **no** la opción "Django": esa monta un proyecto nuevo
   vacío encima y no es lo que quieres.
3. Rellena Source code, Working directory y Virtualenv con lo de la tabla
4. Abre el archivo WSGI que ha generado, **borra todo su contenido** y pega el
   que copiaste
5. Añade la fila de **Static files**
6. Comprueba que `ALLOWED_HOSTS` del `.env` incluye la dirección. Si no, la web
   responde 400 a todo y parece que se ha roto el despliegue
7. `python sistema_carnets/manage.py collectstatic --noinput`
8. **Reload**

### La ventana de caída

Entre el paso 1 y el 8 la dirección principal no responde. Son minutos, pero
son minutos con el sistema caído para todo el mundo, así que **hazlo en una
franja de poco uso** y ten el WSGI ya copiado antes de empezar.

**`prueba-carnetscgt` sigue funcionando todo el rato**, apuntando al mismo
proyecto y la misma base de datos. Si alguien necesita entrar durante la
ventana, esa dirección le sirve. Déjala en pie también después: no estorba y te
da una puerta de entrada si la principal se queda en 400.

> Al apuntar las dos webs al mismo proyecto comparten base de datos: lo que
> hagas por una lo ves por la otra. Es lo que quieres aquí, pero conviene
> saberlo antes de "probar algo" en la de pruebas.

**La vuelta atrás** es recrear la web apuntando al beta —sobre Python 3.10,
porque su virtualenv es de 3.10— con su WSGI. Cópiate también ese antes de
borrar nada, por si acaso. Mientras no borres la base del beta (paso 8), el
camino de vuelta está entero.

---

## Paso 7 — Avisar a los sindicatos

```bash
# En seco: dice a quién escribiría y enseña el mensaje. No envía nada.
python sistema_carnets/manage.py avisar_version_2 --url https://carnetscgt.eu.pythonanywhere.com

# Cuando lo veas bien:
python sistema_carnets/manage.py avisar_version_2 \
    --url https://carnetscgt.eu.pythonanywhere.com --enviar
```

**Un mensaje por destinatario**, nunca todos en el mismo correo: si no, cada
sindicato vería la lista completa de los demás con sus direcciones, que es una
comunicación de datos a terceros que nadie ha autorizado.

Escribe solo a los **sindicatos activos**. Deja fuera a la imprenta, al personal
de administración y a las cuentas pendientes de aprobación.

**Mira la lista de "sindicatos SIN correo"** que saca en seco: a esos no les
llega nada. Hay que avisarles por teléfono.

El texto está en `gestion/templates/gestion/correo/version_2.txt`. Retócalo
antes si quieres; el comando lo lee de ahí.

> **No lleva control de "ya enviado".** Si lo ejecutas dos veces, escribe dos
> veces. Mira siempre la salida en seco antes.

---

## Paso 8 — Cerrar

```bash
rm beta.json
```

Y la copia de tu equipo, **y la papelera**. Mientras exista, hay un fichero de
afiliación en claro fuera de todo control técnico.

**Elimina la base de datos del beta.** Repuntar la dirección le quitó el acceso
por web, pero su SQLite sigue en su carpeta: una copia completa del fichero de
afiliación **sin cifrar, sin segundo factor y sin auditoría**. Que no sea
alcanzable desde fuera no la hace inocua — sigue estando en el disco, y en una
copia de seguridad del servidor.

Bórrala solo cuando el paso 5 esté comprobado y lleves unos días sin incidencias:
mientras exista, es también tu vuelta atrás.

Por último, los tres cron (`tareas_programadas.md`): `revisar_auditoria` cada
hora, `backup_a_s3_cifrado` a diario y `expurgar_afiliados` trimestral. Sin
ellos el sistema funciona, pero no vigila, no respalda y no caduca nada.

---

## Si algo sale mal

| Síntoma | Casi siempre es |
|---|---|
| `400 Bad Request` en todo | Falta la dirección nueva en `ALLOWED_HOSTS` |
| Sale sin estilos, o el logo roto | No se corrió `collectstatic`, o la fila de *Static files* apunta mal |
| `ModuleNotFoundError` | Falta `PYTHONPATH=/home/carnetscgt` en el WSGI, o no está activado `entorno_sindicato` |
| `ImproperlyConfigured` al arrancar | `AUDITORIA_LOG_PATH` apunta a una ruta que no existe; el mensaje dice qué variable es |
| El correo de contraseña no llega | `DEFAULT_FROM_EMAIL` sin configurar (lo detecta `check --deploy`) |
| Un sindicato no puede entrar | Su cuenta no se importó: mira los avisos del paso 4 |
| Los sindicatos ven el sistema vacío | Se recreó la web antes de importar |
| `ModuleNotFoundError` tras recrear la web | Se creó sobre Python 3.10, o el virtualenv no es `entorno_sindicato` |

**La vuelta atrás es recrear la web apuntando al beta**, sobre Python 3.10 y con
su WSGI —cópiate ese archivo antes de borrar nada—. Mientras no borres su base
de datos, el camino de vuelta está entero: de ahí que el paso 8 vaya el último y
solo con el paso 5 comprobado.
