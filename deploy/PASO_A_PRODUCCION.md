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
la que hay que sustituir. Eso cambia el orden de todo lo que viene detrás,
porque durante un rato la misma dirección tiene que dejar de servir una cosa y
empezar a servir otra.

> Si lo que quieres es otra dirección distinta (`carnets.eu.pythonanywhere.com`,
> por ejemplo), eso es **otra cuenta de PythonAnywhere**, no una opción dentro
> de la actual. Y entonces esta guía sirve igual, pero el beta se queda donde
> está y hay que apagarlo aparte (último apartado).

---

## El orden importa

El instinto es "monto lo nuevo y luego migro los datos". Aquí es al revés,
porque **el beta es la única copia de los datos de los sindicatos** y en cuanto
lo sustituyas dejarás de poder sacar el volcado.

```
1. Volcado del beta          ← mientras el beta sigue en pie
2. Congelar el beta          ← que nadie suba nada más
3. Preparar el 2.0
4. Importar el volcado
5. Comprobar
6. Cambiar la dirección
7. Avisar a los sindicatos
8. Borrar el volcado y apagar el beta
```

---

## Paso 1 — Sacar el volcado del beta

**Antes de tocar nada.** El procedimiento completo, con lo que trae de sucio el
volcado real, está en `migrar_desde_beta.md`. En corto:

```bash
# Consola Bash, con el entorno del BETA
PYTHONPATH=/home/carnetscgt python manage.py dumpdata \
    auth.User gestion.PerfilSindicato gestion.Afiliado --indent 2 -o beta.json
```

**Ese archivo es el fichero de afiliación en claro.** No lo mandes por correo,
no lo dejes en Descargas y bórralo en cuanto termines (paso 8).

Descárgalo también a tu equipo: es la única copia de seguridad que vas a tener
si algo sale mal a mitad.

---

## Paso 2 — Congelar el beta

Desde que sacas el volcado hasta que el 2.0 está en pie, cualquier cosa que un
sindicato suba al beta **se pierde**: no está en tu volcado y el beta va a
desaparecer.

Lo más simple y reversible es desactivar las cuentas de sindicato en el admin
del beta (`is_active = False`). Entran, ven que no pueden, y llaman. Es feo,
pero es mucho mejor que perder una carga sin que nadie lo note.

**Hazlo en una franja de poco uso** y ten el paso 7 (el aviso) preparado antes.

---

## Paso 3 — Preparar el 2.0

Si ya tienes la web de pruebas montada, esto ya está hecho: es la misma
aplicación. Comprueba que el `.env` del servidor tiene, además de lo de
`PUESTA_EN_MARCHA.md`, **las tres variables de correo**:

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

## Paso 6 — Cambiar la dirección

En la pestaña **Web** de PythonAnywhere:

1. **Apaga primero el beta.** Con la cuenta de pago puedes tener varias webs,
   pero solo una puede responder en `carnetscgt.eu.pythonanywhere.com`.
   Elimina esa web (o cámbiale el dominio) antes de asignárselo al 2.0.
2. Al 2.0, apúntale el dominio principal.
3. Repasa que sigan bien:
   - **Source code** y **Working directory**
   - **WSGI configuration file** (con `PYTHONPATH=/home/carnetscgt`)
   - **Virtualenv**: `entorno_sindicato`
   - **Static files**: `/static/` → `/home/carnetscgt/carnets/sistema_carnets/staticfiles`
4. `ALLOWED_HOSTS` del `.env` tiene que incluir la dirección nueva. **Si no, la
   web responde 400 a todo** y parece que se ha roto el despliegue.
5. **Reload.**

```bash
python sistema_carnets/manage.py collectstatic --noinput
```

> Deja la web de pruebas en pie unos días, en su propia dirección. Si aparece
> algo, tienes dónde reproducirlo sin tocar producción.

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

**Elimina la base de datos del beta.** Mientras siga en pie hay una copia
completa de los datos sin cifrar, sin segundo factor y sin auditoría. Una vez
comprobada la migración, mantener los dos sistemas duplica la superficie
expuesta sin ninguna contrapartida — y eso es exactamente lo que la EIPD dice
que no se haga.

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
| Un sindicato no puede entrar | Se quedó `is_active=False` del paso 2 |

La vuelta atrás mientras el beta siga en pie es devolverle el dominio. Después
de borrar su base de datos ya no hay vuelta atrás: de ahí que el paso 8 vaya el
último y solo con el paso 5 comprobado.
