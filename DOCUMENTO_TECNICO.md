# Documento Técnico: Sistema de Gestión de Carnets Sindicales

## 1. Resumen Ejecutivo

El Sistema de Gestión de Carnets es una aplicación Django 5.2 diseñada para gestionar datos de afiliación sindical con **máxima confidencialidad y trazabilidad**. Implementa encriptación de datos personales en reposo, auditoría inmutable de todas las operaciones, y control de acceso basado en roles para proteger información clasificada bajo el RGPD Artículo 9 (datos de categoría especial).

**Pilares técnicos:**
- Cifrado AES-256-GCM a nivel de columna, con seam de KMS para rotar claves
- Auditoría de **lecturas y escrituras**, sin datos personales dentro
- Segundo factor (TOTP) en el admin, la única cuenta que descifra
- Limitadores de intentos respaldados por caché compartida
- Comprobaciones que impiden desplegar con una configuración insegura

> **Un matiz que se malinterpreta a menudo:** esto es cifrado **en reposo**, no extremo a
> extremo. El servidor puede leer los datos —los necesita para imprimir los carnets—. Lo que
> el cifrado protege es el disco y las copias de seguridad: quien robe el archivo de la base de
> datos no obtiene nombres, solo texto cifrado.

---

## 2. Arquitectura de Seguridad

### 2.1 Capas de Protección

```
┌─────────────────────────────────────┐
│  Infraestructura (nginx / WAF)      │  TLS, limit_req, fail2ban  [deploy/waf_y_ddos.md]
├─────────────────────────────────────┤
│  Cabeceras de seguridad             │  CSP, HSTS, nosniff, X-Frame-Options
├─────────────────────────────────────┤
│  Interfaz Web (Django Templates)    │  Autoescapado; sin |safe ni mark_safe
├─────────────────────────────────────┤
│  Vistas + Autenticación             │  Sesión, CSRF, limitadores, 2FA en el admin
├─────────────────────────────────────┤
│  Modelos + Cifrado en Columnas      │  AES-256-GCM + nonce por escritura
├─────────────────────────────────────┤
│  Auditoría (accesos + cambios)      │  JSON sin PII + HistoricalRecords
├─────────────────────────────────────┤
│  Almacenamiento (SQLite/PostgreSQL) │  Datos cifrados en reposo, TLS verify-full
└─────────────────────────────────────┘
```

**Ninguna capa depende de que la de arriba haya hecho su trabajo.** Si la CSP falla, el
autoescapado sigue; si alguien roba la base de datos, el cifrado sigue; si roba la contraseña
del admin, el segundo factor sigue.

### 2.2 Encriptación de Datos Personales

**Campos cifrados:**
- `Afiliado.nombre_apellidos` — nombre completo (CampoTextoCifrado)
- `Afiliado.num_afiliado` — número de afiliación de 6 dígitos (CampoTextoCifrado)
- `Afiliado.notas_historicas` — registro de reemisiones (CampoTextoCifrado)

**Algoritmo:**
- **Cifrador:** AES-256-GCM (cifrado autenticado)
- **Clave:** los 32 bytes en crudo que resultan de decodificar el base64 de la configuración.
  **No hay derivación** (ni PBKDF2 ni scrypt): la clave ya es material aleatorio de 256 bits,
  generado con `os.urandom(32)`. Derivar tendría sentido si partiéramos de una contraseña
  humana, que no es el caso.
- **Nonce:** 96 bits de `os.urandom(12)`, **nuevo en cada escritura**
- **Formato almacenado:** `v1$<id_clave>$<base64(nonce || ciphertext+tag)>`

Tres partes separadas por `$`:

```
v1$k1$VGhpcyBpcyBub3QgcmVhbCwgZXMgc29sbyB1biBlamVtcGxvIGRlIGZvcm1hdG8=
│  │  └─ base64 de: nonce (12 bytes) + ciphertext + tag de autenticación (16 bytes)
│  └──── identificador de la clave con la que se cifró
└─────── versión del formato
```

El identificador de clave viaja con el dato: por eso pueden convivir varias claves y se puede
rotar sin reescribir toda la base de datos de golpe.

