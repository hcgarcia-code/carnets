# EVALUACIÓN DE IMPACTO EN PROTECCIÓN DE DATOS (EIPD)
## Sistema de Altas y Gestión de Carnets de Afiliación Sindical

**Conforme a**: Reglamento (UE) 2016/679 (RGPD), Art. 35  
**Versión**: 1.0  
**Fecha**: 2026-08-21  
**Titular de los datos**: CGT (Confederación General del Trabajo)  
**Responsable del tratamiento**: [Nombre del responsable legal]  
**Encargado del tratamiento**: [Si aplica: proveedor cloud/hosting]  

---

## RESUMEN EJECUTIVO

Esta EIPD evalúa el tratamiento de **datos de afiliación sindical** (categoría especial por Art. 9 RGPD) en el Sistema de Carnets. El tratamiento es **necesario** para la gestión de afiliación y emisión de carnets sindicales, e incluye medidas de seguridad técnicas y organizativas proporcionales al riesgo.

**Conclusión**: Con las medidas técnicas implementadas (cifrado en tránsito, validación de entrada, rate limiting, auditoría) y las medidas organizativas descritas en esta EIPD (política de retención, acceso basado en rol, capacitación), los riesgos se reducen a un nivel aceptable.

**Recomendación**: Proceder con el tratamiento, sujeto a implementación de mejoras de seguridad fase v2.0 (cifrado en reposo, KMS, auditoría inmutable centralizada).

---

## 1. DESCRIPCIÓN DEL TRATAMIENTO

### 1.1 Contexto y Finalidad
El Sistema de Carnets es una aplicación web que gestiona solicitudes de afiliación sindical y la emisión de carnets de miembro. Permite a los sindicatos locales:
- Cargar listas de afiliados (vía Excel)
- Registrar datos personales de solicitantes
- Marcar afiliados como listos para imprenta
- Recibir notificaciones cuando sus carnets están lista

### 1.2 Datos Personales Tratados (Art. 9 RGPD — Categoría Especial)

| Campo | Naturaleza | Ejemplo | Categoría | Retención |
|---|---|---|---|---|
| **Nombre y apellidos** | Identificador directo | "Juan García López" | Especial (afiliación) | 3 años post-cancelación |
| **Nº de afiliado** | Identificador único sindical | "123456" | Especial (afiliación) | 3 años post-cancelación |
| **Confederación territorial** | Código administrativo | "28" (Madrid) | Especial (afiliado a CGT) | 3 años post-cancelación |
| **Federación sectorial** | Sector laboral | "02" (Educación) | Especial (profesión) | 3 años post-cancelación |
| **Lengua** | Idioma de emisión del carnet | "C" (Catalán) | Datos personales | 3 años post-cancelación |
| **Estado afiliación** | Alta/Baja | "ALTA" | Especial (afiliación) | 3 años post-cancelación |
| **Fecha de expedición** | Cuando se emitió el carnet | "01/08/2026" | Datos personales | 3 años post-cancelación |
| **IP de solicitud** | Consentimiento RGPD | "203.0.113.45" | Datos personales | 1 año |
| **Fecha de consentimiento** | Firma del acuerdo legal | "21/08/2026 14:32" | Datos personales | 3 años (legal hold) |
| **Datos de contacto sindicato** | Email de notificación | "sindicalista@cgt.es" | Datos personales | Durante afiliación |

**Total de registros**: ~3.024 afiliados (estimado, actualizándose mensualmente)  
**Categoría de datos**: Art. 9 RGPD (afiliación sindical es categoría especial)

### 1.3 Categorías de Interesados
1. **Afiliados**: trabajadores/as solicitantes de carnet
2. **Administradores sindicales**: usuarios que suben listas de afiliados y gestionan carnets
3. **Equipo de CGT**: personal que audita, resuelve conflictos, genera reportes

### 1.4 Duración del Tratamiento
- **Ciclo corto**: solicitud → validación → imprenta → entrega (~1-2 meses)
- **Ciclo largo**: datos viven 3 años post-cancelación (legal hold para auditoría y resolución de conflictos laborales)

---

## 2. BASE LEGAL Y NECESIDAD (Art. 6 + Art. 9 RGPD)

### 2.1 Legitimidad (Art. 6)
El tratamiento se basa en:
- **Art. 6.1.c RGPD**: cumplimiento de obligación legal (registro de afiliados sindicales, trazabilidad RGPD)
- **Art. 6.1.a RGPD**: consentimiento expreso del interesado (firma digital del acuerdo RGPD antes de subir datos)

