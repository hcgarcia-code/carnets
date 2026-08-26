# Migrar las cuentas y los afiliados del beta

El despliegue beta (`carnetscgt.eu.pythonanywhere.com`) tiene sindicatos que ya
se dieron de alta, firmaron el acuerdo y subieron sus listas. El objetivo de
esta migración es que **no tengan que repetir nada**: misma contraseña, mismo
acuerdo ya firmado, mismos afiliados.

Si alguna de esas tres cosas se pierde, hay que pedirles que rehagan el
proceso, y en la práctica eso significa perder a una parte de ellos por el
camino.

---

## Antes de empezar: lo que hay que saber

**El beta y este sistema son ramas divergentes, no versiones sucesivas.**

| | Beta | Este sistema |
|---|---|---|
| Correo en el alta | sí | sí (añadido para esto) |
| Persona de contacto | sí | sí (añadido para esto) |
| Recuperar contraseña | sí | sí (añadido para esto) |
| Portada `/` | sí | **no** |
| Ruta del alta | `/registro/` | `/alta/` |
| Página de contacto | sí | **no** |
| Cifrado en reposo | **no** | sí |
| Segundo factor en el admin | **no** | sí |
| Registro de auditoría | **no** | sí |

Las tres primeras filas se recuperaron precisamente para poder hacer esta
migración sin dejar a nadie peor que antes. Las dos que siguen (portada y
página de contacto) **no existen aquí**: si los sindicatos tienen guardado el
enlace de la portada, hay que avisarles del nuevo.

La ruta de recuperación de contraseña sí se mantuvo idéntica
(`/recuperar-password/`) para no romper enlaces guardados.

---

## Paso 1 — Sacar el volcado del beta

En una consola bash de PythonAnywhere, dentro del directorio del proyecto beta:

```bash
python manage.py dumpdata auth.User gestion.PerfilSindicato gestion.Afiliado --indent 2 > beta.json
```

Descarga `beta.json` desde el panel de archivos de PythonAnywhere.

> ⚠️ **Ese archivo contiene datos de afiliación sindical en claro** — categoría
> especial del Art. 9 del RGPD. El beta es anterior al cifrado en reposo, así
> que sale todo legible. No lo envíes por correo ordinario, no lo dejes en
> Descargas y **bórralo en cuanto termine la importación**. Es exactamente el
> tipo de archivo suelto que la EIPD identifica como riesgo alto.

---

## Paso 2 — Probar en seco

```bash
python sistema_carnets/manage.py importar_desde_beta beta.json --dry-run
```

No escribe nada. Dice cuántas cuentas, perfiles y afiliados entrarían, y
cuántas cuentas de administrador se omitirían.

Compara esas cifras con lo que esperas. Si no cuadran, el volcado está
incompleto o se cortó al copiarlo.

---

## Paso 3 — Importar

```bash
python sistema_carnets/manage.py importar_desde_beta beta.json
```

Todo ocurre dentro de una transacción: o entra completo, o no entra nada.

**Se puede ejecutar varias veces.** No duplica cuentas ni afiliados, y no pisa
la contraseña de una cuenta que ya exista aquí. Si la primera pasada se corta o
descarta filas, corrige y repite.

---

## Paso 4 — Revisar los avisos

El comando informa de tres cosas que hay que mirar, no ignorar:

**Cuentas de administrador omitidas.** No se importan a propósito: el admin de
este sistema exige segundo factor, que un superusuario del beta no tiene
configurado. Importarla crearía una cuenta con todos los privilegios que no
puede entrar, y que nadie recordaría revisar. Créala a mano:

```bash
python sistema_carnets/manage.py createsuperuser
python sistema_carnets/manage.py activar_2fa <usuario>
```

**Afiliados descartados por validación.** Datos que no cumplen el formato
(números de afiliado que no son seis dígitos, códigos con letras). El comando
da la referencia que tenían en el volcado, nunca el dato personal. Hay que
corregirlos en el origen y repetir, o darlos de alta a mano.

**Afiliados sin sindicato reconocible.** Su cuenta no venía en el volcado. **No
se importan**: asignarlos a otro sindicato rompería el aislamiento entre
sindicatos, que es una de las garantías del sistema. Suele significar que el
`dumpdata` no incluyó `auth.User`.

---

## Paso 5 — Comprobar

```bash
python sistema_carnets/manage.py shell
```

```python
from django.contrib.auth.models import User
from gestion.models import Afiliado, PerfilSindicato

User.objects.filter(is_superuser=False).count()      # cuentas de sindicato
PerfilSindicato.objects.filter(acuerdo_aceptado=True).count()   # no repiten firma
Afiliado.objects.count()

# Que los datos entraron cifrados:
from django.db import connection
with connection.cursor() as cur:
    cur.execute('SELECT "nombre_apellidos" FROM "gestion_afiliado" LIMIT 1')
    print(cur.fetchone()[0])       # debe empezar por  v1$
```

Si eso último no empieza por `v1$`, **algo ha entrado sin cifrar** y hay que
parar y revisarlo antes de seguir.

---

## Paso 6 — Avisar a los sindicatos

Un correo corto basta. Conviene que diga:

- La dirección nueva del sistema.
- Que **su usuario y su contraseña son los mismos** y no tienen que hacer nada.
- Que sus afiliados ya cargados están ahí.
- Que si olvidan la contraseña, la recuperan solos desde el enlace del acceso.
- Que la portada y la página de contacto del beta ya no existen.

---

## Paso 7 — Borrar el volcado

```bash
rm beta.json
```

Y también la copia descargada en el equipo local, y la papelera. Mientras exista,
hay un archivo con el fichero de afiliación en claro fuera de todo control
técnico.

Borra igualmente el `beta.json` que quedó en PythonAnywhere.

---

## Qué hacer con el beta después

Mientras siga en pie, sigue habiendo una copia completa de los datos **sin
cifrar, sin segundo factor y sin auditoría**. Una vez comprobada la migración,
lo coherente con la EIPD es apagarlo y eliminar su base de datos. Mantener los
dos sistemas en marcha duplica la superficie expuesta sin ninguna contrapartida.