**Por qué es seguro:**
- **No determinista:** el nonce cambia en cada escritura, así que cifrar dos veces el mismo
  nombre da resultados distintos. Un atacante con acceso al disco no puede deducir que dos
  filas contienen la misma persona.
- **Autenticado:** GCM lleva un tag de integridad. Alterar un nombre editando la base de datos
  directamente no produce otro nombre: produce un error de descifrado.
- **Falla cerrado:** sin clave configurada la aplicación no arranca (`GestionConfig.ready`).
  Nunca se guarda en claro «por un despiste de configuración».
- **No sobrescribe lo ilegible:** si un valor no se puede descifrar, se devuelve un marcador
  de tipo propio (`TextoNoDescifrable`) que `get_prep_value` se **niega a escribir de vuelta**.
  Sin esa protección, abrir y guardar una ficha con la clave equivocada destruiría el dato
  original de forma irreversible.

### 2.3 Gestión de Claves (KMS Seam)

Las claves llegan a través de un **proveedor sustituible**, definido en
`settings.CARNETS_KEY_PROVIDER`: la ruta de un invocable sin argumentos que devuelve una
cadena. El proveedor por defecto (`gestion.crypto.proveedor_desde_entorno`) la lee del `.env`.

Formato de esa cadena — **no es JSON**:

```
CARNETS_ENCRYPTION_KEYS=k2:CLAVE_NUEVA_BASE64=,k1:CLAVE_ANTERIOR_BASE64=
```

`id:clave_base64` separados por comas. **La primera de la lista es la que cifra**; las demás
solo se conservan para poder leer lo guardado antes de la última rotación.

Generar una clave:
```bash
python -c "import base64,os; print(base64.b64encode(os.urandom(32)).decode())"
```

**Estrategia de rotación:**
1. Genera una clave nueva y ponla **la primera**, dejando la anterior detrás
2. Reinicia el proceso (el resultado del proveedor se cachea en memoria a propósito, para no
   llamar al KMS una vez por cada campo descifrado)
3. Ejecuta `manage.py reencriptar_afiliados` — reescribe afiliados **y su historial**
4. Retira la clave antigua del `.env`

**Restricción de cumplimiento:** el proveedor de KMS debe estar en la UE. Ver
`deploy/RESTRICCION_UE.md` (recomendación: HashiCorp Vault autoalojado) y
`deploy/claves_y_kms.md` para implementaciones copiables.

> El proveedor por defecto —el del `.env`— deja la clave tan protegida como el propio archivo
> del servidor, que es **menos de lo que exige el Art. 32 RGPD**. Sustitúyelo por el del KMS
> antes de tratar datos reales.

### 2.4 Auditoría e Inmutabilidad

**django-simple-history registra:**
- Crear, modificar, eliminar afiliados
- Cambiar estado de impresión
- Quién, cuándo, desde qué IP

**Tabla `simple_history_afiliado`:**
```sql
SELECT 
  history_id, 
  history_date, 
  history_user_id, 
  history_change_reason,
  confederacion_territorial,
  num_afiliado,  -- cifrado en v1$...
  nombre_apellidos,  -- cifrado en v1$...
FROM simple_history_afiliado
ORDER BY history_date DESC
```

**Garantías:**
- Los registros son **de solo lectura** (no se pueden editar, solo crear)
- Incluyen **timestamp y usuario** de cada cambio
- Preservan el **estado exacto** de cada campo en el momento del cambio
- No se purgan automáticamente (política de retención: consultar DPO)

**Las LECTURAS también se auditan** (`gestion/auditoria.py`), y esto es lo que distingue a
este sistema de uno que solo registre cambios. Para datos de categoría especial hay que poder
demostrar quién *consultó* qué, no solo quién lo modificó: sin ello, alguien con acceso al
admin puede llevarse el expediente de todos los afiliados sin dejar rastro.