### 2.2 Excepción de Datos de Categoría Especial (Art. 9.2.c + 9.2.d)
El tratamiento de afiliación sindical está permitido bajo:
- **Art. 9.2.c RGPD**: "el que se realice por las organizaciones y asociaciones que se ocupen de política, filosofía, religión o sindicatos"
- **Art. 9.2.d RGPD**: se aplican garantías adecuadas (ver sección 4: medidas de seguridad)

### 2.3 Proporcionalidad
Los datos recogidos son los **mínimos necesarios** para la finalidad:
- Nombre/apellidos: identificación del solicitante ✓
- Nº afiliado: identificador único sindical (obligatorio por normativa sindical) ✓
- Confederación/Federación: obligatorio para emisión del carnet (código de seguridad impreso) ✓
- Lengua: para emisión en idioma correcto ✓
- Estado (Alta/Baja): obligatorio para registro de afiliación ✓
- Fecha expedición: obligatorio en el carnet impreso ✓

**Datos NO recogidos** (por proporcionalidad):
- DNI/Pasaporte (no necesario, solo nº afiliado)
- Datos bancarios (pago manejado por sindicatos locales, fuera de scope)
- Historial laboral (fuera de scope)
- Datos de menores (no aplica)

---

## 3. EVALUACIÓN DE RIESGOS

### 3.1 Matriz de Riesgos (Probabilidad × Impacto)

| Riesgo | Escenario | Probabilidad | Impacto | Severidad | Medida Actual | Medida v2.0 |
|---|---|---|---|---|---|---|
| **Inyección SQL** | Atacante manipula Excel para inyectar SQL | Baja (ORM parametrizado) | Crítico (acceso a BD) | ALTO | ✓ ORM + validación | ✓ Continúa |
| **Fuerza bruta login** | Atacante prueba múltiples contraseñas | Media (común) | Medio (acceso a datos de 1 sindicato) | ALTO | ✓ Rate limiting (5 int./5 min) | ✓ + MFA opcional |
| **Cifrado en tránsito débil** | MITM intercepta datos de solicitud | Media (sin HTTPS) | Crítico (lectura datos) | CRÍTICO | Parcial (HSTS local) | ✓ TLS 1.3 + HSTS preload |
| **Cifrado en reposo débil** | Robo de servidor/backup expone BD | Media-Baja (servidor hosting) | Crítico (3024 afiliados legibles) | CRÍTICO | ✗ NO IMPLEMENTADO | ✓ AES-256 + KMS |
| **Acceso horizontal (IDOR)** | Usuario A accede a afiliados de sindicato B | Baja (queries scoped) | Crítico (violación confidencialidad) | CRÍTICO | ✓ FK + scoped queries | ✓ Continúa |
| **Manipulación de auditoría** | DBA borra registro de acceso para encubrir robo | Baja-Media (insider threat) | Crítico (destrucción de pruebas) | CRÍTICO | Parcial (SimpleHistory en BD) | ✓ Logs append-only externos |
| **Pérdida de datos** | Fallo HW sin backup | Media-Baja | Crítico (pérdida total) | ALTO | ✗ Desconocido | ✓ S3 + versionado |
| **Desbordamiento de memoria/DoS** | Atacante sube Excel de 100k filas | Baja (límite 10k filas) | Medio (servidor caído) | MEDIO | ✓ Límite 10k + 5 MB | ✓ Continúa |
| **Desclasificación accidental** | Admin sindicato exporta datos a email inseguro | Media | Crítico (datos filtrados) | CRÍTICO | ✗ Desconocido | ✓ DLP policies + capacitación |
| **Robo de sesión (cookie)** | Atacante roba cookie de navegador del admin | Baja-Media (HttpOnly + Secure) | Alto (acceso temporal) | ALTO | ✓ HttpOnly + Secure (via .env) | ✓ + SameSite=Strict |
| **Vulnerabilidad software** | 0-day en Django/pandas/openpyxl | Baja | Crítico (acceso código) | BAJO-MEDIO | ✓ Dependencias actuales | ✓ + SAST/DAST |
| **Exposición de secretos en code** | SECRET_KEY/API keys hardcodeados | Baja | Crítico | CRÍTICO | ✓ Todos en .env | ✓ Continúa |
| **Phishing + credenciales débiles** | Admin recibe email fake, da contraseña | Media-Alta | Alto | ALTO | Parcial (política contraseña) | ✓ + MFA + capacitación |

