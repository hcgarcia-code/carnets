# Manual del Administrador: Sistema de Gestión de Carnets

## 1. Introducción

Como administrador del Sistema de Gestión de Carnets, eres responsable de:
- **Activar/desactivar cuentas** de sindicatos que solicitan acceso
- **Revisar auditoría** de cargas y accesos
- **Gestionar datos sensibles** (desencriptar cuando sea necesario)
- **Manejar incidentes** de seguridad
- **Rotar claves** de cifrado anualmente
- **Mantener la integridad** del sistema

Esta documentación asume que tienes acceso a:
1. `django-admin` (panel administrativo web)
2. Línea de comandos (`manage.py`)
3. Acceso a la base de datos (si es necesario)
4. Las variables de entorno (`.env`)

---

## 2. Acceso Inicial

### 2.1 Crear la Cuenta de Admin

En el servidor (desarrollo o producción):

```bash
cd sistema_carnets
python manage.py createsuperuser
```

Responde a:
- **Username:** tu nombre de usuario (p. ej., `admin`)
- **Email:** tu correo corporativo
- **Password:** contraseña fuerte (≥12 caracteres, mixtos)

### 2.2 Activar el segundo factor — OBLIGATORIO ANTES DE ENTRAR

**El admin exige un código de un solo uso además de la contraseña.** Una cuenta recién creada
todavía no tiene ninguno, y Django no trae pantalla para darlo de alta: **si intentas entrar
antes de este paso, no podrás.**

```bash
python manage.py activar_2fa admin
```

El comando imprime:

```
Segundo factor activado para admin.
Da de alta la cuenta en tu aplicacion de autenticacion
(Google Authenticator, Aegis, 1Password, Bitwarden...):
    Secreto:  1623ebdd6ba6bf2b875500bf36324196ee6ffffb
    O pega esta URL:
    otpauth://totp/admin?secret=CYR6XXLL...&algorithm=SHA1&digits=6&period=30
```

Copia esa URL en tu aplicación de autenticación (o teclea el secreto). A partir de ahí te
generará un código de 6 dígitos que cambia cada 30 segundos.

**Por qué esto es obligatorio y no opcional:** la cuenta de administrador es la única que ve
los nombres de los afiliados descifrados. Todo lo demás del sistema está construido para no
poder verlos —la imprenta no los consulta, la auditoría no los escribe, el disco los guarda
cifrados—, así que **una contraseña de administrador robada entrega el archivo entero de
afiliación sindical**. El segundo factor es lo que impide que una credencial filtrada baste.

> **Si pierdes el teléfono:** vuelve a ejecutar el mismo comando. Revoca el dispositivo
> anterior y emite uno nuevo. Que se acumulasen sería peligroso: un teléfono perdido seguiría
> dando acceso indefinidamente.
>
> Como el comando se ejecuta desde la consola del servidor, **nunca puedes quedarte fuera de
> forma irreversible** mientras tengas acceso a esa consola.

### 2.3 Acceder a django-admin

1. Abre el navegador: `https://tu-dominio.es/admin/`
2. Introduce **usuario, contraseña y el código de 6 dígitos** ("Token OTP")
3. Verás el panel administrativo

**URL:** anótala en favoritos. Es tu punto central de control.

Si el código no se acepta, comprueba que la hora de tu teléfono esté sincronizada: TOTP se
basa en el reloj, y un desfase de más de medio minuto invalida los códigos.

---

## 3. Gestión de Cuentas de Sindicatos

### 3.1 Flujo de Aprobación de Solicitudes

```
1. Sindicato accede a /alta/ y solicita el alta
   ├─ Se crea User (is_active=False, con email OBLIGATORIO)
   ├─ Se crea PerfilSindicato (nombre_identificativo, persona_contacto,
   │                           acuerdo_aceptado=False)
   └─ Se audita: SINDICATO_REGISTRADO

2. Admin revisa en django-admin → Users
   ├─ Busca el usuario nuevo
   ├─ Revisa "Información del sindicato":
   │   - nombre_identificativo → qué sindicato dice ser
   │   - persona_contacto      → quién dice ser quien lo pide
   │   + el email de la cuenta
   ├─ Valida que sea legítimo
   └─ Toma decisión: Activar o Rechazar

3. Para ACTIVAR:
   ├─ Marca: ☑ "Activo" (is_active)
   ├─ Guarda
   └─ Sindicato ya puede loguear

4. Para RECHAZAR:
   ├─ Selecciona usuario
   ├─ "Acción": Eliminar usuarios seleccionados
   ├─ Confirma
   └─ Audita: USUARIO_ELIMINADO
```

### 3.2 Panel de Usuarios en django-admin

**Ruta:** `/admin/auth/user/`

**Columnas importantes:**
| Columna | Significado |
|---------|------------|
| Username | Nombre de usuario (suele ser `cgt_rama_metal`, etc.) |
| Email | Contacto del sindicato |
| Activo | ☑ = puede loguear, ☐ = bloqueado |
| Staff | ☑ = acceso a admin (no usar para sindicatos) |
| Superusuario | ☑ = acceso total (solo para admins) |

