# Manual del Usuario: Sistema de Gestión de Carnets

## 1. Introducción

Bienvenido al **Sistema de Gestión de Carnets Sindicales**. Esta guía te ayudará a:

- **Si eres de un sindicato:** Solicitar acceso, subir datos de afiliados, y ver el estado de impresión
- **Si eres imprenta:** Acceder al panel de impresión para consultar lotes listos

El sistema protege los datos personales de los afiliados mediante **encriptación de alta seguridad**. Tómate un momento para entender el flujo.

### Las direcciones que vas a usar

Escribe la dirección del sistema a secas y llegas a la portada, que te ofrece los
tres caminos. No hace falta que memorices ninguna otra:

| Dirección | Para qué |
|-----------|----------|
| `/` | Portada. Entrar, solicitar alta o ir a la ayuda |
| `/ayuda/` | Contacto, manual y los fallos más frecuentes |
| `/ayuda/manual/` | Este mismo manual, para leer en el navegador |
| `/login/` | Entrar con tu cuenta |
| `/alta/` | Solicitar el alta de tu sindicato |
| `/recuperar-password/` | Si olvidaste la contraseña |
| `/subir-datos/` | Subir el Excel de afiliados (requiere sesión) |
| `/notificaciones/` | Estado de tus lotes (requiere sesión) |

La **página de ayuda es pública**: se ve sin cuenta, a propósito, porque quien más
la necesita es justo quien no consigue entrar.

---

## 2. Para Sindicatos

### 2.1 Paso 1: Solicitar Acceso (Registro)

**¿Cuándo hacerlo?** Cuando tu sindicato quiere empezar a usar el sistema por primera vez.

#### Acceder a la página de registro

1. Abre navegador → `https://tu-dominio.es/`
2. En la portada, tarjeta **"Tu sindicato aún no la tiene"** → botón **"Solicitar alta"**
   (o directamente `/alta/`)

#### Completar el formulario

El formulario pide cinco datos (la contraseña, dos veces) y termina con el botón
**Solicitar acceso**:

| Campo | Qué poner | Ejemplo |
|-------|-----------|---------|
| **Nombre de usuario** | Identificador único, sin espacios | `cgt_barcelona` |
| **Correo electrónico** | Obligatorio. Es por donde recuperas la contraseña | `metal@cgtbcn.org` |
| **Sindicato o rama** | Nombre completo, para que el administrador sepa a quién aprueba | `CGT Rama Metal Barcelona` |
| **Persona que solicita** | Tu nombre, para que sepa a quién está aprobando | `Ana Ejemplo` |
| **Contraseña** | Mínimo 12 caracteres; el sistema rechaza las demasiado comunes o solo numéricas | `MiSindicato-2026!` |

> **Pon una dirección de correo que uséis de verdad**, mejor del sindicato que
> personal: es la única vía de recuperar la contraseña sin depender del
> administrador, y si la persona que solicitó el alta se va, la cuenta de correo
> del sindicato sigue ahí. Es obligatoria justamente por eso — dejarla opcional
> significaría que una parte de las cuentas se queda sin recuperación posible, y
> sin saber cuáles hasta que a alguien le hace falta.

#### Qué pasa después

1. El sistema crea tu **cuenta desactivada**: todavía no puedes entrar
2. El administrador ve tu solicitud en su panel, con el nombre de sindicato y la
   persona que declaraste
3. Comprueba que la solicitud es legítima y activa la cuenta
4. ✓ Aprobada → ya puedes iniciar sesión
5. ✗ Con dudas → te contacta por los canales habituales de la organización

**Avísale por tu cuenta de que has solicitado el alta.** El sistema no le manda ningún correo:
tu solicitud le aparece en el panel, pero solo la ve si entra a mirar.

**Tiempo estimado:** 1-2 días laborables

---

### 2.2 Paso 2: Primer Login

**¿Cuándo hacerlo?** Una vez el admin active tu cuenta.