| Acción | Cuándo se emite |
|---|---|
| `afiliados.consultados` | Alguien abre el listado del admin |
| `afiliado.abierto` | Alguien abre una ficha concreta |
| `afiliados.exportados` | Exportación a Excel (la operación más sensible) |
| `afiliados.cargados` | Un sindicato sube un lote |
| `lote_impresion.consultado` | La imprenta abre su panel |
| `acceso.denegado` | Intento rechazado por permisos |
| `sindicato.registrado` | Alta autoservicio |
| `login.correcto` / `login.fallido` / `login.bloqueado` | Autenticación |

**Regla que gobierna ese módulo: aquí no se escriben datos personales.** Se registra quién,
cuándo, desde dónde, qué operación y sobre cuántos registros; nunca el nombre ni el número.
Un log de auditoría con los datos dentro sería una segunda copia sin cifrar de justo lo que
acabamos de cifrar. Hay una prueba que lo comprueba.

Detalles deliberados:
- La IP sale de `REMOTE_ADDR`, **no** de `X-Forwarded-For`: esa cabecera la pone el cliente y
  cualquiera podría falsear su propio rastro.
- Ni siquiera se registra el nombre del archivo subido: lo elige quien sube, y es habitual que
  lleve dentro el nombre de una persona (`altas_maria_fernandez.xlsx`).
- Se anota **después** de comprobar permisos, para que un intento rechazado no quede escrito
  igual que una consulta real.

### 2.5 Autenticación y Sesión

**Mecanismo nativo de Django:**
- Contraseña con hash PBKDF2 (el de Django), más 4 validadores de robustez
- Sesión en base de datos, cookie `HttpOnly` (+ `Secure` en producción)
- Caducidad: 30 min de inactividad y cierre al cerrar el navegador
- Token CSRF en todos los formularios
- **Segundo factor (TOTP) obligatorio en el admin** — ver 2.6

**Limitadores de intentos:**

| Limitador | Clave del contador | Umbral | Bloqueo |
|---|---|---|---|
| Login (`auth_views.py`) | par (IP, usuario) | 5 fallos | **5 minutos** → 429 |
| Alta (`views.py`) | IP | 5 solicitudes | **1 hora** → 429 |

El de login cuenta por *(IP, usuario)* y no solo por IP: así un atacante no puede bloquear la
cuenta de un tercero desde fuera, y sigue cortándose el tanteo de contraseñas.

> **Ambos guardan su contador en la caché de Django, lo que convierte al backend de caché en un
> control de seguridad.** Con la caché en memoria del proceso, cada worker lleva su propia
> cuenta y el límite de 5 se vuelve 5 por worker. Lo impide el check de despliegue
> `gestion.E001` (ver 7.1).

### 2.6 Segundo factor en el admin

El admin usa `OTPAdminSite` de django-otp: pide un código TOTP de 6 dígitos además de la
contraseña. Los sindicatos **no** lo necesitan, porque no descifran nada; exigírselo sería
coste sin contrapartida.

Enrolamiento: `manage.py activar_2fa <usuario>`. Django no trae pantalla para dar de alta el
primer dispositivo, así que sin este comando activar el 2FA equivaldría a cerrar el admin y
tirar la llave. Se ejecuta desde la consola del servidor, de modo que siempre hay vía de
vuelta. Reejecutarlo **revoca** el dispositivo anterior: si se acumularan, un teléfono perdido
seguiría dando acceso indefinidamente.

---

## 3. Flujos de Datos Críticos

### 3.1 Alta de Sindicato (Público, Sin Login)

```
Usuario (sin login)
    ↓
registro_sindicato() [GET]
    ↓ Valida IP
    └→ RegistroSindicatoForm [render]
    
Usuario completa formulario + envía
    ↓
registro_sindicato() [POST]
    └→ Incrementa contador IP en cache
    └→ Crea User (inactivo: is_active=False)
    └→ Crea PerfilSindicato (acuerdo_aceptado=False)
    └→ Audita: SINDICATO_REGISTRADO
    └→ Redirige a /login/ [con mensaje de éxito]
    
Admin revisa, activa cuenta en django-admin
    ↓
Sindicato puede loguear
```

**Validaciones:**
- Nombre de usuario único
- `nombre_identificativo` obligatorio: es la única pista con la que el administrador decide a
  quién está aprobando
- Contraseña: ≥ 8 caracteres y los 4 validadores de Django (ni común, ni solo numérica, ni
  parecida al usuario)