**Filtros útiles:**
- "Activo" → muestra solo cuentas habilitadas
- "Sin crear perfil" → cuentas nuevas sin aceptar términos

### 3.3 Editar Información de Sindicato

Dentro de cada usuario, verás una sección **"Información del sindicato"**:

```
Información del sindicato:
  Nombre identificativo: "CGT Rama Metal Barcelona"
  Persona de contacto:   "Ana Ejemplo"
  Acuerdo aceptado: [☑ / ☐]
  Fecha aceptación: 2026-08-15 14:30:45
  IP aceptación: 203.0.113.42
```

**Qué puedes cambiar:**
- `Nombre identificativo` — si el sindicato lo solicita, actualizar
- `Persona de contacto` — cuando cambia quien lleva la cuenta en el sindicato
- `Activo` — marcar/desmarcar para activar/bloquear
- El `email` de la cuenta, si el sindicato cambia de buzón

**Qué NO debes cambiar:**
- `Acuerdo aceptado` — registra voluntad del usuario, no lo falsees
- Fechas/IPs — auditoría inmutable

> **El email no es un dato de adorno: es la única vía de recuperación de
> contraseña.** Si lo dejas mal escrito o apuntas uno personal de alguien que se
> marcha del sindicato, esa cuenta se queda sin forma de recuperarse sola y volvéis
> a depender de ti para cada olvido. Mejor un buzón del sindicato que uno personal.

---

## 4. Gestión de Afiliados

### 4.1 Ver Panel de Afiliados

**Ruta:** `/admin/gestion/afiliado/`

**Vista de lista:**
- Muestra sindicatos códigos (no nombres)
- Datos personales (nombre, número) cifrados en BD, **visibles aquí desencriptados**
- Fecha de creación y estado de impresión

### 4.2 Desencriptar Datos en el Admin

Cuando haces clic en un afiliado, el formulario muestra:

```
Confederacion Territorial: 28
Federacion Local: 28001
Federacion Sectorial: 01
Sindicato Codigo: 100
Num_Afiliado: 123456       ← Desencriptado (era "v1$1:nonce||cipher")
Nombre_Apellidos: Juan Pérez González  ← Desencriptado
Lengua: A (Castellano)
Estado: ALTA
Fecha Expedicion: 2026-08-15
Notas Historicas: Reemisión 2026-05-10
Estado Impresión: PENDIENTE
```

**Importante:** Esta vista desencripta en MEMORIA. No se guarda ni se loguea qué viste.

### 4.3 Marcar Afiliado como "IMPRESO"

Flujo típico:

```
1. Admin filtra: Estado Impresión = "PENDIENTE"
2. Selecciona lote de afiliados (ej. 50 filas)
3. "Acción": Cambiar estado de impresión a "IMPRESO"
4. Confirma
5. fecha_envio_imprenta se auto-rellena (ahora())
6. Sistema audita la exportación (usuario, cantidad, identificadores)
7. Imprenta verá estos afiliados en su panel
```

**Qué ve exactamente la imprenta:**

| Dato | ¿Lo ve? | Por qué |
|---|---|---|
| Código de sindicato | ✓ Sí | Lo necesita para organizar el trabajo |
| **Número de afiliado** | **✓ Sí, legible** | Es el dato que va impreso en el carnet |
| Fecha de envío | ✓ Sí | Trazabilidad del lote |
| **Nombre y apellidos** | **✗ No** | La consulta no incluye esa columna |
| Notas históricas | ✗ No | Ídem |
| Lotes aún en PENDIENTE | ✗ No | Hasta que tú los envías, no existen para ella |

> **Corrige un malentendido frecuente:** el número de afiliado se muestra **en claro**, no
> cifrado. El cifrado protege el dato **en el disco**, no en la pantalla de quien tiene
> permiso para verlo. Si vieras `v1$1:...` en el panel de la imprenta, eso sería un fallo
> (indicaría que la clave de cifrado no está disponible), no una medida de seguridad.
>
> Lo que sí garantiza el diseño es que el **nombre** nunca llega: la vista pide tres columnas
> concretas y el nombre no está entre ellas, así que no puede escaparse por un descuido en la
> plantilla.

**Limitaciones de Imprenta:**
- ✗ No puede cambiar ningún estado (cuenta de solo lectura)
- ✗ No puede subir afiliados (bloqueado explícitamente en la vista de carga)
- ✗ No puede entrar a `/admin/`
- ✓ Cada consulta suya al panel queda auditada

### 4.4 Eliminar o Anonimizar un Afiliado

Son dos cosas distintas y se confunden con facilidad. **Elegir mal deja datos
personales guardados creyendo haberlos suprimido.**

| Quieres… | Herramienta | Qué pasa con el historial |
|----------|-------------|---------------------------|
| Corregir un alta errónea (duplicado, sindicato equivocado) | Botón **Eliminar** del admin | **Se conserva íntegro**, con el nombre dentro |
| Suprimir los datos de una persona (Art. 17, o vencido el plazo) | `expurgar_afiliados` | **Se anonimiza también** |