#### Acceder

1. Abre navegador → `https://tu-dominio.es/login/`
2. Escribe tu usuario y tu contraseña, y pulsa **Iniciar sesión**

#### Si todo va bien

El sistema te lleva directamente a donde tienes que trabajar:

- **La primera vez**, al acuerdo legal (apartado 2.3). Hasta firmarlo no puedes subir nada
- **Las siguientes**, a la pantalla de **subir datos**

Arriba, en la barra, tienes siempre **Ayuda**, **Notificaciones** y **Salir**.

#### Si falla

| Mensaje | Causa | Solución |
|---------|-------|----------|
| Usuario o contraseña incorrectos | Datos mal escritos | Revisa mayúsculas, espacios |
| Tu cuenta aún está pendiente de aprobación | Admin no ha activado | Espera 1-2 días, luego reintenta |
| Demasiados intentos fallidos | 5 fallos con el mismo usuario | Espera **5 minutos** y reintenta |

#### Cerrar sesión

Botón **"Salir"**, arriba a la derecha, en cualquier pantalla. Te devuelve a la portada.

**Ciérrala siempre en un ordenador compartido.** La sesión caduca sola a la media
hora de inactividad, pero media hora es tiempo de sobra para que quien se siente
después entre en los datos de afiliación de tu sindicato.

---

### 2.3 Paso 3: Aceptar Términos Legales

**¿Por qué?** El sistema recopila **datos personales de afiliados** (RGPD Art. 9). Debes aceptar la política de protección de datos antes de subirlos.

#### Flujo

1. Tras entrar, ves la pantalla **Acuerdo de Protección de Datos**: el texto
   legal completo y, al final, los botones **Aceptar** y **Rechazar**.

2. Lee el acuerdo (o pídeselo a tu DPO/abogado)
3. Haz clic en **"Aceptar"**
   - Se registra: tu nombre, fecha, hora, IP
   - Automáticamente se redirige a: **Subir Afiliados**

#### ¿Qué pasa si rechazo?

- No puedes subir archivos
- Tu cuenta sigue activa
- Puedes aceptar más tarde

#### ¿Puedo cambiar de opinión?

- **Sí.** Pero no puedes "desaceptar"
- Si necesitas borrar tu consentimiento, contacta al admin

---

### 2.4 Paso 4: Preparar y Subir Archivo de Afiliados

**¿Qué es?** Un archivo Excel (`.xlsx`) con datos de afiliados a imprimir.

#### Descargar la plantilla

**No la fabriques tú.** Hay una plantilla oficial y es el único formato que el
sistema acepta. Se descarga desde **`/subir-datos/`**, con el botón *"Descargar la
plantilla oficial (.xlsx)"* que hay encima del formulario.

| | |
|---|---|
| **Archivo** | `plantilla_afiliacion_oficial.xlsx` (unos 25 KB) |
| **Hoja `ALTAS`** | Donde escribes. Trae la fila de cabecera y nada más |
| **Hoja `Datos`** | Las listas de confederaciones, federaciones y sindicatos |

#### Rellenar la plantilla

Escribe **en la hoja `ALTAS`**, debajo de la cabecera. No cambies, borres ni
renombres ninguna columna: si falta una, el sistema rechaza el archivo entero.

Las cuatro primeras columnas se rellenan **copiando el valor completo de la hoja
`Datos`**, con su código y su nombre. El sistema se queda con el código de
delante; el texto que va detrás del guion es para que tú puedas leerlo.

Así se ve una fila bien rellenada:

| Confederacion | Fed_Local | Fed_Sectorial | Sindicato | Num_Afiliado | Nombre_Apellidos | Lengua | Estado |
|---|---|---|---|---|---|---|---|
| `01-Confederación Andalucía` | `01080-fed. local Vitoria` | `00 - OFICIOS VARIOS` | `001 - S.O.V. Almeria` | `000001` | Juan Pérez González | `A` | `ALTA` |
| `01-Confederación Andalucía` | `01080-fed. local Vitoria` | `03 - ENSEÑANZA` | `007 - Enseñanza Granada` | `000002` | María García López | `A` | `ALTA` |
| `03-Confederación Asturias` | `03800-fed. local Alcoy` | `02 - BANCA, BOLSA, AHORRO` | `005 - OO.VV. Xerez` | `000003` | Carlos López Ruiz | `C` | `BAJA` |