- Máximo 5 solicitudes por IP/hora

**El formulario no recoge correo electrónico** (`Meta.fields = ("username",)`). Consecuencias
que conviene tener presentes: no hay avisos automáticos ni recuperación de contraseña por
correo, y el administrador tiene que mirar el panel para enterarse de las solicitudes nuevas.

**Mass assignment:** `is_active`, `is_staff` e `is_superuser` no son campos del formulario, y
`save()` fuerza `is_active = False`. Aunque alguien los inyecte en el POST, se ignoran; la
cuenta nace desactivada y `ModelBackend.user_can_authenticate` le impide entrar hasta que un
administrador la apruebe.

---

### 3.2 Aceptación de Términos Legales (Autenticado)

```
Sindicato autenticado accede a /subir/
    ↓
cargar_datos_sindicato() [GET]
    └→ ¿PerfilSindicato.acuerdo_aceptado = True?
        ├─ Sí → [Renderiza formulario de subida]
        └─ No → [Redirige a acuerdo_legal()]
    
acuerdo_legal() [GET]
    └→ [Renderiza página de acuerdo + botón "Aceptar"]
    
Sindicato hace clic "Aceptar"
    ↓
acuerdo_legal() [POST]
    └→ PerfilSindicato.acuerdo_aceptado = True
    └→ PerfilSindicato.fecha_aceptacion = now()
    └→ PerfilSindicato.ip_aceptacion = request.REMOTE_ADDR
    └→ .save() [audita vía HistoricalRecords]
    └→ Redirige a /subir/
    
[Sindicato ya puede subir archivos]
```

**Trazabilidad legal:**
- IP y timestamp de aceptación grabadas
- No se puede "desaceptar"
- Cambios auditan automáticamente

---

### 3.3 Subida de Afiliados (Excel → Cifrado en BD)

```
Sindicato prepara archivo .xlsx
    ↓
POST a cargar_datos_sindicato()
    ├→ Valida: ¿imprenta? → 403 PermissionDenied
    ├→ Valida: ¿acuerdo aceptado? → redirige acuerdo_legal()
    ├→ Valida: extensión .xlsx, ≤5 MB
    ├→ Lee con pandas
    ├→ Valida columnas requeridas presentes
    ├→ Valida ≤10.000 filas
    │
    └─→ Para cada fila:
        ├─ Crea instancia Afiliado
        ├─ Valida formato (regex, tipos)
        │   ├─ Confederacion: 2 dígitos
        │   ├─ Fed_Local: 5 dígitos
        │   ├─ Num_Afiliado: 6 dígitos
        │   ├─ Nombre_Apellidos: ≤255 chars
        │   ├─ Lengua: 'A' (Castellano) o 'C' (Catalán)
        │   └─ Estado: 'ALTA' o 'BAJA'
        ├─ Si error en UNA fila → aborta TODO (transacción atómica)
        └─ Si válidas → agrega a lista
    
    ├→ TRANSACTION ATOMIC:
    │   ├─ bulk_create_with_history(afiliados_validos)
    │   │   └─ Para cada fila en Afiliado:
    │   │       └─ nombre_apellidos → CampoTextoCifrado
    │   │           └─ AES-256-GCM(plaintext, nonce_aleatorio)
    │   │           └─ Guardado: "v1$1:nonce||ciphertext"
    │   │
    │   │       └─ num_afiliado → CampoTextoCifrado [idem]
    │   │       └─ notas_historicas → CampoTextoCifrado (si presente)
    │   │
    │   │       └─ Auditoría: HistoricalRecords crea entrada
    │   │
    │   ├─ RegistroSubida.objects.create(...)
    │   │   └─ Registra: usuario, fecha, cantidad, nombre_archivo
    │   │
    │   └─ Si falla: ROLLBACK, sin cambios en BD
    │
    └─→ Audita: AFILIADOS_CARGADOS (cantidad, sin nombres)
    
[Afiliados almacenados cifrados, listos para imprenta]
```

**Garantías transaccionales:**
- "Todo o nada": si una fila falla validación, NO se guarda ni una
- Si falla la BD, no queda RegistroSubida huérfano
- Auditoría captura el estado exacto pre- y post-cambio