### 3.2 Riesgos Específicos por Rol

#### Riesgo para Afiliados
- **Confidencialidad**: datos de afiliación filtrados a empleador (represalias laborales)
- **Integridad**: modificación de estado (Alta → Baja) sin autorización
- **Disponibilidad**: no poder acceder a su propio expediente (DSAR)

#### Riesgo para Sindicatos Locales
- **Confidencialidad**: datos de otros sindicatos expuestos
- **Integridad**: pérdida de registros de solicitudes presentadas
- **Disponibilidad**: no poder emitir carnets cuando sistema está caído

#### Riesgo para CGT (Responsable)
- **Reputacional**: brecha publicada → pérdida de confianza de afiliados
- **Legal**: sanciones RGPD (€20M o 4% ingresos), proceso judicial de afiliados
- **Operacional**: costo de notificación, remediación, auditoría externa

---

## 4. MEDIDAS TÉCNICAS Y ORGANIZATIVAS

### 4.1 Medidas Técnicas Implementadas (v1.0)

#### Seguridad de Datos
- ✓ **Validación de entrada**: extensión archivo (.xlsx), tamaño (5 MB), filas (<10k), regex validators
- ✓ **ORM parametrizado**: 0 SQL raw, todas las queries via Django ORM
- ✓ **Transacciones atómicas**: Excel todo-o-nada (si 1 fila falla, nada se guarda)
- ✓ **Auditoría**: SimpleHistory registra cada cambio (usuario, fecha, delta)

#### Autenticación y Autorización
- ✓ **Autenticación Django**: usuario + contraseña con validación de fuerza
- ✓ **Rate limiting**: 5 intentos fallidos → 429 (bloqueo 5 min por IP+usuario)
- ✓ **Autorización basada en rol**: cada sindicato solo ve sus afiliados (FK scoped)
- ✓ **Sin IDOR**: vistas nunca aceptan ID desde URL/POST, usan `request.user`

#### Protección en Tránsito
- ✓ **Cookies HttpOnly**: no accesibles a JavaScript
- ✓ **CSRF tokens**: en todos los formularios POST
- ✓ **HSTS** configurable (desactivado local, activable HTTPS en .env)
- ✗ **TLS 1.3 obligatorio**: pendiente (debe configurarse en reverse proxy/servidor)

#### Control de Recursos
- ✓ **Límite de tamaño request**: middleware rechaza >10 MB (413)
- ✓ **Límite de filas**: máximo 10k por Excel
- ✓ **Timeout de sesión**: 30 minutos de inactividad (configurable)

#### Gestión de Secretos
- ✓ **Variables de entorno**: SECRET_KEY, EMAIL_PASSWORD, DATABASE_NAME cargados desde .env
- ✓ **.gitignore**: .env y __pycache__ desatrackeados de git

### 4.2 Medidas Técnicas Planificadas (v2.0)

| Medida | Descripción | Timeline |
|---|---|---|
| **Cifrado en reposo (AES-256)** | Campos sensibles (nombre, nº afiliado, direcciones) cifrados con django-cryptography | Fase 2 (3-4 sem) |
| **KMS externo** | Claves de cifrado en AWS KMS / Azure Key Vault, no en código | Fase 2 (2-3 sem) |
| **PostgreSQL en VPC** | Base de datos en subred privada, sin IP pública | Fase 3 (2-3 sem) |
| **Auditoría centralizada** | Logs en Splunk/ELK/CloudWatch, append-only, retención 2 años | Fase 3 (2-3 sem) |
| **Seudonimización** | UUID interno + nº afiliado cifrado, desvinculación en queries | Fase 2 (2 sem) |
| **Backups cifrados** | S3 + SSE-KMS, versionado, Glacier después 90 días | Fase 5 (1 sem) |
| **TLS 1.3 + HSTS preload** | Cifrado tránsito obligatorio + preload de navegadores | Fase 4 (1 sem) |
| **Pen testing externo** | Auditoría caja gris: inyección, IDOR, bypass autenticación | Fase 4 (2 sem) |
| **MFA opcional** | TOTP/SMS para admin sindicatos si desean | Fase 4 (1 sem) |

### 4.3 Medidas Organizativas