#### Borrar del admin: para corregir errores, no para suprimir

```
1. Admin selecciona afiliado
2. Botón "Eliminar"
3. Confirma
4. La fila desaparece — pero su historial NO
5. Queda registrado en /admin/admin/logentry/ (log del admin de Django)
```

> **El borrado del admin no suprime nada a efectos del RGPD.**
> `django-simple-history` guarda una copia de cada versión del afiliado en
> `gestion_historicalafiliado` **para siempre**. Borrar la fila viva deja el nombre
> anterior ahí, cifrado pero recuperable con la clave, e invisible desde la
> aplicación: es decir, deja sin suprimir justo el dato que acabas de declarar
> suprimido. Para una solicitud de supresión, ve al apartado 8.3.

#### Anonimizar: `expurgar_afiliados`

```bash
python manage.py expurgar_afiliados --dry-run   # SIEMPRE primero
python manage.py expurgar_afiliados
```

Anonimiza los afiliados **en estado BAJA** cuya `fecha_baja` tenga más de **3 años**
(el plazo que fija la EIPD). Sustituye nombre y número por valores neutros **en la
ficha y en todo su historial**, y deja el recuento de carnets emitidos, que ya no
identifica a nadie.

| Opción | Para qué |
|--------|----------|
| `--dry-run` | Dice a cuántos afectaría sin tocar nada |
| `--anios N` | Cambia el plazo (por defecto 3) |

Deja rastro en la auditoría como `afiliados.expurgados`. Ese registro **es la prueba
de haber cumplido el plazo** —y de no haberte adelantado a él—, porque después del
expurgo ya no queda dato que enseñar.

> **Avisa de las bajas sin fecha.** Si el comando dice *"N afiliado(s) de baja sin
> fecha de baja"*, son bajas anteriores a que el campo existiera: no hay plazo que
> contar, así que no las toca. **Revísalas a mano**, no las ignores: si las dejas,
> se quedan fuera del expurgo para siempre. Para saldarlas, ponles una `fecha_baja`
> razonable (la de la última modificación del historial suele servir) o
> anonimízalas a mano.

---

## 5. Auditoría e Investigación

### 5.1 Ver el Historial de Cambios

**Ruta:** `/admin/gestion_historicalafiliado/`

Esta tabla muestra **cada cambio** hecho a cada afiliado:

```
History ID | Date | User | Accion | Confederacion | Num_Afiliado | Nombre | ...
1           | 2026-08-15 10:30 | admin_user | created | 28 | v1$1:... | v1$1:... | ...
2           | 2026-08-15 15:45 | admin_user | changed (estado_impresion=IMPRESO) | 28 | v1$1:... | v1$1:... | ...
```

**Filtros útiles:**
- Por usuario (quién hizo cambios)
- Por fecha (cuándo)
- Por change_reason (por qué)

### 5.2 Auditar Registros de Subida

**Ruta:** `/admin/gestion/registrosubida/`

Cada subida de Excel genera un registro:

```
Sindicato | Fecha | Cantidad | Nombre Archivo
CGT Metal | 2026-08-15 14:20 | 150 | afiliados_agosto.xlsx
```

**Información:**
- **Sindicato:** Quién subió
- **Fecha:** Cuándo
- **Cantidad:** Cuántos afiliados se cargaron
- **Nombre Archivo:** el que le puso el sindicato

> **Ojo con el nombre del archivo.** Se guarda **en esta tabla** tal cual lo mandó el
> sindicato, y lo elige él: nada le impide subir `maria_fernandez.xlsx`, y entonces
> esta columna contiene un dato personal. No aparece en cambio en el registro de
> auditoría en JSON (§5.3), que solo guarda el recuento.
>
> Si ves nombres de personas en esta columna, díselo al sindicato. Y tenlo en cuenta
> al expurgar: esta tabla no la toca `expurgar_afiliados`.

### 5.3 Revisar Logs de Acceso

El registro de auditoría se escribe en la ruta que indique `AUDITORIA_LOG_PATH` en el `.env`
del servidor. Sin esa variable **solo va a la salida estándar y se pierde**, así que en
producción es obligatoria.

Formato: un JSON por línea, pensado para que lo lea una máquina.

```json
{"accion": "sindicato.registrado", "ip": "203.0.113.42", "ts": "2026-08-21T10:30:45Z", "usuario": "cgt_nueva"}
{"accion": "afiliados.cargados", "cantidad": 50, "ip": "203.0.113.42", "ts": "...", "usuario": "cgt_metal"}
{"accion": "afiliados.exportados", "cantidad": 150, "ids": ["1","2"], "ip": "203.0.113.9", "ts": "...", "usuario": "admin"}
{"accion": "login.bloqueado", "ip": "198.51.100.7", "ts": "...", "usuario": "admin"}
```

**Aquí no van datos de afiliados.** Se registra quién, cuándo, desde dónde, qué operación y
sobre cuántos registros; nunca el nombre ni el número de afiliado. Un registro de auditoría
con los datos dentro sería una segunda copia sin cifrar de justo lo que se acaba de cifrar.