---

### 3.4 Panel de Imprenta (Cifrado Parcial)

```
Imprenta autenticada accede a /panel-imprenta/
    ↓
panel_imprenta() [GET]
    └→ ¿User.groups.filter(name='Imprenta').exists()?
        ├─ No → 403 PermissionDenied, audita ACCESO_DENEGADO
        └─ Sí → continúa
    
    └→ Consulta a BD:
        Afiliado.objects.filter(estado_impresion='IMPRESO')
                 .values('sindicato_codigo', 'num_afiliado', 'fecha_envio_imprenta')
        
        ├─ .values() con TRES columnas: nombre_apellidos y notas_historicas
        │   ni siquiera entran en el SELECT, así que no llegan a memoria y
        │   una plantilla no puede mostrarlos ni por descuido.
        │
        └─ num_afiliado SÍ se descifra: .values() aplica los conversores de
           campo (ValuesIterable -> results_iter -> apply_converters), así que
           CampoTextoCifrado.from_db_value se ejecuta igual que con instancias.
    
    └→ Renderiza template con:
        ├─ sindicato_codigo      ✓ visible, no personal
        ├─ num_afiliado          ✓ visible EN CLARO — es el dato que se imprime
        ├─ fecha_envio_imprenta  ✓ visible, no personal
        
    └→ Audita: LOTE_IMPRESION_CONSULTADO
        └─ Registra: usuario, cantidad de filas vistas
```

> **Precisión importante.** Es un error frecuente suponer que `.values()` devuelve el valor
> crudo de la columna: no lo hace. `ValuesIterable` llama a `compiler.results_iter()`, que
> aplica los conversores de campo, de modo que `from_db_value` se ejecuta y el número llega
> descifrado a la plantilla.
>
> Y así debe ser: la imprenta necesita el número para imprimir el carnet. **El cifrado en
> reposo protege el disco y los backups, no la pantalla de quien tiene permiso.** Ver un
> `v1$...` en el panel indicaría que falta la clave, no una medida de seguridad.
>
> La garantía real de esta vista no es que el número sea ilegible, sino que **el nombre nunca
> se consulta**. Es una propiedad estructural, no cosmética.

**Restricciones de Imprenta:**
- ✗ NO puede subir afiliados (`cargar_datos_sindicato` bloquea al grupo Imprenta con 403)
- ✗ NO ve nombres ni notas históricas (no están en el `SELECT`)
- ✗ NO ve lotes en estado PENDIENTE
- ✗ NO tiene acceso a `/admin/` (sin `is_staff`)
- ✓ Ve: código de sindicato, número de afiliado, fecha de envío
- ✓ Cada consulta queda auditada

---

## 4. Almacenamiento de Datos

### 4.1 Modelo de Base de Datos

```sql
-- Tabla principal
gestion_afiliado:
  id (PK)
  sindicato_usuario_id (FK → auth_user)
  confederacion_territorial (CharField, 2 dígitos)
  federacion_local (CharField, 5 dígitos)
  federacion_sectorial (CharField, 2 dígitos)
  sindicato_codigo (CharField, 3 dígitos)
  num_afiliado (TextField) → CIFRADO: "v1$1:nonce||ciphertext"
  nombre_apellidos (TextField) → CIFRADO: "v1$1:nonce||ciphertext"
  lengua (CharField: 'A'/'C')
  estado (CharField: 'ALTA'/'BAJA')
  notas_historicas (TextField) → CIFRADO (nullable)
  estado_impresion (CharField: 'PENDIENTE'/'IMPRESO')
  fecha_envio_imprenta (DateTimeField, nullable)
  fecha_creacion (DateTimeField, auto_now_add)

-- Auditoría (HistoricalRecords de simple-history)
simple_history_afiliado:
  history_id (PK)
  ... [TODOS los campos de gestion_afiliado + history_user_id, history_date]
  
-- Registro de subidas
gestion_registrosubida:
  id (PK)
  sindicato_id (FK → auth_user)
  fecha (DateTimeField, auto_now_add)
  cantidad_afiliados (IntegerField)
  nombre_archivo (CharField) — SIN datos personales

-- Perfiles de sindicato
gestion_perfilsindicato:
  id (PK)
  usuario_id (OneToOneField → auth_user)
  nombre_identificativo (CharField) — "CGT Rama Metal"
  acuerdo_aceptado (BooleanField)
  fecha_aceptacion (DateTimeField)
  ip_aceptacion (GenericIPAddressField)
```