**Detalles de cada columna:**

| Columna | Qué escribir | Qué guarda el sistema |
|---------|--------------|----------------------|
| **Confederacion** | El valor entero de la hoja `Datos` | Los **2 dígitos** de delante del guion |
| **Fed_Local** | El valor entero de la hoja `Datos` | Los **5 dígitos** de delante del guion |
| **Fed_Sectorial** | El valor entero de la hoja `Datos` | Los **2 dígitos** de delante del guion |
| **Sindicato** | El valor entero de la hoja `Datos` | Los **3 dígitos** de delante del guion |
| **Num_Afiliado** | El número, con o sin ceros delante | **6 dígitos**: rellena con ceros por la izquierda (`42` → `000042`) |
| **Nombre_Apellidos** | Nombre completo, hasta 255 caracteres | Tal cual, **cifrado** |
| **Lengua** | `A` o `C`, exactamente | `A`=Castellano, `C`=Catalán |
| **Estado** | `ALTA` o `BAJA`, exactamente | Situación del afiliado |

> **`Lengua` y `Estado` van en MAYÚSCULAS, sin excepción.** Se comparan letra a
> letra y **distinguen mayúsculas**: `ALTA` vale; `Alta` y `alta` los rechaza
> (comprobado). Los espacios sobrantes delante o detrás sí se quitan solos.
> Tampoco valen `Castellano`, `ES` ni `PENDIENTE`. Si una fila trae otra cosa, da
> error, y con una sola fila mala se cae el archivo entero.

#### Validaciones que hace el sistema

Cuando subes el archivo, el sistema revisa:

✓ **Formato del archivo:** .xlsx (no .xls, .csv, .txt)
✓ **Tamaño:** ≤ 5 MB
✓ **Filas:** ≤ 10.000
✓ **Columnas:** Todas presentes
✓ **Formato de datos:**
  - Confederacion: exactamente 2 dígitos
  - Fed_Local: exactamente 5 dígitos
  - Num_Afiliado: exactamente 6 dígitos
  - Lengua: 'A' o 'C'
  - Estado: 'ALTA' o 'BAJA'

#### Si hay error

Si una o más filas tienen errores, el sistema:
- **Rechaza el lote completo** (no guarda NADA)
- Muestra primeros 10 errores
- Te pide que corrijas y vuelvas a subirlo

**Ejemplo de error:**
```
❌ No se ha guardado ningún afiliado: 3 fila(s) tienen errores de formato

Detalle:
  Fila 3: columna Num_Afiliado: valor "12345" (esperado 6 dígitos)
  Fila 7: columna Lengua: valor "E" (esperado 'A' o 'C')
  Fila 12: columna Estado: valor "PENDIENTE" (esperado 'ALTA' o 'BAJA')
```

#### Subir el archivo

1. Accede a `/subir-datos/`
2. Botón **"Elegir archivo"** → selecciona tu .xlsx
3. Botón **"Procesar Archivo"**
4. Espera (puede tardar 10-30 segundos según cantidad de filas)

#### Confirmación

✓ Si todo OK:
```
✓ ¡Éxito! Se han procesado y guardado 500 afiliados correctamente.

Siguiente paso: El administrador revisará los datos y los marcará
como listos para imprenta. Recibirás una notificación cuando esté hecho.
```

✗ Si hay error:
```
❌ No se ha guardado ningún afiliado: ...
[Corrige el archivo y vuelve a subir]
```

---

### 2.5 Paso 5: Ver Notificaciones