> **Salvedad heredada del beta.** El campo `usuario` es el nombre de la cuenta, y llegaron dos
> cuentas cuyo nombre de usuario es un DNI. En esas dos, una línea del registro dice que el
> titular de un documento concreto ha cargado afiliación sindical —dato de categoría especial
> del Art. 9— dentro de un archivo que se envía a un destino externo.
>
> El alta ya no lo permite: el formulario rechaza DNI y NIE como nombre de usuario. Las dos que
> quedan hay que renombrarlas. Para localizarlas:
>
> ```bash
> python sistema_carnets/manage.py shell -c "import re; from django.contrib.auth.models import User; print([u.username for u in User.objects.all() if re.fullmatch(r'\d{8}[A-Za-z]|[XYZxyz]\d{7}[A-Za-z]', u.username)])"
> ```
>
> **Avisa al sindicato antes de renombrar**: le cambia la forma de entrar. La contraseña y todo
> lo demás siguen igual. Desde el admin, campo "Nombre de usuario".

### 5.4 Alertas automáticas: que alguien se entere

Un registro que nadie lee documenta el incidente, pero no lo detecta. Para que llegue un aviso:

```bash
python manage.py revisar_auditoria
```

Revisa la última hora y **envía un correo** si encuentra algo reseñable:

| Suceso | Umbral | Por qué ese umbral |
|---|---|---|
| `login.bloqueado` | 3 en la ventana | Un bloqueo suelto es alguien que olvidó su contraseña; una racha es un ataque |
| `acceso.denegado` | 3 en la ventana | Ídem: alguien tanteando permisos |
| `afiliados.exportados` | **1** | Saca datos personales a un archivo descargable: con una vez basta |

Ponlo en cron, una vez por hora:

```
0 * * * * cd /ruta/al/proyecto && python manage.py revisar_auditoria
```

Necesita `ADMINS` y `EMAIL_HOST` configurados para que el correo salga de verdad.

> **Esto es el escalón de mientras tanto, no el destino.** Un archivo en el propio servidor lo
> puede editar quien lo haya comprometido, y entonces este comando no ve nada. La auditoría
> seria vive en un destino externo de solo-adición: ver `deploy/auditoria_centralizada.md`.

También está el **log del admin de Django** en `/admin/admin/logentry/`, que registra altas,
cambios y bajas hechas desde el panel.

---

## 6. Gestión de Claves de Cifrado

### 6.1 Entender la Rotación de Claves

Las claves se almacenan en `.env`:

```
CARNETS_ENCRYPTION_KEYS=k2:CLAVE_NUEVA_BASE64=,k1:CLAVE_ANTERIOR_BASE64=
```

**ID de clave en datos:**
```
v1$1:nonce||ciphertext   ← cifrado con clave ID "1"
v1$2:nonce||ciphertext   ← cifrado con clave ID "2"
```

El sistema **siempre** desencripta correctamente leyendo el ID.

### 6.2 Rotar Claves Anualmente

**Paso 1: Generar Nueva Clave**

```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Salida: a1b2c3d4e5f6...7f8e9d10 (64 caracteres = 256 bits)
```

**Paso 2: Actualizar .env**

```
# Antes:
CARNETS_ENCRYPTION_KEYS=k1:a1b2c3...=

# Después:
CARNETS_ENCRYPTION_KEYS=k2:x9y8z7...=,k1:a1b2c3...=
```

**Paso 3: Re-cifrar los datos antiguos**

**No hay que programar nada: el comando ya existe.**

```bash
python manage.py reencriptar_afiliados --dry-run   # primero, para ver cuántas filas toca
python manage.py reencriptar_afiliados
```

Qué hace, y por qué importan los detalles:

- **Incluye la tabla de historial**, no solo los afiliados. De nada serviría re-cifrar el
  afiliado si su historial de auditoría se queda bajo la clave antigua: seguirías sin poder
  retirarla.
- **Aborta sin escribir nada** si encuentra filas cifradas con una clave que ya no está
  configurada, y te dice cuáles son. Vuelve a añadir esa clave y repite.
- **Usa `bulk_update`, que no emite señales**, así que django-simple-history no crea una
  entrada de historial por afiliado. Es deliberado: no está cambiando ningún dato, solo la
  clave con la que está cifrado, y llenar la auditoría de cambios que no ha hecho nadie sería
  peor que inútil.

Todo ocurre dentro de una transacción: si algo falla a mitad, no queda la base de datos con
unas filas bajo la clave nueva y otras bajo la vieja.

**Paso 4: Retirar la clave antigua**

Una vez todas las filas están bajo la clave nueva, ya puedes quitar la anterior del `.env`:

```
CARNETS_ENCRYPTION_KEYS=k2:x9y8z7...=
```