### 4.2 Retención de Datos

| Tabla | Retención | Motivo | Responsable |
|-------|-----------|--------|-------------|
| gestion_afiliado | Según RGPD (consultar DPO) | Base de datos de miembros activos | Sindicato (propietario) |
| simple_history_afiliado | 2 años (configurable) | Auditoría de cambios | RGPD Art. 15 (derecho de acceso) |
| gestion_registrosubida | Indefinida | Trazabilidad de cargas | DPO, para investigaciones |
| django_admin_log | 2 años | Auditoría de admin | Seguridad, investigación |
| Logs (stdout/fichero) | 30 días (rotación diaria) | Detección de anomalías | Operaciones |

---

## 5. Control de Acceso Basado en Roles (RBAC)

### 5.1 Roles y Permisos

| Rol | Descripción | Permisos | Vistas Accesibles |
|-----|-------------|----------|------------------|
| **Sin login** | Público | ninguno | /registro/, /login/ |
| **Sindicato** (is_active=True) | Usuario sindical | read/write propios afiliados | /acuerdo/, /subir/, /notificaciones/ |
| **Sindicato** (is_active=False) | Cuenta pendiente | ninguno | /login/ (mensaje de rechazo) |
| **Imprenta** (group='Imprenta') | Cta de imprenta | read parcial (sin nombres) | /panel-imprenta/ |
| **Admin** (is_superuser=True) | Administrador | full access (CRUD) | django-admin, todas las vistas |

### 5.2 Validaciones de Acceso

**En cada vista autenticada:**

```python
@login_required
def vista(request):
    # 1. Usuario logueado?
    # 2. ¿Tiene permiso específico de rol?
    if not request.user.groups.filter(name='Imprenta').exists():
        raise PermissionDenied  # 403
    
    # 3. ¿Sus datos, o dato de otro usuario?
    # request.user.afiliados usa related_name [aislamiento automático]
```

**Aislamiento de datos:**
- Cada sindicato solo ve sus propios afiliados (via FK sindicato_usuario)
- Imprenta ve solo los marcados como IMPRESO
- Admin ve todo (con datos desencriptados si los solicita)

---

## 6. Validación de Entrada

### 6.1 Niveles de Validación

1. **Cliente (Template):** `<input type="text" maxlength="255">` — UX, no seguridad
2. **Form (Django):** `RegistroSindicatoForm` — lógica de negocio
3. **Modelo (Model):** Validadores de regex, `full_clean()` — integridad de datos
4. **BD (Database):** Constraints, tipos — último guardián

### 6.2 Validadores en Modelos

```python
confederacion_territorial = CharField(
    max_length=2,
    validators=[RegexValidator(r'^\d{2}$', 'Debe ser de 2 dígitos.')]
)
```

**Inyección SQL:** Imposible vía ORM (parametrizado automáticamente)

**Inyección en Templates:** `{{ variable }}` con escapado automático XSS

---

## 7. Configuración de Seguridad (Django Settings)

**Ningún valor sensible vive en `settings.py`.** Todo viene del entorno (`.env` en el
servidor, nunca en el repositorio). `SECRET_KEY` se lee con `os.environ['SECRET_KEY']`, sin
valor por defecto: si falta, la aplicación no arranca en vez de arrancar con una clave débil.

Variables del `.env` de producción:

```bash
DEBUG=False
ALLOWED_HOSTS=carnets.example.es

# Cifrado en reposo. Formato: id:clave_base64,id:clave_base64
# La PRIMERA cifra; las siguientes solo permiten leer lo guardado antes de rotar.
# (No es JSON: lo parsea gestion/crypto.py:_parsear_claves)
CARNETS_ENCRYPTION_KEYS=k2:kFh3...=,k1:9dPz...=

# HTTPS
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO:https   # solo si hay proxy TLS delante

# Caché COMPARTIDA: sostiene los limitadores de intentos
CACHE_BACKEND=django.core.cache.backends.redis.RedisCache
CACHE_LOCATION=redis://10.0.1.30:6379/1

# Auditoría
AUDITORIA_LOG_PATH=/var/log/carnets/auditoria.jsonl
```

