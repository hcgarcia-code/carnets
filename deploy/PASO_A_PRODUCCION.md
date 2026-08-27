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
la que hay que reconfigurar para que sirva el 2.0 en vez del beta. No hace falta
borrarla ni crear ninguna otra.

> Si lo que quieres es otra dirección distinta (`carnets.eu.pythonanywhere.com`,
> por ejemplo), eso es **otra cuenta de PythonAnywhere**, no una opción dentro
> de la actual. Esta guía serviría igual, pero el beta se quedaría en pie y
> habría que apagarlo aparte.

---

## El orden importa (pero menos de lo que parece)

No hay que borrar ni recrear ninguna web. La dirección es una **propiedad de la
aplicación web**, y el código es otra: en la pestaña Web se le cambia a
`carnetscgt.eu.pythonanywhere.com` a qué proyecto apunta, y ya está. El beta se
queda en su carpeta, con su base de datos intacta, sin dirección.

Eso simplifica dos cosas:

- **El volcado del beta puedes sacarlo cuando quieras**, también después de
  quitarle la dirección: el `dumpdata` se ejecuta desde una consola contra la
  carpeta del beta, no contra su web.
- **No hace falta "congelar" el beta desactivando cuentas.** Repuntar la
  dirección *es* el corte: en cuanto recargas, el beta deja de ser accesible y
  nadie puede subir nada más ahí.

Lo que sí importa es que **los datos estén dentro antes de que los sindicatos
lleguen**. Si cambias la dirección primero e importas después, hay un rato en el
que entran y no encuentran a sus afiliados.

```
1. Decidir con qué base de datos se queda producción   ← lo que más se olvida
2. Volcado del beta
3. Configurar el correo
4. Importar en el 2.0        ← con el 2.0 todavía en prueba-carnetscgt
5. Comprobar
6. Repuntar la dirección     ← esto es el corte
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

## Paso 5 — Comprobar antes de cambiar la dirección

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

## Paso 6 — Repuntar la dirección

**No hay que borrar ni recrear ninguna web.** Se le cambia a la que ya existe en
`carnetscgt.eu.pythonanywhere.com` a qué proyecto apunta. El código y la base de
datos del beta se quedan donde están; lo único que pierde es la dirección.

En la pestaña **Web**, sobre `carnetscgt.eu.pythonanywhere.com`, copia lo que ya
tiene configurado `prueba-carnetscgt`:

| Campo | Valor |
|---|---|
| **Source code** | `/home/carnetscgt/carnets` |
| **Working directory** | `/home/carnetscgt/carnets` |
| **Virtualenv** | `entorno_sindicato` |
| **WSGI configuration file** | El del 2.0, con `PYTHONPATH=/home/carnetscgt` |
| **Static files** | `/static/` → `/home/carnetscgt/carnets/sistema_carnets/staticfiles` |

Lo más práctico es abrir las dos webs en dos pestañas del navegador y copiar
campo por campo, incluido el contenido del archivo WSGI.

Antes de recargar:

```bash
python sistema_carnets/manage.py collectstatic --noinput
```

Y **`ALLOWED_HOSTS` del `.env` tiene que incluir la dirección nueva**. Si no, la
web responde 400 a todo y parece que se ha roto el despliegue.

Entonces sí: **Reload**.

> **Deja `prueba-carnetscgt` en pie**, apuntando al mismo proyecto. No estorba y
> te da una dirección por la que entrar si la principal se queda en 400 por un
> `ALLOWED_HOSTS` mal puesto.
>
> Ojo: al apuntar las dos webs al mismo proyecto, comparten base de datos. Lo
> que hagas por una lo verás por la otra. Eso es lo que quieres aquí, pero
> conviene saberlo antes de "probar algo" en la de pruebas.

**La vuelta atrás es inmediata mientras el beta siga en su carpeta**: devuélvele
a esta web la configuración anterior y recarga.

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
| Los sindicatos ven el sistema vacío | Se repuntó la dirección antes de importar |

**La vuelta atrás es devolver a la web su configuración anterior y recargar.**
Mientras no borres la base del beta, el camino de vuelta está entero: de ahí que
el paso 8 vaya el último y solo con el paso 5 comprobado.