> **Riesgo irreversible.** Si retiras una clave y queda una sola fila cifrada con ella, ese
> dato es **irrecuperable**: no hay forma de descifrarlo, ni por soporte ni por copia de
> seguridad. Ejecuta siempre `reencriptar_afiliados` antes, y verifica que terminó sin errores.
>
> Mantener 2 versiones vivas mientras dure la transición es lo prudente.

### 6.3 Backup de Claves

**CRÍTICO:** Las claves son el corazón del sistema.

- ☑ Guardar `.env` en bóveda segura (1Password, Vault, KMS)
- ☑ Realizar backups periódicos (diarios)
- ☑ Encriptar backups (AES-256 también)
- ✗ Nunca commitear `.env` en git
- ✗ Nunca compartir claves por email

---

## 7. Configuración de Roles y Permisos

### 7.1 Crear Cuenta de Imprenta

```
1. Django-admin → Users → Add User
2. Username: imprenta
3. Password: [genera con secrets.token_urlsafe(12)]
4. Guarda
5. Edita el usuario:
   - Marca "Activo"
   - NO marques "Staff" ni "Superusuario"
   - Scroll a "Grupos" (Groups)
   - Selecciona "Imprenta" de la lista
   - Guarda
```

**Resultado:** Imprenta puede loguear, ver panel, pero no subir ni acceder a admin.

### 7.2 Cambiar Permisos de Un Sindicato

Algunos sindicatos pueden tener permisos especiales:

```
1. Admin → Users → Edita Usuario
2. Scroll a "Permisos de usuario" (User permissions)
3. Ejemplo: agregar "Can delete afiliado"
   [Esto le permite eliminar sus propios afiliados desde una vista custom]
4. Guarda
```

**Cuidado:** No todos los permisos están activos. Solo los que están en la app.

### 7.3 Listar Usuarios por Rol

```bash
# En manage.py shell:
python manage.py shell

from django.contrib.auth.models import User, Group

# Sindicatos activos
User.objects.filter(is_active=True, is_staff=False, is_superuser=False).count()

# Imprenta
imprenta_group = Group.objects.get(name='Imprenta')
imprenta_group.user_set.all()

# Administradores
User.objects.filter(is_superuser=True)
```

---

## 8. Procedimientos de Incidentes

### 8.1 Incident: Contraseña Comprometida

**Síntomas:**
- Acceso no autorizado desde IP extraña
- Cambios inesperados en afiliados
- Sindicato reporta "no reconozco esta subida"

**Respuesta:**
```
1. Investigar auditoría:
   - Quién hizo cambios (usuario)
   - Cuándo (fecha/hora)
   - Desde dónde (IP)

2. Decidir:
   - ¿Fue acceso fraudulento? → Deshacer cambios, rotar contraseña
   - ¿Fue error del sindicato? → Notificar, documentar

3. Cortar el acceso YA:
   django-admin → Users → Edita usuario → desmarca "Activo" → Guarda
   [Esto expulsa a quien esté dentro en cuanto caduque su sesión, como
    máximo a la media hora, y le impide volver a entrar]

4. Reponer la contraseña. Dos vías, y la primera es mejor:
   a) Dile al sindicato que use /recuperar-password/ (le llega un enlace
      de un solo uso a su correo). Así la contraseña nueva no pasa por ti
      ni por ningún canal intermedio.
   b) Si perdieron también el buzón: django-admin → Users → "Establecer
      contraseña". Comunícasela por un canal distinto al que usó para
      pedírtela.

5. Vuelve a marcar "Activo" cuando la cuenta esté saneada
```

> **El botón "Establecer contraseña" del admin no envía ningún correo.** Es de
> Django y solo cambia el hash: si lo usas, tienes que comunicar la contraseña tú, y
> ese es precisamente el paso frágil. Prefiere siempre `/recuperar-password/`.

> **Desactivar la cuenta no cierra la sesión abierta al instante.** Django comprueba
> `is_active` al autenticar, no en cada petición; quien ya esté dentro sigue hasta
> que su sesión caduque (`SESSION_COOKIE_AGE`, 30 minutos por defecto). Si necesitas
> echarlo ahora mismo, borra sus sesiones:
> ```bash
> python manage.py shell -c "
> from django.contrib.sessions.models import Session
> from django.utils import timezone
> for s in Session.objects.filter(expire_date__gte=timezone.now()):
>     if s.get_decoded().get('_auth_user_id') == 'ID_DEL_USUARIO':
>         s.delete()
> "
> ```

### 8.2 Incident: Datos Exfiltrados (Brecha)

**Validar primero:** ¿Realmente fue una brecha? ¿O solo acceso legítimo?

```
1. Verificar auditoría:
   - ¿Quién accedió a qué datos?
   - ¿Desde qué IP?
   - ¿Cuándo?

2. Si fue un admin viendo datos legítimamente → No es brecha

3. Si fue acceso no autorizado:
   - Cambiar contraseña de admin
   - Auditar todas las máquinas de admin (en logs)
   - Comprobar que el segundo factor sigue activo y es tuyo

4. Notificar (ver el matiz de abajo):
   - Al DPO y a los sindicatos afectados, cuanto antes
   - A la AEPD, salvo que sea improbable que haya riesgo
```