### 7.1 Comprobaciones que impiden un despliegue inseguro

Estos ajustes tienen valores por defecto pensados para desarrollo local (HTTPS desactivado,
caché en memoria). Eso significa que **olvidar el `.env` produciría un servidor en producción
sirviendo por HTTP con las cookies en claro**, sin que nada fallara de forma visible.

Tres mecanismos lo impiden:

| Mecanismo | Dónde | Qué corta |
|---|---|---|
| `GestionConfig.ready()` | `gestion/apps.py` | Arrancar sin clave de cifrado |
| Check de despliegue `gestion.E001` | `gestion/checks.py` | Caché no compartida entre workers |
| `check --deploy --fail-level WARNING` | script de despliegue | HTTPS, cookies, HSTS, `SECRET_KEY` débil |

El tercero es clave: los avisos de seguridad de Django son `WARNING`, no `ERROR`, así que un
`check --deploy` a secas terminaba con éxito sobre una configuración insegura. Con
`--fail-level WARNING` un aviso detiene el despliegue igual que un error.

### 7.2 Por qué la caché es un control de seguridad

Los limitadores de intentos (login y alta) guardan su contador en la caché. Con el backend por
defecto de Django —memoria del proceso— **cada worker de gunicorn lleva su propia cuenta**: el
límite de 5 intentos se convierte en 5 × número de workers, y se reinicia en cada recarga. No
falla nada; simplemente deja de proteger. De ahí el check `gestion.E001`.

---

## 8. Logging y Monitoreo

### 8.1 Logs de Aplicación

**Archivo:** `sistema_carnets/gestion/auditoria.py`

**Acciones auditadas:**
- `SINDICATO_REGISTRADO` — nueva solicitud de alta
- `AFILIADOS_CARGADOS` — subida de lote (número, no nombres)
- `LOTE_IMPRESION_CONSULTADO` — acceso al panel de imprenta
- `ACCESO_DENEGADO` — intento de acceso sin permisos

**Ejemplo de entrada de auditoría:**
```json
{
  "timestamp": "2026-08-21T15:30:45.123Z",
  "accion": "AFILIADOS_CARGADOS",
  "usuario": "sindicato_cgt",
  "cantidad": 150,
  "ip": "203.0.113.42",
  "user_agent": "Mozilla/5.0...",
  "notas": ""
}
```

**Garantía:** No se registran nombres, números de afiliado, ni datos personales.

---

## 9. Casos de Uso de Seguridad

### 9.1 Escenario: Contraseña Comprometida

```
1. Usuario cambia contraseña en Django admin / formulario
2. New hash se almacena con PBKDF2
3. Sesión actual se invalida (CSRF token)
4. Próximo login requiere nueva contraseña
5. Auditoría registra el cambio
→ Datos personales NO están en riesgo (están cifrados)
```

### 9.2 Escenario: Acceso a BD Comprometido

```
SELECT nombre_apellidos FROM gestion_afiliado LIMIT 1;
→ "v1$1:Uc3Dq2mP+9xL5kJ==||aBcDeFg..."
→ Sin la clave de CARNETS_ENCRYPTION_KEYS, ilegible
→ GCM detecta si alguien lo modifica
```

### 9.3 Escenario: el administrador consulta un afiliado

```
1. Admin entra a /admin/ con contraseña + código TOTP de 6 dígitos
   └─ Sin el segundo factor, OTPAdminSite rechaza el acceso
2. Hace clic en un Afiliado
3. El formulario descifra nombre_apellidos y num_afiliado en memoria
4. Los ve en pantalla (no se persisten, no se escriben en ningún log)
5. Cierra la pestaña
→ La auditoría SÍ registra el acceso: afiliado.abierto, con usuario, IP y PK
→ Lo que NO registra es el contenido: ni nombre ni número entran en el log
```