Mientras el admin procesa tu lote, puedes ver el progreso.

#### Acceder

1. Login → `/notificaciones/`
2. Verás historial de eventos:

Un historial en orden, de lo más reciente a lo más antiguo. Las que no has
leído aparecen destacadas en rojo:

| Fecha | Aviso |
|---|---|
| 21/08/2026 14:30 | Tu lote de 500 afiliados ha sido marcado como IMPRESO. Está listo para enviar a imprenta |
| 20/08/2026 10:15 | Se han recibido 500 afiliados de tu envío del 15/08 |
| 15/08/2026 09:45 | Subida correcta: 500 afiliados procesados |

#### Marcar como leídas

- Botón **"Marcar todas como leídas"** al final

---

### 2.6 Recuperar la Contraseña

#### Olvidé la contraseña

**Puedes reponerla tú, sin esperar a nadie.**

1. En `/login/`, enlace **"¿Has olvidado tu contraseña?"** (o ve a `/recuperar-password/`)
2. Escribe el correo con el que se dio de alta la cuenta
3. Recibirás un mensaje con un **enlace de un solo uso**
4. Ábrelo y elige una contraseña nueva

**Si no llega el correo**, en este orden: mira la carpeta de spam; comprueba que la
dirección es la que declarasteis en el alta; y si sigue sin llegar, escribe a soporte
(apartado 6).

> **La pantalla dice "si existe una cuenta con ese correo, te hemos enviado un
> mensaje" tanto si existe como si no.** No es un fallo ni una evasiva: si
> confirmara cuáles existen, cualquiera podría ir probando direcciones para
> averiguar qué sindicatos usan el sistema.

**El enlace caduca a las dos horas** y solo sirve una vez. Si tardas, pide otro.

**Hay un límite de peticiones**: cinco cada cuarto de hora desde la misma conexión a
internet. Si estáis varias personas en el mismo local y probáis a la vez, os puede
salir un aviso de "demasiadas peticiones". Esperad quince minutos.

#### Quiero cambiarla, pero la recuerdo

Usa el mismo circuito de arriba: pide el correo de recuperación y elige una nueva. La
aplicación no tiene todavía una pantalla aparte de "cambiar contraseña" para las
cuentas de sindicato.

#### Si prefieres que lo haga el administrador

Sigue siendo posible (por ejemplo, si perdisteis también el acceso al buzón de
correo). Entonces:

- Que te la comunique **por un canal distinto** al que usaste para pedirla
- **No la envíes ni la pidas por correo sin cifrar.** Una contraseña en un buzón queda
  ahí indefinidamente y abre el acceso a datos de afiliación sindical

---

## 3. Para Imprenta

### 3.1 Acceso al Panel

**¿Cuándo?** Cuando el administrador te haya creado una cuenta en el grupo "Imprenta".

#### Login

1. Abre navegador → `https://tu-dominio.es/login/`
2. Usuario y contraseña (que te proporciona admin)
3. Automáticamente ves: **Panel de Impresión**

#### Qué ves

Una tabla con tres columnas, y solo tres:

| Sindicato | Nº Afiliado | Fecha de envío |
|---|---|---|
| 003 | 000101 | 21/08/26 14:30 |
| 003 | 000102 | 21/08/26 14:30 |
| 007 | 000201 | 20/08/26 10:15 |
| 007 | 000202 | 20/08/26 10:15 |
| 003 | 000103 | 15/08/26 09:45 |

#### ¿Qué ves y qué NO ves?

✓ **Ves:**
- Código de sindicato
- **Número de afiliado, legible** — es el dato que necesitas para imprimir
- Fecha en que se envió a imprenta

✗ **NO ves:**
- **Nombres y apellidos** de los afiliados
- Notas históricas de reemisión
- Lotes que el administrador todavía no ha enviado
- El historial de cambios

#### ¿Por qué el número sí y el nombre no?

El número lo necesitas para tu trabajo; el nombre no. Esa es toda la lógica.