> **No hay ningún umbral de "X% de afectados".** El criterio del RGPD (Art. 33) es
> otro: se notifica a la AEPD **siempre**, en 72 horas, *salvo* que sea improbable
> que la brecha suponga un riesgo para los derechos y libertades de las personas. Y
> aquí el dato es **afiliación sindical**, categoría especial del Art. 9: dar por
> improbable el riesgo con estos datos es muy difícil de sostener. **Ante la duda, se
> notifica.**
>
> Las 72 horas cuentan **desde que la organización tiene conocimiento**, no desde que
> terminas de investigar. Si a las 72 horas no lo sabes todo, se notifica con lo que
> haya y se completa después: el propio Art. 33.4 lo permite.
>
> **Quien notifica es el sindicato responsable de los datos**, no esta aplicación.
> Tu papel es darle los hechos —qué pasó, cuándo, qué datos, cuántas personas, qué
> has hecho— con la auditoría en la mano y sin tardar.

### 8.3 Incident: Afiliado Solicita Supresión (RGPD Art. 17)

**La solicitud no te llega a ti.** El responsable de los datos es **el sindicato** al
que la persona está afiliada, no esta aplicación ni CGT Confederal: aquí los datos
solo se tratan por encargo, para confeccionar el carnet. Quien recibe, valora y
contesta la solicitud es el sindicato. Tú ejecutas lo que te pida.

```
1. El sindicato verifica la solicitud (es su obligación, no la tuya)
   y te pide por escrito la supresión, identificando al afiliado por
   su número, NO por su nombre en un correo sin cifrar

2. Localizas la ficha en /admin/gestion/afiliado/

3. La anonimizas — ficha E HISTORIAL:
```

```bash
python manage.py shell
```

```python
from gestion.models import Afiliado
from gestion.auditoria import ACCIONES, registrar

IDS = [1234]   # las pk de las fichas a suprimir

Afiliado.history.filter(id__in=IDS).update(
    nombre_apellidos="ANONIMIZADO", num_afiliado="000000", notas_historicas="")
Afiliado.objects.filter(pk__in=IDS).update(
    nombre_apellidos="ANONIMIZADO", num_afiliado="000000", notas_historicas="")
registrar(ACCIONES.AFILIADOS_EXPURGADOS,
          usuario="supresion_art17", cantidad=len(IDS), ids=IDS)
```

```
4. Verificación:
   - La ficha ya no lleva nombre en el admin
   - El historial de esa ficha tampoco (compruébalo, es el paso que se olvida)
   - Confirmas al sindicato para que conteste al afiliado

5. Plazo: 30 días desde que el afiliado lo pidió a su sindicato.
```

> **Primero el historial, luego la ficha.** En ese orden: si anonimizas la ficha
> viva, `django-simple-history` crea **una versión más** con el dato viejo dentro y
> vuelves a tener el problema.
>
> **Y no uses el botón "Eliminar" del admin para esto.** Borra la fila y deja el
> historial completo, con el nombre: habrías respondido "suprimido" conservando el
> dato (ver 4.4).

> **Antes de suprimir, comprueba si procede.** El derecho del Art. 17 no es
> incondicional: si el afiliado sigue de alta y el carnet está en curso, el sindicato
> puede tener base para conservarlo. Esa valoración es del sindicato; tú no la haces
> ni la discutes, pero tampoco ejecutes una supresión que nadie te ha pedido por
> escrito.

---

## 9. Mantenimiento Periódico

### 9.1 Semanal

- [ ] Revisar nuevas solicitudes de alta (`/admin/auth/user/`, filtro "Activo" = No)
- [ ] Aprobar (acción "Aprobar las cuentas de sindicato seleccionadas") o eliminar
- [ ] Ojear los avisos que haya enviado `revisar_auditoria` durante la semana

### 9.2 Mensual

- [ ] Auditar accesos de imprenta (consultas totales, IPs)
- [ ] Revisar cargas de afiliados (¿hay patrones sospechosos?)
- [ ] **Comprobar que los backups cifrados se están generando de verdad** (no basta con que el
      cron exista: mira que haya objetos nuevos en el destino)
- [ ] Listar permisos especiales (¿quién tiene qué?)
- [ ] Verificar que `revisar_auditoria` sigue corriendo (si nunca llega ningún correo, puede
      ser que no haya incidencias... o que el cron esté parado)

### 9.3 Trimestral

- [ ] **Ejecutar el expurgo del plazo de conservación** (RGPD Art. 5.1.e). Primero en seco:
      ```bash
      python manage.py expurgar_afiliados --dry-run
      python manage.py expurgar_afiliados
      ```
      Si avisa de bajas **sin fecha de baja**, resuélvelas: son anteriores al campo y
      se quedan fuera del expurgo para siempre si nadie las mira (ver 4.4)
- [ ] Revisar incidentes del trimestre
- [ ] **Comprobar que el segundo factor del admin sigue funcionando** (entra y sal; si has
      cambiado de teléfono sin reejecutar `activar_2fa`, te enterarás ahora y no en una urgencia)