**Esta es la vía de exposición más ancha del sistema, y por eso es la única con 2FA.** Todo lo
demás está construido para no poder ver estos datos; el admin sí puede, por necesidad.

### 9.3.bis Escenario: contraseña de administrador robada

```
1. Atacante obtiene usuario y contraseña válidos del admin
2. Intenta entrar en /admin/
3. Se le pide "Token OTP" → no lo tiene
4. Acceso denegado
→ La credencial por sí sola ya no basta: hace falta el dispositivo físico
→ Los intentos quedan registrados (login.fallido / login.bloqueado)
→ Con 3 bloqueos en una hora, `revisar_auditoria` envía un aviso por correo
```

Antes del segundo factor, este escenario terminaba con el archivo completo de afiliación
sindical en manos del atacante.

### 9.4 Escenario: Robo de Sesión Cookie

```
1. Atacante roba cookie de sesión
2. Lo intenta usar en IP/navegador distinto
3. Django/navegador detecta CSRF token falta
4. Petición rechazada (403)
→ Defensa en profundidad: incluso sin token,
   el usuario no puede hacer cambios
```

---

## 10. Compliance Normativo

### 10.1 RGPD (Reglamento General de Protección de Datos)

| Artículo | Implementación |
|----------|----------------|
| Art. 5(1)(a) Legalidad | Formulario solicita consentimiento explícito (acuerdo_aceptado) |
| Art. 5(1)(f) Integridad | Encriptación AES-256-GCM + auditoría con HistoricalRecords |
| Art. 9 Datos especiales | Categoría especial (afiliación sindical); cifrado obligatorio |
| Art. 15 Derecho de acceso | HistoricalRecords permite auditoria de lo que el usuario vio |
| Art. 17 Derecho al olvido | Sindicatos pueden solicitar eliminación (admin lo ejecuta, audita) |
| Art. 32 Seguridad técnica | Encriptación, autenticación, limitadores, logging |

### 10.2 Auditoría Responsable de Datos (DPO)

El DPO debe revisar:
- Política de retención (cuánto tiempo conservar auditoría)
- Copias de seguridad (¿cifradas? ¿dónde se almacenan?)
- Testigos de acceso a datos sensibles (¿quién vio qué)
- Incidentes de seguridad (plantilla de notificación)

---

## 11. Guía de Despliegue Seguro

### 11.1 Antes de Producción

```bash
# 1. Activar modo seguro
export DEBUG=False
export ALLOWED_HOSTS="tu-dominio.es,www.tu-dominio.es"

# 2. Generar SECRET_KEY fuerte (no commitear en git)
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 3. Generar claves de cifrado (256 bits, en hexadecimal)
python -c "import secrets; print(secrets.token_hex(32))"

# 4. Almacenar en .env (gitignored)
SECRET_KEY=...
CARNETS_ENCRYPTION_KEYS=k2:CLAVE_NUEVA_BASE64=,k1:CLAVE_ANTERIOR_BASE64=

# 5. Migrar BD
python manage.py migrate

# 6. Crear superusuario
python manage.py createsuperuser

# 7. Ejecutar pruebas de seguridad
pytest tests/ -v
ruff check .
bandit -r . -c pyproject.toml

# 8. Habilitar HTTPS (certificado Let's Encrypt)
# Usar gunicorn + nginx
```

### 11.2 Stack Recomendado (Producción)

```
Internet
   ↓
[nginx] — proxy inverso, HTTPS/SSL, cache estática
   ↓
[gunicorn] × N — app workers (multithread)
   ↓
[PostgreSQL 14+] — BD con replicación
   ↓
[Redis] — caché + sessions (persistencia entre reinicios)
   ↓
[Backup diario] — encrypted, en EU (RGPD)
```

---

## 12. Referencias

- **Django Security:** https://docs.djangoproject.com/en/5.2/topics/security/
- **cryptography.io:** https://cryptography.io/en/latest/
- **RGPD Art. 9:** https://gdpr-info.eu/art-9-gdpr/
- **OWASP Top 10:** https://owasp.org/www-project-top-ten/