El sistema no te "oculta" el nombre poniéndolo en gris: **ni siquiera lo lee de la base de
datos** al construir esta pantalla. La consulta pide tres columnas y el nombre no está entre
ellas, así que no hay forma de que aparezca por un descuido de programación.

Los datos van cifrados **en el disco** del servidor, de modo que quien robe una copia de la
base de datos no pueda leerlos. Cuando la aplicación los muestra a quien tiene permiso, los
descifra. Son dos cosas distintas: cifrado en reposo ≠ oculto en pantalla.

#### ¿Y si me roban la contraseña de imprenta?

El daño está acotado por diseño:

- Quien entre ve números de afiliado y fechas, **nunca nombres**
- No puede subir ni modificar nada: la cuenta es de solo lectura
- No puede entrar al `/admin/`
- Solo ve los lotes ya enviados, no lo que aún está pendiente

Aun así, avisa al administrador de inmediato: cada consulta a este panel queda registrada, y
puede comprobar si hubo accesos que no fueran tuyos.

### 3.2 Limitaciones (Por Diseño)

| Acción | ¿Puedes? | Razón |
|--------|----------|-------|
| Ver números de afiliado | ✓ Sí | Es lo que necesitas para imprimir |
| Ver nombres | ✗ No | La pantalla no los consulta siquiera |
| Descargar el lote | ✗ No | El panel solo muestra la tabla en pantalla |
| Subir afiliados | ✗ No | Solo los sindicatos suben datos |
| Editar afiliados | ✗ No | Cuenta de solo lectura |
| Acceder a `/admin/` | ✗ No | Sin permisos de staff |
| Ver la auditoría | ✗ No | Solo el administrador |

**Si necesitas algo que no puedes hacer, contacta al administrador.**

---

## 4. Guía de Seguridad Para Todos

### 4.1 Contraseña Segura

**Tu contraseña es la llave a datos sensibles.**

✓ Usa:
- ≥ 12 caracteres (cuanto más larga, mejor)
- Mayúsculas Y minúsculas
- Números Y símbolos
- Algo que recuerdes, pero no sea predecible

✗ Evita:
- Tu nombre o cumpleaños
- "Sindicato2026" (predecible)
- Contraseña de otro servicio
- Escritas en papeletas

**Ejemplo seguro:** `MiGrupo#Barcelona+2026!`

### 4.2 Nunca Compartas Credenciales

| Nunca hagas | Razón |
|------------|--------|
| Email tu contraseña al admin | Admin ya tiene acceso; no la necesita |
| Enviar contraseña por chat/SMS | No es seguro; pueden interceptarla |
| Anotar en post-its en tu escritorio | Alguien la puede ver |
| Usar misma contraseña en 5 sitios | Si 1 falla, se cae el castillo |

### 4.3 Si Sospechas que Alguien Más Accedió a Tu Cuenta

1. **Cambia la contraseña inmediatamente** tú mismo, por `/recuperar-password/`
   (apartado 2.6). No esperes a que conteste nadie
2. **Contacta al admin:**
   ```
   "Mi cuenta [username] puede haber sido comprometida.
    Cambié contraseña pero pido que revises auditoría
    por accesos sospechosos."
   ```
3. **Admin investigará** y desactivará cuenta si es necesario

### 4.4 Datos Personales en el Sistema

**¿Cómo se protegen?**
- ✓ Encriptación AES-256 (nivel banco)
- ✓ Historial de cambios auditado (quién vio, cuándo)
- ✓ Acceso restringido por rol
- ✓ Sesiones seguras (HTTPS)

**¿Cuánto tiempo se guardan?**

| Qué | Cuánto | Desde cuándo cuenta |
|-----|--------|---------------------|
| Datos del afiliado | **3 años** | Desde que pasa a **BAJA**, no desde que se dio de alta |
| Registro de auditoría de accesos | 2 años | Desde cada acceso |

