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

## Plan acordado: las cuentas por comando, los afiliados a mano

El volcado real trae **56 cuentas, 39 perfiles y 3918 afiliados**, y esos
afiliados vienen sucios:

| Problema | Filas | Qué es |
|---|---|---|
| `estado` corrupto | 407 (10,4%) | Trae `"202` o `"201` —un código de federación— en vez de ALTA/BAJA |
| `lengua` inválida | 344 (8,8%) | 18 letras que no existen; el modelo solo admite `A` y `C`. Parece una celda de Excel arrastrada que reprodujo el alfabeto |

**El comando no los corrige.** Rechaza esas filas y lo dice. Inventar un estado
o una lengua significaría emitir carnets en el idioma equivocado o dar de alta
a quien estaba de baja, y sin que nadie se entere.

Por eso el reparto es:

- **Las cuentas, con este comando.** Es lo que no se puede rehacer a mano: 54
  contraseñas que nadie debe tener que cambiar y 39 acuerdos ya firmados.
- **Los afiliados, por el Excel de siempre.** Se descarga la tabla, se limpia
  en Excel, se manda a imprimir, y se sube por `/subir-datos/` como cualquier
  otra carga. La ruta normal ya valida fila a fila y avisa de lo que no cuadra.

El comando **sí sabe** importar afiliados si algún día hace falta; simplemente
no es la vía elegida ahora.

---

## Paso 1 — Sacar el volcado del beta

En una consola bash de PythonAnywhere, dentro del directorio del proyecto beta:

```bash
workon entorno_sindicato
PYTHONPATH=/home/carnetscgt python manage.py dumpdata auth.User gestion.PerfilSindicato gestion.Afiliado --indent 2 -o beta.json
```

Dos cosas concretas de ese servidor, ambas necesarias:

- **`workon entorno_sindicato`**: la consola bash usa el Python del sistema, donde no está `django-simple-history`. La web sí corre en ese virtualenv.
- **`PYTHONPATH=/home/carnetscgt`**: el proyecto tiene estructura plana —`settings.py` junto a `manage.py`, y el propio directorio es el paquete `sistema_carnets`—, así que su padre tiene que estar en el path. El WSGI de PythonAnywhere lo añade; bash no.

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
