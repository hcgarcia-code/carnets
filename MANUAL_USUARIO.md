# Manual del Usuario: Sistema de Gestión de Carnets

## 1. Introducción

Bienvenido al **Sistema de Gestión de Carnets Sindicales**. Esta guía te ayudará a:

- **Si eres de un sindicato:** Solicitar acceso, subir datos de afiliados, y ver el estado de impresión
- **Si eres imprenta:** Acceder al panel de impresión para consultar lotes listos

El sistema protege los datos personales de los afiliados mediante **encriptación de alta seguridad**. Tómate un momento para entender el flujo.

---

## 2. Para Sindicatos

### 2.1 Paso 1: Solicitar Acceso (Registro)

**¿Cuándo hacerlo?** Cuando tu sindicato quiere empezar a usar el sistema por primera vez.

#### Acceder a la página de registro

1. Abre navegador → `https://tu-dominio.es/`
2. Verás un botón **"Solicitar alta"** o directamente `/registro/`

#### Completar el formulario

```
┌────────────────────────────────────────────┐
│      Solicitud de Alta de Sindicato        │
├────────────────────────────────────────────┤
│ Nombre de usuario: [cgt_rama_metal]        │
│ Sindicato o rama:  [CGT Rama Metal BCN]    │
│ Contraseña:        [••••••••••]            │
│ Repetir contraseña:[••••••••••]            │
│                                            │
│         [ Solicitar acceso ]               │
└────────────────────────────────────────────┘
```

**Detalles importantes:**

| Campo | Qué poner | Ejemplo |
|-------|-----------|---------|
| **Nombre de usuario** | Identificador único, sin espacios | `cgt_barcelona` |
| **Sindicato o rama** | Nombre completo, para que el administrador sepa a quién aprueba | `CGT Rama Metal Barcelona` |
| **Contraseña** | Mínimo 8 caracteres; el sistema rechaza las demasiado comunes o solo numéricas | `MiSindicato-2026!` |

> **El formulario no pide correo electrónico.** No es un olvido: el sistema no envía ningún
> aviso automático, así que un correo que nadie va a usar sería un dato personal guardado sin
> motivo. La consecuencia práctica está en el apartado 2.6: **si pierdes la contraseña, hay que
> pedírsela al administrador**, no hay recuperación por correo.

#### Qué pasa después

1. El sistema crea tu **cuenta desactivada**: todavía no puedes entrar
2. El administrador ve tu solicitud en su panel, con el nombre de sindicato que declaraste
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
2. Completa:
   ```
   Usuario: [tu username]
   Contraseña: [tu contraseña]
   [ Iniciar sesión ]
   ```

#### Si todo va bien

- Verás **panel de inicio** con 3 secciones:
  1. Acuerdo Legal (pendiente)
  2. Subir Afiliados
  3. Notificaciones

#### Si falla

| Mensajón | Causa | Solución |
|----------|-------|----------|
| Usuario o contraseña incorrectos | Datos mal escritos | Revisa mayúsculas, espacios |
| Tu cuenta aún está pendiente de aprobación | Admin no ha activado | Espera 1-2 días, luego reintenta |
| Demasiados intentos fallidos | 5 fallos con el mismo usuario | Espera **5 minutos** y reintenta |

---

### 2.3 Paso 3: Aceptar Términos Legales

**¿Por qué?** El sistema recopila **datos personales de afiliados** (RGPD Art. 9). Debes aceptar la política de protección de datos antes de subirlos.

#### Flujo

1. Tras loguear, ves página:
   ```
   ┌─────────────────────────────────────┐
   │      Acuerdo de Protección Datos    │
   ├─────────────────────────────────────┤
   │ [Texto legal: protección datos,     │
   │  reglamento RGPD, retención, ...]   │
   │                                     │
   │      [ Aceptar ]  [ Rechazar ]      │
   └─────────────────────────────────────┘
   ```

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

#### Descargar plantilla

El sistema proporciona una **plantilla oficial** en: `/recursos/afiliados_plantilla.xlsx`

**O descargarlo aquí:**

```
Nombre archivo: afiliados_plantilla.xlsx
Peso: ~10 KB
Columnas: Confederacion | Fed_Local | Fed_Sectorial | Sindicato | Num_Afiliado | Nombre_Apellidos | Lengua | Estado
```