Pasados los tres años, un proceso automático **anonimiza** la ficha: desaparecen el
nombre y el número de afiliado, y con ellos el vínculo entre una persona y su
afiliación sindical. Se anonimiza también todo el historial de versiones de esa
ficha, que es la parte que de verdad importa: borrar solo la ficha viva dejaría el
nombre anterior guardado en el historial.

Queda el recuento de carnets emitidos, que ya no identifica a nadie.

> **Mientras el afiliado siga de ALTA no hay plazo que corra**, porque los datos
> siguen haciendo falta para la finalidad que los legitima. El reloj empieza el día
> que se marca la baja.

---

## 5. Preguntas Frecuentes

### P: ¿Cuánto tarda en activarse mi cuenta?

**R:** 1-2 días laborales. El admin valida que tu sindicato sea legítimo.

### P: ¿Puedo cambiar mi nombre de usuario?

**R:** No. Contacta al admin si hay error; podría crear uno nuevo.

### P: ¿Se pueden subir archivos .CSV o .XLS?

**R:** Solo .XLSX. Convierte en Excel 2007+.

### P: ¿Cuántos afiliados puedo subir de una vez?

**R:** Máximo 10.000 por archivo. Si tienes más, divide en 2-3 archivos.

### P: ¿Qué pasa si subo datos incorrectos?

**R:** El admin lo verá y notificará. Si es grave, se contacta al sindicato. Puedes subir de nuevo con correcciones.

### P: ¿Dónde están nuestros datos?

**R:** En servidor seguro, encriptados. Acceso solo con credenciales.

### P: ¿Puedo acceder desde mi teléfono móvil?

**R:** Sí, pero no recomendado (pantalla pequeña, menos seguro). Mejor desde PC/Mac con HTTPS.

### P: ¿Necesito una aplicación especial?

**R:** No. Solo navegador web (Chrome, Firefox, Safari, Edge). Nada que instalar.

### P: ¿Qué pasa si pierdo acceso?

**R:** Si es la contraseña, repónla tú desde `/recuperar-password/` (apartado 2.6).
Si perdiste también el buzón de correo del alta, contacta con el administrador.

### P: ¿Se puede exportar datos de afiliados?

**R:** Ni los sindicatos ni la imprenta pueden exportar. **Solo el administrador**
genera el archivo para la imprenta, desde el panel de administración, y esa
exportación queda registrada en la auditoría. La imprenta consulta su panel en
pantalla, sin botón de descarga.

### P: ¿Dónde consigo la plantilla oficial?

**R:** En `/subir-datos/`, encima del formulario, o en la página de ayuda
(`/ayuda/`). Es un `.xlsx` de unos 25 KB. No fabriques la tuya: el sistema comprueba
que estén las ocho columnas con su nombre exacto.

### P: ¿Cómo cierro la sesión?

**R:** Botón **"Salir"**, arriba a la derecha. Hazlo siempre en ordenadores
compartidos.

### P: ¿Qué seguridad hay contra hackers?

**R:**
- **Cifrado en reposo:** nombres y números se guardan cifrados (AES-256-GCM) en el disco del
  servidor. Quien robe una copia de la base de datos no puede leerlos.
- **HTTPS:** la comunicación entre tu navegador y el servidor va cifrada.
- **Contraseñas con hash:** ni el administrador puede ver la tuya.
- **Limitador de intentos:** 5 fallos bloquean el acceso 5 minutos, lo que hace inviable
  probar contraseñas a ciegas. Vale igual para tu pantalla de acceso y para la del
  administrador.
- **Segundo factor en el administrador:** la cuenta que puede ver los nombres necesita además
  un código de 6 dígitos que cambia cada 30 segundos. Robar su contraseña ya no basta.
- **Auditoría:** cada consulta y cada exportación de datos queda registrada.
- **Content-Security-Policy:** el navegador se niega a ejecutar cualquier script que no venga
  del propio sitio.