#### Políticas y Procedimientos
- **Política de Retención** (sección 5): datos de afiliados 3 años post-baja, logs 2 años
- **Política de Acceso**: solo admin sindicatos (creados por CGT central) y superusuarios CGT
- **Política de Cambios**: cambios en código requieren revisión pre-deployment (SAST/tests)
- **Plan de Respuesta a Incidentes**: procedimiento de notificación en 72h a APD si brecha

#### Control de Acceso Físico y Lógico
- **Hosting seguro**: actualmente PythonAnywhere (requiere revisión de infraestructura en v2.0)
- **Acceso a servidor**: SSH keys + MFA para admin (requiere Bastion en v2.0)
- **Acceso a BD**: no hay acceso directo desde office (requiere VPN + Bastion en v2.0)

#### Capacitación y Conciencia
- **Capacitación RGPD**: todos los usuarios de sindicatos reciben guía de seguridad antes de usar sistema
- **Capacitación admin CGT**: responsable técnico entrenado en gestión de secretos, KMS, backups
- **NDA**: usuarios sindicatos firman acuerdo de confidencialidad

#### Gestión de Incidentes
- **Detección**: alertas automáticas de fallos, errores de aplicación
- **Contención**: procedimiento de rollback de cambios, aislamiento de acceso
- **Notificación**: 72h máximo para notificar a APD (Art. 33 RGPD)
- **Remediación**: parche + redeployment + auditoría post-incident

#### Subprocesadores (Art. 28 RGPD)
- **Proveedor hosting**: PythonAnywhere (requiere DPA firmado)
  - Acceso a BD: restringido a acceso de app (sin acceso manual)
  - Backups: terceros (requiere cifrado + cláusula de confidencialidad)
- **Proveedor email**: SMTP de CGT (interno)

---

## 5. DERECHOS DE LOS INTERESADOS (Art. 12-22 RGPD)

### 5.1 Derecho de Acceso (Art. 15)
**Implementación**: El sistema permite que cada afiliado (via su sindicato local) acceda a sus datos
- **Cómo**: formulario DSAR (Data Subject Access Request) dirigido a CGT
- **Plazo**: 30 días desde solicitud
- **Formato**: archivo exportable (CSV/PDF con datos personales del solicitante)

### 5.2 Derecho de Rectificación (Art. 16)
- **Implementación**: formulario de corrección de datos en sistema (o vía CGT)
- **Quién**: afiliado o admin sindicato con consentimiento
- **Auditoría**: cada cambio registrado con usuario y timestamp

### 5.3 Derecho al Olvido (Art. 17)
- **Aplicable cuando**: afiliado solicita baja + han pasado 3 años post-baja (retención legal vencida)
- **Implementación**: tarea de anonimización/borrado programada (nombre → "ANONIMIZADO", afiliado → NULL, etc)
- **Excepciones**: datos conservados por legal hold (litigios laborales) o cumplimiento ley

### 5.4 Derecho a Limitar el Tratamiento (Art. 18)
- **Implementación**: si hay disputa sobre precisión, afiliado puede solicitar bloqueo temporal
- **Procedimiento**: CGT revisa disputa, marca registro como "en disputa" (no se procesa hasta resolución)

### 5.5 Derecho a la Portabilidad (Art. 20)
- **Aplicable para**: datos proporcionados por afiliado (nombre, estado, etc)
- **Formato**: JSON/CSV estructurado
- **Plazo**: 30 días

### 5.6 Derecho de Oposición (Art. 21)
- **Aplicable para**: si en futuro CGT usa datos para marketing (actualmente NO aplica)
- **Procedimiento**: afiliado puede oponerme a cualquier nuevo uso de datos

### 5.7 Decisiones Automatizadas e Información
- **Actual**: NO hay decisiones automatizadas (todos los cambios de estado requieren acción manual)
- **Transparencia**: aviso legal describe qué datos se recogen y para qué

---

## 6. POLÍTICA DE RETENCIÓN Y EXPURGADO

### 6.1 Tabla de Retención