#### Rellenar la plantilla

**Importante:** Respetar exactamente el formato. El sistema es estricto.

```
┌──────────┬──────────┬──────────┬──────────┬──────────┬─────────────────────┬────────┬──────────┐
│Confedera-│ Fed_     │ Fed_     │Sindicato │Num_      │Nombre_Apellidos     │Lengua  │ Estado   │
│cion      │Local     │Sectorial │          │Afiliado  │                     │        │          │
├──────────┼──────────┼──────────┼──────────┼──────────┼─────────────────────┼────────┼──────────┤
│    28    │  28001   │    01    │   100    │ 000001   │Juan Pérez González  │  A     │  ALTA    │
│    28    │  28001   │    01    │   100    │ 000002   │María García López   │  A     │  ALTA    │
│    28    │  28002   │    01    │   200    │ 000001   │Carlos López Ruiz    │  C     │  BAJA    │
└──────────┴──────────┴──────────┴──────────┴──────────┴─────────────────────┴────────┴──────────┘
```

**Detalles de cada columna:**

| Columna | Formato | Ejemplo | Notas |
|---------|---------|---------|-------|
| **Confederacion** | 2 dígitos | 28 | Código CCAA (28=Madrid) |
| **Fed_Local** | 5 dígitos | 28001 | Código local provincial |
| **Fed_Sectorial** | 2 dígitos | 01 | Sector (01=Sector A) |
| **Sindicato** | 3 dígitos | 100 | Código sindicato local |
| **Num_Afiliado** | 6 dígitos | 000001 | Número secuencial |
| **Nombre_Apellidos** | Texto ≤255 car. | Juan Pérez | Nombre completo |
| **Lengua** | A o C | A | A=Castellano, C=Catalán |
| **Estado** | ALTA o BAJA | ALTA | Situación del afiliado |

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

1. Accede a `/subir/`
2. Botón **"Elegir archivo"** → selecciona tu .xlsx
3. Botón **"Subir y procesar"**
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

```
┌─────────────────────────────────────────────────┐
│        NOTIFICACIONES DE TU SINDICATO           │
├─────────────────────────────────────────────────┤
│ 21/08/2026 14:30                               │
│ "Tu lote de 500 afiliados ha sido marcado      │
│  como IMPRESO. Está listo para enviar a        │
│  imprenta."                                     │
│                                                 │
│ 20/08/2026 10:15                               │
│ "Se han recibido 500 afiliados de tu envío    │
│  del 15/08. Admin está validando..."           │
│                                                 │
│ 15/08/2026 09:45                               │
│ "Subida exitosa: 500 afiliados procesados"     │
└─────────────────────────────────────────────────┘
```

#### Marcar como leídas

- Botón **"Marcar todas como leídas"** al final

---

### 2.6 Cambiar Contraseña

#### Olvidé la contraseña

**No hay recuperación automática.** El sistema no tiene enlace de "¿Olvidaste la contraseña?"
ni envía correos, porque el formulario de alta no recoge ninguna dirección (ver 2.1).

La vía es pedírselo al administrador:

1. Contacta con el administrador por los canales habituales de la organización
2. Te asigna una contraseña nueva desde su panel
3. Te la comunica **por un canal distinto** al que usaste para pedirla, si es posible
4. Entra con ella y pídele que te la cambie por una tuya si no puedes hacerlo

**No la envíes ni la pidas por correo electrónico sin cifrar.** Una contraseña en un buzón
queda ahí indefinidamente y abre el acceso a datos de afiliación sindical.

#### Quiero cambiarla, pero la recuerdo

Igual: pídeselo al administrador. La aplicación no tiene todavía pantalla de cambio de
contraseña para las cuentas de sindicato.

> Si esto os resulta incómodo en el uso diario, decídselo al administrador: añadir la
> recuperación por correo es posible, pero exige recoger y custodiar las direcciones, y esa
> decisión es de la organización, no técnica.

---

## 3. Para Imprenta

### 3.1 Acceso al Panel

**¿Cuándo?** Cuando el administrador te haya creado una cuenta en el grupo "Imprenta".

#### Login

