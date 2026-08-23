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
1. Sindicato accede a /registro/ y solicita alta
   ├─ Se crea User (is_active=False)
   ├─ Se crea PerfilSindicato (acuerdo_aceptado=False)
   └─ Se audita: SINDICATO_REGISTRADO

2. Admin revisa en django-admin → Users
   ├─ Busca el usuario nuevo
   ├─ Revisa "Información del sindicato" (nombre_identificativo)
   │   [Es la única pista: "CGT Rama Metal Barcelona", "UGT Sector Educación", etc.]
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
  Acuerdo aceptado: [☑ / ☐]
  Fecha aceptación: 2026-08-15 14:30:45
  IP aceptación: 203.0.113.42
```

**Qué puedes cambiar:**
- `Nombre identificativo` — si el sindicato lo solicita, actualizar
- `Activo` — marcar/desmarcar para activar/bloquear

**Qué NO debes cambiar:**
- `Acuerdo aceptado` — registra voluntad del usuario, no lo falsees
- Fechas/IPs — auditoría inmutable

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

### 4.4 Eliminar Afiliado

**Antes de eliminar:**
1. Revisa la auditoría en `HistoricalRecords`
2. Confirma que el sindicato lo solicita (hay un ticket)
3. Documenta el motivo

**Proceso:**
```
1. Admin selecciona afiliado
2. Botón "Eliminar"
3. Confirma
4. El afiliado se elimina (pero HistoricalRecords lo conserva)
5. Auditoría registra: AFILIADO_ELIMINADO, usuario, IP, motivo
```

**Garantía:** Incluso después de eliminar, el historial de cambios queda íntegro.

---

## 5. Auditoría e Investigación

### 5.1 Ver el Historial de Cambios

**Ruta:** `/admin/simple_history_afiliado/`

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
- **Nombre Archivo:** Sin datos personales (el usuario elige el nombre)

**Nota:** El nombre del archivo NO se logea (el usuario podría poner "maria_fernandez.xlsx" y eso sería personal).

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

**Aquí nunca hay datos personales.** Se registra quién, cuándo, desde dónde, qué operación y
sobre cuántos registros; nunca el nombre ni el número de afiliado. Un registro de auditoría
con los datos dentro sería una segunda copia sin cifrar de justo lo que se acaba de cifrar.

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

3. Acciones:
   django-admin → Users → Edita usuario
   - Botón "Establecer contraseña":
     [Fuerza reset, sindicato recibe email con enlace temporal]

4. Auditar:
   Crear entrada manual en logs:
   "INCIDENTE: acceso_no_autorizado usuario=X motivo=Y accion=reset_password"
```

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
   - Activar 2FA si está disponible

4. Notificar:
   - DPO (Delegado de Protección de Datos)
   - AEPD si es grave (>2% de usuarios)
   - Sindicatos afectados (plazo 72h)
```

### 8.3 Incident: Afiliado Solicita "Derecho al Olvido"

Un afiliado solicita que se eliminen sus datos (RGPD Art. 17).

```
1. Verificar solicitud:
   - Email auténtico del afiliado
   - Confirmar que es sindicalista de ese sindicato

2. Coordinación:
   - Contactar al sindicato propietario de los datos
   - Sindicato solicita a admin que elimine

3. Eliminación:
   admin@sistema → Django-admin → Afiliado
   - Busca afiliado por nombre/número
   - Botón "Eliminar"
   - Confirma: "Sí, estoy seguro"
   - Sistema audita: AFILIADO_ELIMINADO, motivo=derecho_al_olvido

4. Verificación:
   - Confirmar que no aparece en búsquedas
   - HistoricalRecords lo conserva (para auditoría legal)
```

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

- [ ] Revisar incidentes del trimestre
- [ ] **Comprobar que el segundo factor del admin sigue funcionando** (entra y sal; si has
      cambiado de teléfono sin reejecutar `activar_2fa`, te enterarás ahora y no en una urgencia)
- [ ] Verificar capacidad de almacenamiento (logs, BD)
- [ ] Repasar que CI sigue en verde en GitHub Actions

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

**Última revisión:** 2026-08-21
**Versión:** 1.0