> Ojo con un matiz que se confunde a menudo: esto **no** es cifrado extremo a extremo. El
> servidor sí puede leer los datos —necesita hacerlo para imprimir los carnets—. Lo que
> protege el cifrado es el disco y las copias de seguridad, no al propio servidor.

### P: ¿Qué hago si olvido contraseña?

**R:** Repónla tú desde `/recuperar-password/`. Te llega un enlace de un solo uso al
correo del alta (ver 2.6).

### P: ¿Puedo eliminar mis datos?

**R:** Sí. Si eres una persona afiliada, **dirígete a tu sindicato**, no a esta web:
tu sindicato es el responsable de tus datos y quien tramita el derecho de supresión
(RGPD Art. 17). El plazo legal es de 30 días. Con independencia de que lo pidas, los
datos se anonimizan solos a los 3 años de la baja (ver 4.4).

---

## 6. Contactos de Soporte

**Todo esto está también en la web, en `/ayuda/`**, que se ve sin necesidad de tener
cuenta.

| Vía | Dato |
|-----|------|
| Correo | **soporte-carnets@cgt.org.es** |
| Teléfono | **918 055 047** (horario de oficina) |

**Cuando escribas, cuenta qué estabas haciendo y qué te dijo la pantalla**, con el
mensaje de error tal cual salió. Si el fallo fue al subir un archivo, di el nombre
del archivo.

> **No adjuntes nunca el Excel de afiliados.** Lleva nombres y números de personas
> afiliadas, y el correo electrónico no va cifrado: mandarlo convierte una consulta
> de soporte en una filtración de datos de categoría especial.

Antes de escribir, mira el apartado *"Antes de escribirnos"* de `/ayuda/`: recoge las
cuatro causas por las que el sistema rechaza un archivo, que son casi todas.

**Si tienes indicios de una brecha de seguridad** —alguien ha entrado en vuestra
cuenta, os han robado el portátil con la sesión abierta— avisad de inmediato y
decidlo en el asunto. El plazo legal para notificar una brecha a la autoridad es de
72 horas y empieza a correr desde que la organización lo sabe.

---

## 7. Checklist: Primer Uso

- [ ] Solicité el alta en `/alta/` (con correo del sindicato y persona de contacto)
- [ ] Avisé al administrador de que la había solicitado
- [ ] Esperé aprobación (1-2 días)
- [ ] Entré con mi usuario y contraseña en `/login/`
- [ ] Leí y acepté el acuerdo legal
- [ ] Descargué `plantilla_afiliacion_oficial.xlsx` desde `/subir-datos/`
- [ ] Rellené la hoja **ALTAS**, copiando los valores de la hoja **Datos**
- [ ] Subí el archivo (sin errores)
- [ ] Recibí confirmación de "Éxito"
- [ ] La notificación muestra el estado "IMPRESO"
- [ ] **Cerré la sesión con "Salir"**

✓ **¡Listo! Tu primer lote está en camino a imprenta.**

---

**Última revisión:** 2026-08-27
**Versión:** 2.0

Este manual se lee también en el navegador, en **`/ayuda/manual/`**, enlazado desde
la página de ayuda. Es el mismo texto: la web lo renderiza desde este archivo.

**Qué cambió en la 2.0.** El alta pide ahora correo y persona de contacto, y con el
correo llegó la **recuperación de contraseña por tu cuenta** (2.6), que antes no
existía: este manual decía que había que pedírsela al administrador. Hay **portada**
y **página de ayuda** públicas, y botón de **Salir**. La **plantilla oficial se
descarga** desde la propia web, y la documentación de sus columnas estaba mal: los
cuatro códigos se copian enteros desde la hoja `Datos` (`01-Confederación Andalucía`),
no como dos dígitos sueltos. Se corrigieron las direcciones `/registro/` → `/alta/` y
`/subir/` → `/subir-datos/`, el plazo de conservación (3 años **desde la baja**), y la
respuesta sobre exportación, que se contradecía con el apartado 3.2.