- [ ] Verificar capacidad de almacenamiento (logs, BD)
- [ ] Repasar que CI sigue en verde en GitHub Actions, **incluido `pip-audit`**: avisa de
      vulnerabilidades conocidas en las dependencias en cada push

### 9.4 Anualmente

- [ ] Rotación de claves de cifrado (ver sección 6)
- [ ] Backup de configuración (.env, settings)
- [ ] Auditoría de seguridad completa
- [ ] Revisar y actualizar política de retención (con DPO)
- [ ] Capacitación en seguridad para admins

---

## 10. Troubleshooting Común

### P: No puedo loguear en django-admin

**R:**
1. Verifica que tu usuario sea superuser:
   ```bash
   python manage.py shell
   from django.contrib.auth.models import User
   u = User.objects.get(username='tu_usuario')
   u.is_superuser  # Debe ser True
   ```
2. Si es False:
   ```bash
   u.is_superuser = True
   u.is_staff = True
   u.save()
   ```

### P: Un sindicato no puede subir archivos

**R:**
1. Verifica que esté activo: `is_active = True`
2. Verifica que haya aceptado términos: `PerfilSindicato.acuerdo_aceptado = True`
3. Verifica que no esté en grupo "Imprenta": `groups.filter(name='Imprenta').exists() = False`

### P: Los nombres aparecen cifrados en django-admin

**R:**
1. Verifica que `CARNETS_ENCRYPTION_KEYS` esté en `.env`
2. Verifica que la clave sea válida (256 bits = 64 caracteres en hex)
3. Reinicia el servidor Django
4. Si aún no desencripta, check logs:
   ```bash
   grep -i "decrypt" sistema_carnets/logs/*.log
   ```

### P: Imprenta ve nombres en su panel

**R (CRÍTICO):** Esto sí sería un fallo de seguridad real. Comprueba, por este orden:

1. La vista `panel_imprenta()` en `views.py` debe pedir **solo tres columnas**:
   ```python
   .values('sindicato_codigo', 'num_afiliado', 'fecha_envio_imprenta')
   # 'nombre_apellidos' NO debe aparecer aquí
   ```
2. La plantilla `panel_imprenta.html` no debe referenciar `nombre_apellidos`.
3. Hay una prueba que lo vigila: `tests/test_alta_e_imprenta.py::test_el_panel_no_muestra_nombres_ni_notas`.
   Ejecútala. Si falla, no despliegues.

### P: Imprenta ve el número de afiliado en claro, ¿es un fallo?

**R: No, es lo esperado.** El número es el dato que necesita para imprimir el carnet. El
cifrado protege el disco y las copias de seguridad, no la pantalla de quien tiene permiso.

Lo que sí sería un fallo es lo contrario: si en el panel aparece `v1$1:...` o
`⟨no descifrable⟩`, significa que **la clave de cifrado no está disponible** y hay que revisar
`CARNETS_ENCRYPTION_KEYS` de inmediato (ver la pregunta siguiente).

---

## 11. Contactos y Escaladas

| Situación | A quién contactar | Urgencia |
|-----------|------------------|----------|
| Nueva solicitud de alta | DPO del sindicato (verificar email) | Baja (24h) |
| Brecha de datos | DPO, AEPD | **CRÍTICA (1h)** |
| Contraseña admin olvidada | Contacto técnico | Media (2h) |
| Error en subida de afiliados | Sindicato + equipo técnico | Media (4h) |
| Imprenta no ve datos | Equipo técnico | Media (4h) |
| Backup fallido | Equipo técnico | **CRÍTICA (1h)** |

---

## 12. Apéndice: Comandos Útiles

### Los comandos del proyecto

Todos se ejecutan desde la raíz, con el entorno activado:
`python sistema_carnets/manage.py <comando>`

| Comando | Para qué | Ojo con |
|---------|----------|---------|
| `expurgar_afiliados` | Anonimiza las bajas con el plazo vencido (§4.4) | **Irreversible.** Usa `--dry-run` antes, siempre |
| `reencriptar_afiliados` | Re-cifra todo con la clave nueva al rotar (§6.2) | Aborta si falta alguna clave antigua; no escribe nada a medias |
| `revisar_auditoria` | Manda correo si hay algo reseñable en la última hora (§5.4) | Necesita `ADMINS` y `EMAIL_HOST` configurados |
| `activar_2fa` | Da de alta el segundo factor de una cuenta de admin (§2.2) | Sin esto no se entra al admin |
| `backup_a_s3_cifrado` | Copia de seguridad cifrada a Object Storage | Ver `deploy/backups_cifrados_s3.md` |
| `importar_desde_beta` | Trae cuentas y afiliados del despliegue beta | Solo para la migración inicial; ver abajo |
| `sanear_volcado_beta` | Fija por **asunción** el estado y la lengua ilegibles del volcado | No recupera el dato: lo inventa según un criterio. Guarda su salida |
| `preparar_pruebas` | Monta un entorno de pruebas completo | **Se niega a correr con `DEBUG=False`** o sobre una base con afiliados |
| `avisar_version_2` | Avisa por correo a los sindicatos del paso a la 2.0 | **En seco por defecto**: sin `--enviar` no manda nada. No lleva control de "ya enviado" |