| Datos | Finalidad | Periodo Retención | Fundamento Legal | Acción post-plazo |
|---|---|---|---|---|
| **Afiliado (nombre, nº, confederación)** | Gestión carnet + auditoría laboral | 3 años post-baja | Legal hold (resolución conflictos laborales) | Anonimizar |
| **Estado impresión (PENDIENTE/IMPRESO)** | Trazabilidad | Mientras activo + 3 años | Legal hold | Anonimizar |
| **Fecha expedición** | Validación carnet | Mientras activo + 3 años | Legal hold | Anonimizar |
| **IP consentimiento RGPD** | Prueba de consentimiento | 3 años | Legal hold (defensa en brecha) | Borrar |
| **Log de auditoría (SimpleHistory)** | Trazabilidad cambios | 2 años | Ley de Auditoría interna | Archivar en cold storage |
| **Email admin sindicato** | Notificaciones operativas | Mientras uso activo | Necesario para servicio | Anonimizar en baja |
| **Backup de BD** | Recuperación ante desastre | 30 días versión actual + 1 año Glacier | Continuidad operacional | Destruir cifrado |

### 6.2 Procedimiento de Expurgado
**Tarea cron trimestral** (no implementada en v1.0, TODO v2.0):
```
SELECT * FROM Afiliado WHERE estado='BAJA' AND fecha_cancelacion < (NOW() - INTERVAL 3 YEAR)
  → Anonimizar: nombre_apellidos='ANONIMIZADO', num_afiliado=NULL
  → Marcar como "expurgado": expurgado_en=NOW()
```

**Auditoría**: cada expurgado registrado en log de auditoría con usuario y razón.

---

## 7. TRANSFERENCIAS DE DATOS

### 7.1 Transferencias Internas
- **Dentro de CGT**: datos de afiliados compartidos entre estructura central y federaciones (necesario para auditoría)
  - **Medida**: acceso basado en rol, cada federación solo ve sus afiliados
  - **Contrato**: no requiere por ser mismo responsable de datos

### 7.2 Transferencias Internacionales (Fuera UE)
- **No aplica**: sistema alojado en UE (PythonAnywhere), datos NO se transfieren fuera UE
- **Nota**: si en futuro se usa servidor fuera UE → requiere Decisión de Adecuación u otro mecanismo legal (Cláusulas Tipo Contractuales, Vinculante Corp Rules)

### 7.3 Subprocesadores
- **Hosting**: PythonAnywhere (proveedor UK, post-Brexit requiere DPA + Standard Contractual Clauses)
- **Email SMTP**: CGT interno (no subprocesador)
- **Futuros**: si se añade Splunk/KMS externo → DPA y garantías de confidencialidad

---

## 8. CONSULTA CON LA AUTORIDAD DE PROTECCIÓN DE DATOS

### 8.1 ¿Se Requiere EIPD?
Sí, conforme a Art. 35.4 RGPD: el tratamiento de datos de **categoría especial a gran escala** requiere EIPD obligatoria.

### 8.2 ¿Se Requiere Consulta Previa a APD?
**Según Art. 36 RGPD**, se requiere consulta previa si la EIPD indica riesgos altos y las medidas propuestas no los mitigan suficientemente.

**En este caso**: NO hay consulta previa si se implementan **TODAS las medidas v2.0** (cifrado, KMS, auditoría centralizada). Con medidas reducidas (solo v1.0), se recomienda consultar.

**Recomendación**: Consultar voluntariamente con APD (p. ej. Aepd en España) antes de v2.0 en producción, presentando esta EIPD + plan de implementación.

---

## 9. EVALUACIÓN DE IMPACTO RESIDUAL (Después de Medidas)

### 9.1 Riesgos Residuales

| Riesgo | Nivel v1.0 | Nivel v2.0 | Aceptabilidad |
|---|---|---|---|
| Inyección SQL | Bajo | Bajo | ✓ Aceptable |
| Fuerza bruta login | Medio | Bajo | ✓ Aceptable (+ MFA) |
| IDOR | Bajo | Bajo | ✓ Aceptable |
| Brecha en tránsito (MITM) | Medio | Bajo | ✓ Aceptable (TLS 1.3) |
| **Brecha en reposo** | **ALTO** | **BAJO** | ✗→✓ (v2.0 lo reduce) |
| **Manipulación auditoría** | **MEDIO** | **BAJO** | ✗→✓ (logs centralizados) |
| Insider threat (DBA) | Medio | Bajo | ✓ Aceptable (menor privilegio) |
| Pérdida de datos | Medio | Bajo | ✓ Aceptable (backups) |

### 9.2 Análisis Costo-Beneficio
- **Costo implementación v2.0**: ~16 semanas dev + hosting KMS/PostgreSQL (~€500-1000/mes)
- **Costo potencial brecha**: €20M sanción RGPD + costos legales + remediación + reputacional
- **ROI**: claro — inversión pequeña vs. riesgo catastrófico

---