1. Abre navegador → `https://tu-dominio.es/login/`
2. Usuario y contraseña (que te proporciona admin)
3. Automáticamente ves: **Panel de Impresión**

#### Qué ves

```
┌────────────────────────────────────────────────────┐
│           LOTES ENVIADOS A IMPRENTA                │
├────────────────────────────────────────────────────┤
│ Sindicato     | Nº Afiliado      | Fecha de envío │
├────────────────────────────────────────────────────┤
│    003        | 000101           | 21/08/26 14:30 │
│    003        | 000102           | 21/08/26 14:30 │
│    007        | 000201           | 20/08/26 10:15 │
│    007        | 000202           | 20/08/26 10:15 │
│    003        | 000103           | 15/08/26 09:45 │
└────────────────────────────────────────────────────┘
```

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

1. **Cambia contraseña inmediatamente** (Cambiar contraseña, ver arriba)
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
- ✓ Historial de cambios audito (quién vio, cuándo)
- ✓ Acceso restringido por rol
- ✓ Sesiones seguras (HTTPS)

**¿Cuánto tiempo se guardan?**
- Afiliados: Mientras sea necesario (consulta DPO de tu sindicato)
- Auditoría de cambios: 2 años (para investigaciones)
- Logs de acceso: 30 días (borrado automático)

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

**R:** Contacta al admin. Puede resetear tu contraseña.

### P: ¿Se puede exportar datos de afiliados?

**R:** Solo imprenta puede descargar lotes listos para imprenta (si admin lo permite). Sindicatos no pueden exportar masivamente.

### P: ¿Qué seguridad hay contra hackers?

**R:**
- **Cifrado en reposo:** nombres y números se guardan cifrados (AES-256-GCM) en el disco del
  servidor. Quien robe una copia de la base de datos no puede leerlos.
- **HTTPS:** la comunicación entre tu navegador y el servidor va cifrada.
- **Contraseñas con hash:** ni el administrador puede ver la tuya.
- **Limitador de intentos:** 5 fallos bloquean el acceso 5 minutos, lo que hace inviable
  probar contraseñas a ciegas.
- **Segundo factor en el administrador:** la cuenta que puede ver los nombres necesita además
  un código de 6 dígitos que cambia cada 30 segundos. Robar su contraseña ya no basta.
- **Auditoría:** cada consulta y cada exportación de datos queda registrada.
- **Content-Security-Policy:** el navegador se niega a ejecutar cualquier script que no venga
  del propio sitio.

> Ojo con un matiz que se confunde a menudo: esto **no** es cifrado extremo a extremo. El
> servidor sí puede leer los datos —necesita hacerlo para imprimir los carnets—. Lo que
> protege el cifrado es el disco y las copias de seguridad, no al propio servidor.

### P: ¿Qué hago si olvido contraseña?

**R:** Pídesela al administrador: no hay recuperación automática por correo (ver 2.6).

### P: ¿Puedo eliminar mis datos?

**R:** Sí, contacta a tu DPO. Es tu derecho (RGPD Art. 17). El admin lo ejecuta con auditoría.

---

## 6. Contactos de Soporte

| Problema | Contacto | Tiempo |
|----------|----------|--------|
| No puedo loguear | admin@sistema.es | 24h |
| Error al subir archivo | admin@sistema.es | 24h |
| Datos incorrectos | tu_sindicato@ejemplo.es + admin | 48h |
| Brecha de seguridad | admin@sistema.es (URGENTE) | 1h |
| Acceso a imprenta | admin@sistema.es | 24h |

---

## 7. Checklist: Primer Uso

- [ ] Solicité acceso en `/registro/`
- [ ] Esperé aprobación (1-2 días)
- [ ] Logueé con mi usuario y contraseña
- [ ] Leí y acepté términos legales
- [ ] Descargué plantilla `afiliados_plantilla.xlsx`
- [ ] Rellené datos de mis afiliados
- [ ] Subí archivo (sin errores)
- [ ] Recibí confirmación de "Éxito"
- [ ] Notificación muestra estado "IMPRESO"

✓ **¡Listo! Tu primer lote está en camino a imprenta.**

---

**Última revisión:** 2026-08-21
**Versión:** 1.0