### Avisar a los sindicatos de un cambio

```bash
python sistema_carnets/manage.py avisar_version_2 --url https://LA-DIRECCION
python sistema_carnets/manage.py avisar_version_2 --url https://LA-DIRECCION --enviar
```

**Compone un mensaje por destinatario, nunca uno con todos.** Meter a todos los
sindicatos en el mismo correo dejaría que cada uno viera la lista completa de los
demás con sus direcciones: quién está usando el sistema de carnets de CGT. Eso no
es un descuido de estilo, es una comunicación de datos a terceros.

Mira la lista de **"sindicatos SIN correo"** que saca en seco: a esos no les llega
nada y hay que avisarles por teléfono. El texto vive en
`gestion/templates/gestion/correo/version_2.txt`.

### Migración desde el beta (una sola vez)

```bash
# En el beta — solo las tres tablas que hacen falta, no la base entera:
python manage.py dumpdata auth.User gestion.PerfilSindicato gestion.Afiliado \
    --indent 2 -o beta.json

# En el 2.0:
python sistema_carnets/manage.py importar_desde_beta beta.json --dry-run
python sistema_carnets/manage.py importar_desde_beta beta.json
```

- **Copia el hash de la contraseña sin volver a cifrarlo**, así que los sindicatos
  entran con la contraseña que ya tenían y no hay que repartir credenciales nuevas
- **No duplica**: descarta los afiliados que ya existan para el mismo sindicato y número
- Recupera la fecha de alta original, que `auto_now_add` machacaría

El procedimiento completo, con el estado de los datos del beta y qué hacer con las
filas corruptas, está en **`deploy/migrar_desde_beta.md`**.

### Django Shell

```bash
cd sistema_carnets
python manage.py shell
```

**Dentro:**

```python
# Contar usuarios activos
from django.contrib.auth.models import User
User.objects.filter(is_active=True).count()

# Buscar usuario por email
u = User.objects.get(email='cgt@example.es')

# Cambiar contraseña programáticamente
u.set_password('nueva_contraseña_fuerte')
u.save()

# Ver afiliados de un sindicato
from gestion.models import Afiliado
afiliados = Afiliado.objects.filter(sindicato_usuario=u)
for a in afiliados:
    print(f"{a.nombre_apellidos} - {a.num_afiliado}")

# Desencriptar un dato específico
a = Afiliado.objects.first()
print(a.nombre_apellidos)  # Desencriptado automáticamente

# Ver si está cifrado en BD
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT nombre_apellidos FROM gestion_afiliado LIMIT 1")
row = cursor.fetchone()
print(row[0])  # v1$1:nonce||cipher (cifrado en BD)
```

### Bash

```bash
# Exportar lista de usuarios
python manage.py shell << EOF
from django.contrib.auth.models import User
for u in User.objects.filter(is_active=True):
    print(f"{u.username},{u.email},{u.is_superuser}")
EOF

# Crear backup de BD
python manage.py dumpdata > backup_$(date +%Y%m%d).json

# Limpiar cache
python manage.py shell << EOF
from django.core.cache import cache
cache.clear()
print("✓ Cache limpiada")
EOF
```

---

**Última revisión:** 2026-08-27
**Versión:** 2.0

**Qué cambió en la 2.0.** Se corrigieron tres cosas que podían llevar a error real:

1. **§4.4 y §8.3 — supresión de datos.** La versión anterior presentaba como
   *garantía* que el historial sobrevive al borrado. Para una solicitud del Art. 17
   eso es justo el fallo: borrar la fila del admin deja el nombre en
   `gestion_historicalafiliado`, y habrías contestado "suprimido" conservando el
   dato. Ahora se distingue borrar (corregir errores) de anonimizar
   (`expurgar_afiliados`), y el procedimiento del Art. 17 anonimiza **historial
   primero, ficha después**.
2. **§8.1 — "el botón Establecer contraseña envía un correo".** No lo envía; es de
   Django y solo cambia el hash. Además ya existe `/recuperar-password/`, que es la
   vía correcta. Se añade cómo cerrar de verdad una sesión abierta.
3. **§8.2 — el umbral ">2% de usuarios" para notificar a la AEPD.** No existe. El
   criterio del Art. 33 es el riesgo, y quien notifica es el sindicato responsable.

Se añaden `expurgar_afiliados`, `importar_desde_beta` y el resto de comandos (§12),
el expurgo trimestral (§9.3), `pip-audit` en CI, y los campos nuevos del alta
(correo obligatorio y persona de contacto). También se anota que
`RegistroSubida.nombre_archivo` guarda el nombre que eligió el sindicato y puede
llevar datos personales (§5.2). Se corrigió `/registro/` → `/alta/` y se retiró la
acción de auditoría `AFILIADO_ELIMINADO`, que no existe.