## 10. CONCLUSIÓN Y RECOMENDACIONES

### 10.1 Estado de Conformidad

| Aspecto | v1.0 | v2.0 Planificada |
|---|---|---|
| **Base legal (Art. 6+9)** | ✓ Cumple | ✓ Cumple |
| **Necesidad y proporcionalidad** | ✓ Cumple | ✓ Cumple |
| **Seguridad en tránsito** | Parcial | ✓ Cumple (TLS 1.3) |
| **Seguridad en reposo** | ✗ Incumple | ✓ Cumple (AES-256+KMS) |
| **Auditoría inmutable** | Parcial | ✓ Cumple (logs centralizados) |
| **Derechos interesados** | Parcial | ✓ Cumple |
| **Retención** | Documentada (esta EIPD) | ✓ Implementada |

**Veredicto v1.0**: Cumplimiento parcial, riesgos aceptables si se implementan medidas v2.0 en 2026 Q4.  
**Veredicto v2.0**: Cumplimiento completo Art. 35 RGPD.

### 10.2 Recomendaciones Prioritarias

#### Corto Plazo (Ahora)
1. ✓ **Adoptar esta EIPD** como documento de defensa legal
2. ✓ **Comunicar a afiliados** qué datos se recogen y para qué (mediante aviso legal en UI)
3. ✓ **Documentar procedimiento de brecha**: cómo notificar APD en 72h
4. ✓ **Capacitar admin sindicatos** en seguridad (contraseñas fuertes, no compartir credenciales)

#### Mediano Plazo (Q4 2026 o antes)
1. ✓ **Implementar medidas v2.0** (cifrado reposo, KMS, PostgreSQL, auditoría centralizada)
2. ✓ **Auditoría externa** (pen test + DAST) antes de despliegue producción
3. ✓ **Consultar con APD** (voluntario pero recomendado) presentando EIPD + plan implementación
4. ✓ **Firmar DPA con PythonAnywhere** si no existe

#### Operacional (Continuo)
1. ✓ **Monitoreo continuo**: alertas de fallos, intentos de acceso no autorizados
2. ✓ **Parches de seguridad**: actualizar Django, pandas, openpyxl mensualmente
3. ✓ **Rotación de credenciales**: cambiar SECRET_KEY cada año, passwords cada 90 días
4. ✓ **Respuesta a incidentes**: plan documentado, equipo capacitado

### 10.3 Firmantes

| Rol | Nombre | Firma | Fecha |
|---|---|---|---|
| Responsable de Protección de Datos (DPO) | [Nombre] | _____ | 2026-08-21 |
| Responsable del Tratamiento (CGT) | [Nombre] | _____ | 2026-08-21 |
| Responsable Técnico (CTO/Dev Lead) | [Nombre] | _____ | 2026-08-21 |

---

## ANEXOS

### Anexo A: Registro de Cambios en la EIPD
Cada revisión de esta EIPD se registrará aquí:

| Versión | Fecha | Cambios | Autor |
|---|---|---|---|
| 1.0 | 2026-08-21 | EIPD inicial, estado v1.0 + roadmap v2.0 | [Autor] |

### Anexo B: Referencias Legales
- Reglamento (UE) 2016/679 — RGPD
- Directiva (UE) 2016/680 — Protección datos ley enforcement
- Ley Orgánica 3/2018 (LOPDGDD) — implementación RGPD en España
- Ley de Convenios Colectivos — retención datos afiliados sindicales
- ISO 27001 — gestión seguridad información (referencia)

### Anexo C: Modelo de Notificación de Brecha
[Plantilla para notificar a APD en 72h si ocurre brecha]

```
Asunto: Notificación de Brecha de Seguridad — Sistema Carnets (Art. 33 RGPD)

Autoridad de Protección de Datos:

La entidad [CGT] notifica una brecha de seguridad detectada el [FECHA] en su sistema 
[Sistema Carnets]. La brecha afecta a [N] registros de afiliados.

Naturaleza: [SQL injection | Unauthorized access | Data theft | etc]
Datos afectados: [nombres, nºs afiliados, confederaciones]
Medidas adoptadas: [immediate containment actions]
Resultados: [número final registros comprometidos, si se conoce]

Información de contacto: [DPO email/teléfono]
```

---

**FIN DE LA EIPD**

*Este documento debe revisarse anualmente o cuando haya cambios significativos en el tratamiento (nuevos datos, nuevas finalidades, cambios de infraestructura, etc).*
