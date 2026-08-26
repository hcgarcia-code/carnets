# EVALUACIÓN DE IMPACTO EN PROTECCIÓN DE DATOS (EIPD)
## Sistema de Altas y Gestión de Carnets de Afiliación Sindical

**Conforme a**: Reglamento (UE) 2016/679 (RGPD), Art. 35  
**Versión**: 1.2  
**Fecha**: 2026-08-26 (v1.0: 2026-08-21)  
**Responsables del tratamiento**: los sindicatos de rama y de provincia, cada uno respecto de sus personas afiliadas  
**Encargado del tratamiento**: CGT Confederal, exclusivamente para la confección del carnet  
**Subencargados**: empresa de impresión · proveedor de alojamiento · proveedor de custodia de claves  

**Elaborada por** CGT Confederal en su condición de encargado, en cumplimiento del deber de asistencia del Art. 28.3.f, **para su adopción por cada sindicato responsable**.

---

## NOTA PRELIMINAR: QUIÉN ES QUIÉN

Esta EIPD, en sus versiones 1.0 y 1.1, atribuía a CGT Confederal la condición de responsable del tratamiento. **Es incorrecto**, y la corrección afecta a la estructura entera del cumplimiento, no a un párrafo.

**Los datos no los recaba CGT Confederal.** Los recaban los **sindicatos de rama y de provincia**, que son entidades con personalidad jurídica propia, en el momento de la afiliación y en el marco de la relación asociativa que cada persona mantiene con su sindicato. Esos sindicatos los trasladan a CGT Confederal **con una finalidad única y acotada: la confección del carnet**.

De ahí se sigue el reparto de papeles:

| Quién | Papel | Por qué |
|---|---|---|
| **Sindicato de rama o provincia** | **Responsable del tratamiento** (Art. 4.7) | Recaba los datos, mantiene la relación asociativa con la persona afiliada y decide el porqué del tratamiento |
| **CGT Confederal** | **Encargado del tratamiento** (Art. 4.8) | Trata los datos **por cuenta** de los sindicatos y solo para confeccionar el carnet. No los recaba, no decide la finalidad y no puede darles otro uso |
| **Empresa de impresión** | **Subencargada** (Art. 28.4) | Contratada por CGT Confederal para ejecutar parte del encargo |
| **Proveedores de alojamiento y de claves** | **Subencargados** (Art. 28.4) | Igual |

**Consecuencias prácticas de esta calificación**, que recorren todo el documento:

1. **Quien informa a la persona afiliada es su sindicato**, no CGT Confederal, y aplica el **Art. 13** (datos obtenidos del propio interesado), no el Art. 14. Corrige lo que decía la v1.1.
2. **Los derechos se ejercen ante el sindicato.** Si una persona se dirige a CGT Confederal, esta no puede resolver por sí misma: debe trasladar la solicitud a su sindicato y asistirle (Art. 28.3.e).
3. **Hace falta contrato entre cada sindicato y CGT Confederal** (Art. 28.3). Sin él, el traslado de datos del sindicato a Confederal carece de cobertura.
4. **La imprenta es subencargada, no encargada.** Su contratación exige **autorización de los sindicatos responsables** (Art. 28.2), no basta la decisión de Confederal.
5. **CGT Confederal lleva registro de encargado** (Art. 30.2), de contenido distinto y más reducido. **Cada sindicato lleva el suyo de responsable** (Art. 30.1).
6. **La EIPD la debe adoptar cada responsable.** Confederal la elabora y la pone a su disposición, que es lo razonable cuando un mismo servicio sirve a muchos responsables y sería absurdo repetir la evaluación técnica una vez por sindicato. Pero la evaluación no se tiene por hecha hasta que cada sindicato la asume.

> **Esta calificación es una propuesta técnica fundada en cómo funciona realmente el sistema, no un dictamen.** Existe una lectura alternativa —**corresponsabilidad** del Art. 26— si se concluyera que sindicatos y Confederal deciden conjuntamente fines y medios. La calificación que aquí se sostiene se apoya en que la finalidad la determina la relación asociativa entre la persona y su sindicato, y en que CGT Confederal no puede dar a los datos ningún uso propio. **Corresponde a la asesoría jurídica de CGT confirmarla o rectificarla antes de firmar nada**, porque de ella dependen los documentos que hay que suscribir.

---

## RESUMEN EJECUTIVO

Esta EIPD evalúa el tratamiento de **datos de afiliación sindical** (categoría especial por Art. 9 RGPD) en el Sistema de Carnets. El tratamiento es **necesario** para la gestión de afiliación y emisión de carnets sindicales, e incluye medidas de seguridad técnicas y organizativas proporcionales al riesgo.

**Qué cambia en la v1.2**: corrige el reparto de papeles entre los sindicatos y CGT Confederal (ver Nota Preliminar), del que dependen qué documentos hay que suscribir, quién informa a las personas afiliadas y ante quién ejercen sus derechos.

**Qué cambió en la v1.1**: la v1.0 describía el cifrado en reposo, el KMS, los backups cifrados, el segundo factor y la auditoría automatizada como medidas *planificadas* para una fase v2.0. **Todas están implementadas y verificadas** (§4.1), igual que el expurgado automático por vencimiento del plazo de conservación, que la v1.0 daba por documentado pero no ejecutable. Corrigió además la base legal (§2.1) y el campo del que depende el cómputo del plazo (§6.2).

**Conclusión**: Con las medidas técnicas implementadas (cifrado en reposo y en tránsito, gestión de claves en KMS, doble factor en el punto donde se descifra, auditoría de accesos, validación de entrada, limitación de intentos y expurgado automático) y las medidas organizativas descritas en esta EIPD, los riesgos técnicos se reducen a un nivel aceptable.

**Recomendación**: Proceder con el tratamiento una vez suscritos **los dos contratos que hoy faltan** —el que vincula a cada sindicato con CGT Confederal, y el que vincula a Confederal con la empresa de impresión (§7.3)—, y una vez que los sindicatos entreguen a sus personas afiliadas la información del Art. 13 (§5.8). Los riesgos residuales altos son los tres, y ninguno es de naturaleza técnica. Ver §10.2.

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
| **Fecha de expedición** | Cuando se emitió el carnet | "01/08/2026" | Datos personales | 3 años post-baja |
| **Notas históricas** | Registro de reemisiones | "Reemitido 03/2024" | Especial (afiliación) | 3 años post-baja |
| **Estado y fecha de impresión** | Trazabilidad del carnet | "IMPRESO", "12/08/2026" | Datos personales | 3 años post-baja |
| **Fecha de baja** | Inicio del cómputo de conservación | "14/03/2026" | Especial (afiliación) | 3 años post-baja |

**Cifrados en reposo** (AES-256-GCM a nivel de columna): nombre y apellidos, nº de afiliado y notas históricas. Los códigos de confederación, federación y sindicato no se cifran: son códigos administrativos de tres o cinco dígitos, sin espacio de valores suficiente para que el cifrado aporte nada, y son necesarios en claro para filtrar y ordenar los lotes de impresión.

**Datos de los usuarios del sistema** (no de los afiliados; interesados distintos, ver §1.3):

| Campo | Naturaleza | Sujeto | Retención |
|---|---|---|---|
| **Usuario y contraseña** (hash) | Credencial de acceso | Sindicato / imprenta / admin | Mientras la cuenta esté activa |
| **Nombre identificativo del sindicato** | Para aprobar el alta | Sindicato | Mientras la cuenta esté activa |
| **IP y fecha de aceptación del acuerdo** | Prueba de aceptación del acuerdo de confidencialidad | Sindicato | 3 años |
| **Registro de auditoría de accesos** | Usuario, IP, acción, recuento | Sindicato / imprenta / admin | 2 años (§6.1) |

**Total de registros**: ~3.024 afiliados (estimado, actualizándose mensualmente)  
**Categoría de datos**: Art. 9 RGPD (afiliación sindical es categoría especial)

### 1.3 Categorías de Interesados y Recorrido del Dato

**Interesados**: las personas afiliadas a los sindicatos de rama y de provincia confederados en CGT. Son los únicos interesados cuyos datos son de categoría especial, y los únicos que **no interactúan con este sistema**.

**Recorrido del dato**, que es lo que explica el reparto de papeles:

```
  Persona afiliada
        │  se afilia y facilita sus datos a su sindicato
        ▼
  Sindicato de rama / provincia          ← RESPONSABLE
        │  los sube al sistema, solo para que le confeccionen el carnet
        ▼
  CGT Confederal                          ← ENCARGADO
        │  agrupa los lotes y remite lo necesario para imprimir
        ▼
  Empresa de impresión                    ← SUBENCARGADA
        │  imprime y devuelve los carnets
        ▼
  Sindicato → persona afiliada
```

El dato **nace en el sindicato y vuelve al sindicato**. CGT Confederal es un tramo intermedio con una finalidad única.

**Quiénes usan el sistema** (no confundir con los interesados):

1. **Personal de los sindicatos**: sube las listas y consulta exclusivamente sus propias personas afiliadas. Actúa por cuenta del responsable.
2. **Administración de CGT Confederal**: gestiona el servicio. Es el único perfil que ve los datos descifrados, y por eso es el único al que se le exige segundo factor.
3. **Personal de la empresa de impresión**: accede a un panel de solo lectura con el código de sindicato y el nº de afiliado de los lotes ya remitidos. **No ve nombres** y no ve nada que aún no se le haya enviado.

### 1.4 Duración del Tratamiento
- **Ciclo corto**: solicitud → validación → imprenta → entrega (~1-2 meses)
- **Ciclo largo**: datos viven 3 años post-cancelación (legal hold para auditoría y resolución de conflictos laborales)

---

## 2. BASE LEGAL Y NECESIDAD (Art. 6 + Art. 9 RGPD)

### 2.1 Legitimidad (Art. 6)

> **Quién fija la base legal.** La determina **cada sindicato responsable**, no CGT Confederal. Un encargado no tiene base jurídica propia: opera al amparo de la del responsable. Lo que sigue es la base que, a juicio de quien elabora esta EIPD, ampara el tratamiento, y que cada sindicato debe hacer suya al adoptarla.

> **Corrección respecto de la v1.0.** La v1.0 invocaba el **Art. 6.1.a (consentimiento del interesado)** y lo justificaba con «firma digital del acuerdo RGPD antes de subir datos». Eso describe mal lo que hace el sistema: el acuerdo que se acepta en la aplicación —con registro de fecha e IP— lo acepta **el sindicato** que sube el archivo, y es un compromiso sobre el uso de la herramienta. **La persona afiliada no interviene en el sistema y este no recoge, ni almacena, ni puede acreditar su consentimiento.** Apoyar la licitud en un consentimiento que no existe deja el tratamiento sin base si alguien lo revisa.

El tratamiento se apoya en:
- **Art. 6.1.b RGPD**: ejecución de la relación asociativa entre la persona afiliada y su sindicato, de la que la emisión del carnet es una prestación característica.
- **Art. 6.1.c RGPD**, con carácter complementario: cumplimiento de las obligaciones de registro derivadas de la normativa sindical y de la propia normativa de protección de datos.

La afiliación se produce en el sindicato, no aquí. Este sistema no es el punto de captación del dato: es donde se procesa para confeccionar el carnet. La base legal la sostiene la relación asociativa previa entre la persona y su sindicato, no el acto de subir un archivo.

### 2.2 Excepción de Datos de Categoría Especial (Art. 9.2.d)

> **Corrección respecto de la v1.0.** La v1.0 citaba el **Art. 9.2.c** y le atribuía el texto sobre organizaciones sindicales. Ese texto no es del 9.2.c —que se refiere al interés vital del interesado cuando no puede prestar consentimiento— sino del **9.2.d**. La excepción aplicable es la d.

El tratamiento de datos de afiliación sindical está permitido por el **Art. 9.2.d RGPD**: tratamiento efectuado en el ámbito de sus actividades legítimas, y con las debidas garantías, por un organismo sin ánimo de lucro de finalidad sindical, siempre que se refiera exclusivamente a sus miembros actuales o antiguos y que los datos **no se comuniquen a terceros sin consentimiento**.

Esta última condición es la que gobierna el diseño del sistema y merece subrayarse, porque **la cadena tiene ahora dos eslabones y ambos han de sostenerse**:

- El traslado del sindicato a **CGT Confederal** no es comunicación a un tercero: Confederal actúa como **encargada** por cuenta del sindicato, sin finalidad propia. Esa condición se acredita con el contrato del Art. 28.3 entre ambos, hoy inexistente.
- La remisión de Confederal a la **empresa de impresión** tampoco lo es, por la misma razón, siendo aquella **subencargada** (Art. 28.4). Requiere contrato y, además, autorización de los sindicatos responsables (Art. 28.2).
- **Si falla cualquiera de los dos contratos**, el eslabón correspondiente pasa a ser una comunicación a un tercero sin consentimiento y el tratamiento pierde el amparo del 9.2.d **en su conjunto**, no solo en ese tramo. Es la razón por la que ambos figuran como bloqueantes en §10.2.
- La limitación «miembros actuales o antiguos» refuerza el plazo de conservación del §6: pasado un plazo razonable tras la baja, la excepción deja de dar cobertura.

Las «debidas garantías» que el precepto exige son las medidas de la sección 4.

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

Estado a fecha de esta revisión. La columna «Riesgo residual» es la que queda **después** de aplicar la medida.

| Riesgo | Escenario | Severidad inicial | Medida implementada | Riesgo residual |
|---|---|---|---|---|
| **Cifrado en reposo** | Robo del servidor o de un backup expone la BD | CRÍTICO | AES-256-GCM por columna sobre nombre, nº de afiliado y notas; claves servidas por KMS (Vault), nunca en el código | BAJO |
| **Cifrado en tránsito** | Intercepción de la sesión de un sindicato | CRÍTICO | HTTPS forzado, HSTS, cookies Secure. El despliegue **se detiene** si falta cualquiera de los cuatro ajustes | BAJO |
| **Credencial robada del admin** | Una contraseña filtrada abre el archivo entero descifrado | CRÍTICO | Segundo factor TOTP obligatorio en el admin, que es el único punto donde se descifra | BAJO |
| **Fuerza bruta / credential stuffing** | Prueba masiva de contraseñas | ALTO | 5 intentos por par (IP, usuario) y bloqueo de 5 minutos; el contador vive en caché compartida, verificado por comprobación de despliegue | BAJO |
| **Acceso horizontal (IDOR)** | Un sindicato accede a los afiliados de otro | CRÍTICO | Las vistas nunca aceptan identificadores desde la URL o el POST: derivan siempre de `request.user` | BAJO |
| **Inyección SQL** | Excel manipulado para inyectar SQL | ALTO | ORM exclusivamente, sin SQL construido por concatenación; validación por expresión regular campo a campo | BAJO |
| **XSS** | Script inyectado en un nombre de afiliado | ALTO | Autoescapado de plantillas sin excepciones + Content-Security-Policy con `script-src 'self'`, que deja inerte un XSS aunque llegara a inyectarse | BAJO |
| **Manipulación del registro de auditoría** | Alguien con acceso al servidor borra su rastro | CRÍTICO | Registro estructurado emitido para su envío a destino externo de solo-adición | **MEDIO** — depende de que el envío externo esté configurado en el servidor (§9.1) |
| **Pérdida de datos** | Fallo de hardware sin copia | ALTO | Backup diario cifrado con Vault antes de salir del servidor, subido a Object Storage con cifrado de servidor y rotación | **MEDIO** — hasta que se pruebe una restauración real (§10.2) |
| **Conservación indefinida** | Los datos sobreviven a la finalidad que los legitimaba | ALTO | `expurgar_afiliados`: anonimiza la ficha **y su historial completo** al vencer el plazo | BAJO |
| **Fuga por la exportación a imprenta** | El archivo con nombres en claro sale del sistema y queda en un correo o un disco | **CRÍTICO** | La exportación exige permiso de cambio y queda auditada con autor y recuento | **ALTO** — es el riesgo residual más alto del sistema (§9.1) |
| **Vulnerabilidad en dependencias** | CVE en Django, pandas u openpyxl | MEDIO | `pip-audit` en cada push, junto con bandit, ruff y la suite de pruebas | BAJO |
| **Secretos en el código** | Claves o contraseñas escritas en el repositorio | CRÍTICO | Todo por variables de entorno; la aplicación se niega a arrancar sin clave de cifrado | BAJO |
| **Robo de sesión** | Cookie robada del navegador del administrador | ALTO | HttpOnly, Secure, caducidad a los 30 minutos de inactividad, y el segundo factor limita lo que una cookie sola permite | BAJO |
| **Denegación de servicio** | Excel de 100.000 filas, peticiones masivas | MEDIO | Límite de 5 MB y 10.000 filas; rechazo de cuerpos de más de 10 MB. Lo demás no puede resolverlo la aplicación: requiere WAF y fail2ban en la infraestructura | **MEDIO** — ver `deploy/waf_y_ddos.md` |
| **Phishing al administrador** | Correo falso que captura la contraseña | ALTO | El segundo factor impide que la contraseña sola sirva de algo | BAJO |

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

### 4.1 Medidas Técnicas Implementadas

Todas las de esta sección están en el código y cubiertas por pruebas automáticas que se ejecutan en cada cambio. Las que la v1.0 listaba como planificadas para una «fase v2.0» van marcadas **[v1.1]**.

#### Cifrado y gestión de claves
- **[v1.1] Cifrado en reposo AES-256-GCM** a nivel de columna sobre nombre y apellidos, nº de afiliado y notas históricas. Cifrado autenticado: una modificación del texto cifrado en la base de datos no pasa desapercibida, falla al descifrar.
- **[v1.1] Identificador de clave en cada valor**, lo que permite rotar la clave sin reescribir la base de datos de golpe y sin perder lo cifrado con la anterior.
- **[v1.1] Claves servidas por KMS** (HashiCorp Vault), no por el `.env`, con la restricción de que el proveedor esté en la UE (`deploy/RESTRICCION_UE.md`).
- **Protección contra destrucción irreversible**: si un valor no se puede descifrar porque falta su clave, el sistema se niega a escribirlo de vuelta. Sin esto, abrir y guardar una ficha con la clave mal configurada sobrescribiría el dato original de forma definitiva.
- La aplicación **se niega a arrancar** sin clave de cifrado configurada, antes que guardar datos personales en claro.

#### Autenticación y autorización
- **[v1.1] Segundo factor TOTP obligatorio en el administrador**, que es el único punto del sistema donde los datos se ven descifrados. No se exige a los sindicatos, que no descifran nada: sería un coste sin contrapartida.
- Limitación de intentos: 5 fallos por par (IP, usuario) y bloqueo de 5 minutos. **[v1.1]** El contador vive en caché compartida entre procesos, y el despliegue se detiene si no lo está — con caché por proceso el límite se multiplicaba por el número de trabajadores.
- Autorización por rol; las vistas nunca aceptan identificadores desde la URL o el formulario, siempre derivan de `request.user`.
- Las cuentas de sindicato nacen inactivas y requieren aprobación manual.

#### Minimización efectiva
- El panel de la imprenta consulta **sin traer los nombres**: ve el código de sindicato y el nº de afiliado de los lotes ya enviados, y solo de los ya enviados.
- El registro de auditoría **no escribe datos personales**: quién, cuándo, desde dónde, qué operación y sobre cuántos registros. Hay una prueba automática que lo comprueba.
- La representación de un afiliado en el registro interno del administrador de Django no incluye nombre ni número. Esa tabla no está cifrada, no se purga y viaja en todos los backups; incluir ahí los datos habría dejado una copia en claro de justo lo que se cifra. Se corrigió además lo ya escrito con una migración.

#### Entrada y salida
- Validación por expresión regular campo a campo; extensión, tamaño (5 MB) y número de filas (10.000) acotados; rechazo de cuerpos de más de 10 MB.
- Carga de Excel todo-o-nada en una transacción.
- ORM exclusivamente, sin SQL construido por concatenación.
- **[v1.1] Content-Security-Policy** en todas las respuestas, con `script-src 'self'`, que convierte un XSS en inerte aunque llegara a inyectarse.

#### Conservación
- **[v1.1] Expurgado automático** (`expurgar_afiliados`): al vencer el plazo, anonimiza la ficha **y todas las versiones de su historial**. Sin lo segundo el expurgado sería aparente: el historial conserva una copia de cada versión y ahí seguiría el nombre.
- **[v1.1] Sello automático de la fecha de baja**, que es el punto desde el que se cuenta el plazo. Sin él el plazo estaba escrito pero no era aplicable.

#### Continuidad
- **[v1.1] Backup diario cifrado antes de salir del servidor** (Vault Transit, desde memoria: el volcado en claro no llega a tocar el disco), subido con cifrado de servidor y rotación automática.

#### Verificación continua
- **[v1.1]** En cada cambio del código se ejecutan la suite completa de pruebas, análisis estático de seguridad (bandit), análisis de calidad (ruff), **[v1.1]** comprobación de vulnerabilidades conocidas en las dependencias (pip-audit) y la comprobación de despliegue de Django con los avisos de seguridad tratados como errores.
- **[v1.1] Alerta automática** por correo ante rachas de bloqueos de acceso, exportaciones de afiliados o accesos denegados.

### 4.2 Medidas Pendientes

| Medida | Por qué sigue pendiente | Responsable |
|---|---|---|
| **Contrato de encargado con la imprenta** | Requiere firma de ambas partes | CGT (jurídico) |
| **Envío de la auditoría a destino externo de solo-adición** | Requiere configuración en el servidor de producción | Responsable técnico |
| **Prueba real de restauración de backup** | El procedimiento está escrito; falta ejecutarlo una vez | Responsable técnico |
| **PostgreSQL en subred privada** | Se aplica al desplegar en Scaleway/OVH | Responsable técnico |
| **Pen testing externo** | Recomendable antes de producción. La suite incluye pruebas propias de inyección, IDOR y fuerza bruta, pero una revisión propia no sustituye a una externa | CGT |
| **Seudonimización (identificador interno desvinculado)** | Mejora, no requisito. El cifrado por columna ya cubre el riesgo principal | — |

### 4.3 Medidas Organizativas

#### Políticas y Procedimientos
- **Política de Retención** (sección 5): datos de afiliados 3 años post-baja, logs 2 años
- **Política de Acceso**: solo admin sindicatos (creados por CGT central) y superusuarios CGT
- **Política de Cambios**: cambios en código requieren revisión pre-deployment (SAST/tests)
- **Plan de Respuesta a Incidentes**: procedimiento de notificación en 72h a APD si brecha

#### Control de Acceso Físico y Lógico
- **Alojamiento**: el destino documentado es Scaleway u OVHcloud, ambos en la UE, con la base de datos en subred privada sin IP pública (`deploy/scaleway_setup.md`, `deploy/postgresql_vpc.md`). La v1.0 daba por hecho PythonAnywhere, con sede en Reino Unido: la migración a un proveedor de la UE elimina de raíz la transferencia internacional que aquella obligaba a justificar.
- **Acceso al servidor**: claves SSH; sin acceso directo a la base de datos desde puestos de trabajo.
- **Usuario de base de datos sin permisos de DDL**, de modo que una vulnerabilidad en la aplicación no pueda alterar el esquema ni borrar tablas.

#### Tareas periódicas
Tres controles dependen de que estén programados en el servidor; sin ellos existen en el código pero no se ejecutan nunca (`deploy/tareas_programadas.md`):

| Comando | Cadencia | Qué deja de cumplirse si no corre |
|---|---|---|
| `revisar_auditoria` | Cada hora | Detección de accesos anómalos (Art. 32.1.d) |
| `backup_a_s3_cifrado` | Diaria | Capacidad de restaurar (Art. 32.1.c) |
| `expurgar_afiliados` | Trimestral | Plazo de conservación (Art. 5.1.e) |

#### Capacitación y Conciencia
- **Capacitación RGPD**: todos los usuarios de sindicatos reciben guía de seguridad antes de usar sistema
- **Capacitación admin CGT**: responsable técnico entrenado en gestión de secretos, KMS, backups
- **NDA**: usuarios sindicatos firman acuerdo de confidencialidad

#### Gestión de Incidentes
- **Detección**: alertas automáticas de fallos, errores de aplicación
- **Contención**: procedimiento de rollback de cambios, aislamiento de acceso
- **Notificación**: 72h máximo para notificar a APD (Art. 33 RGPD)
- **Remediación**: parche + redeployment + auditoría post-incident

#### Encargados del tratamiento (Art. 28 RGPD)
Ver §7.3, donde se detallan junto con el estado de cada contrato.

---

## 5. DERECHOS DE LOS INTERESADOS (Art. 12-22 RGPD)

> **Ante quién se ejercen.** Ante **el sindicato** al que la persona está afiliada, que es el responsable del tratamiento. CGT Confederal no puede resolver una solicitud por sí misma: si la recibe, debe trasladarla al sindicato correspondiente sin dilación y prestarle la asistencia técnica que necesite (Art. 28.3.e) —típicamente, localizar el registro, extraer los datos o ejecutar una supresión—. Atenderla directamente sería actuar como responsable, papel que no le corresponde.
>
> **Advertencia sobre el alcance de esta sección.** Los procedimientos que siguen son **organizativos y manuales**. La aplicación no tiene portal de autoservicio, ni formulario de solicitud, ni generación automática de expedientes. La v1.0 podía dar a entender lo contrario al decir «el sistema permite».
>
> Que sean manuales no los hace insuficientes: con el volumen actual y la frecuencia esperada de solicitudes, un procedimiento manual bien definido cumple el Art. 12. Lo que exige es que **cada sindicato publique un canal y designe a alguien que lo atienda dentro del plazo de un mes**. Ese canal debe figurar en el texto informativo que el sindicato entrega en el momento de la afiliación (§5.8).

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

### 5.8 Información al Interesado (Art. 13 y 14) — **pendiente**

> **Corrección respecto de la v1.1.** La v1.1 sostenía que aplicaba el **Art. 14**, por entender que los datos no se obtenían del propio interesado. Era consecuencia de situar mal el punto de captación. **Los datos sí se obtienen del interesado**: se los facilita a su sindicato al afiliarse. Aplica por tanto el **Art. 13**, y el momento de informar es **ese mismo**, no «en un plazo razonable».

**Obligado a informar: el sindicato**, que es quien recaba y quien es responsable. No CGT Confederal, que no tiene contacto con la persona afiliada ni forma de alcanzarla.

**Situación actual**: no consta que se entregue información alguna en el momento del alta. El texto que muestra la aplicación es un acuerdo dirigido al sindicato usuario (§2.1), no a la persona afiliada.

**Contenido exigible** (Art. 13.1 y 13.2): identidad y contacto del **sindicato** como responsable; del delegado de protección de datos si se designa; finalidad y base jurídica (Arts. 6.1.b y 9.2.d); categorías de datos; **destinatarios —CGT Confederal como encargada y la empresa de impresión como subencargada—**; plazo de conservación; derechos y canal de ejercicio; y derecho a reclamar ante la AEPD.

**Acción**: CGT Confederal facilita a los sindicatos un modelo listo para usar (`INFORMACION_Afiliados_Art13.md`); cada sindicato lo adapta con sus propios datos, lo incorpora a su impreso de alta y deja constancia de la entrega. Para quienes ya están afiliados, comunicación por el canal habitual del sindicato.

Que Confederal proporcione el modelo no traslada la obligación: **cumple quien lo entrega**.

---

## 6. POLÍTICA DE RETENCIÓN Y EXPURGADO

### 6.1 Tabla de Retención

| Datos | Finalidad | Periodo Retención | Fundamento Legal | Acción post-plazo |
|---|---|---|---|---|
| **Afiliado (nombre, nº, confederación)** | Gestión carnet + auditoría laboral | 3 años post-baja | Legal hold (resolución conflictos laborales) | Anonimizar |
| **Estado impresión (PENDIENTE/IMPRESO)** | Trazabilidad | Mientras activo + 3 años | Legal hold | Anonimizar |
| **Fecha expedición** | Validación carnet | Mientras activo + 3 años | Legal hold | Anonimizar |
| **Historial de cambios del afiliado** | Trazabilidad de quién modificó qué | Igual que el afiliado | Art. 5.2 (responsabilidad proactiva) | Anonimizar **junto con la ficha** (§6.2) |
| **IP y fecha de aceptación del acuerdo (sindicato)** | Acreditar que el sindicato aceptó el compromiso de confidencialidad. No es consentimiento del afiliado (§2.1) | 3 años desde la baja de la cuenta | Defensa frente a reclamaciones | Borrar |
| **Registro de auditoría de accesos** | Trazabilidad de consultas y exportaciones | 2 años | Art. 30 y 32.1.d | Borrar del destino externo |
| **Cuenta de sindicato** | Acceso al servicio | Mientras la cuenta esté activa | Prestación del servicio | Desactivar y anonimizar |
| **Backup de la base de datos** | Recuperación ante desastre | Según rotación configurada | Continuidad (Art. 32.1.c) | Destruir |

**Nota sobre los backups y el derecho de supresión.** Un afiliado anonimizado en la base de datos viva sigue apareciendo en los backups anteriores al expurgado hasta que estos rotan. Esto es admisible siempre que los backups no se usen para otra cosa que restaurar ante desastre, y que una restauración vaya seguida de una ejecución del expurgado. **Conviene que el plazo de rotación de backups sea sensiblemente menor que el plazo de conservación**, para que la ventana en que el dato sobrevive a su supresión sea corta y acotada.

### 6.2 Procedimiento de Expurgado

> **Corrección respecto de la v1.0.** El procedimiento descrito en la v1.0 no se podía ejecutar: consultaba un campo `fecha_cancelacion` que nunca existió en el modelo. El estado pasaba a BAJA sin dejar constancia de **cuándo**, de modo que no había fecha desde la que contar el plazo. El plazo estaba documentado pero era inaplicable, que a efectos prácticos equivale a no tenerlo.

**Implementado** como comando `expurgar_afiliados`, para ejecución trimestral desde el planificador de tareas:

1. Selecciona los afiliados en estado BAJA cuya `fecha_baja` (sellada automáticamente al pasar a baja) sea anterior al plazo, tres años por defecto.
2. Anonimiza nombre, nº de afiliado y notas históricas **en la ficha y en todas las versiones de su historial**, dentro de una única transacción.
3. Deja constancia en el registro de auditoría con el recuento y los identificadores afectados, nunca con los datos suprimidos.

**Por qué el historial es la parte esencial**: el sistema conserva una copia de cada versión del afiliado para poder acreditar quién cambió qué. Anonimizar solo la ficha viva dejaría el nombre anterior intacto en esa tabla —cifrado, pero recuperable con la clave—, es decir, dejaría sin suprimir exactamente el dato que se acaba de declarar suprimido. Es un fallo que no se ve desde la aplicación: la ficha aparece anonimizada.

**Se anonimiza en lugar de borrar la fila** para conservar el recuento histórico de carnets emitidos, que no identifica a nadie. Lo que desaparece es el vínculo entre una persona y su afiliación sindical, que es el dato de categoría especial.

**Comprobación previa obligatoria**: la operación es irreversible por definición. Antes de programarla debe ejecutarse con `--dry-run`, que informa de a cuántos afectaría y, por separado, de cuántas bajas carecen de fecha y por tanto no son expurgables. Estas últimas requieren decisión manual: **no se les asigna una fecha estimada**, porque errar por exceso significaría anonimizar a alguien antes de tiempo.

**Auditoría**: cada expurgado queda registrado como `afiliados.expurgados`. Es la única prueba de haber cumplido el plazo —y de no haberse adelantado a él—, porque una vez expurgado no queda dato que mostrar.

---

## 7. TRANSFERENCIAS DE DATOS

### 7.1 Transferencias Internas
- **Dentro de CGT**: datos de afiliados compartidos entre estructura central y federaciones (necesario para auditoría)
  - **Medida**: acceso basado en rol, cada federación solo ve sus afiliados
  - **Contrato**: no requiere por ser mismo responsable de datos

### 7.2 Transferencias Internacionales (Fuera UE)
- **No aplica** si se despliega según lo documentado: Scaleway u OVHcloud, ambos con sede y centros de datos en la UE. El proveedor de claves está sujeto además a una restricción explícita de permanecer en la UE (`deploy/RESTRICCION_UE.md`), porque quien custodia las claves puede, por definición, acceder a los datos.
- La v1.0 asumía PythonAnywhere, con sede en Reino Unido. Tras el Brexit eso constituye transferencia internacional y habría exigido apoyarse en la decisión de adecuación del Reino Unido y vigilar su renovación. Migrar a un proveedor de la UE cierra la cuestión sin depender de decisiones que pueden decaer.
- Si en el futuro se contrata cualquier servicio fuera de la UE, hay que revisar esta sección antes, no después.

### 7.3 Cadena de Encargo (Arts. 28.2, 28.3 y 28.4)

| Eslabón | Papel | Instrumento necesario | Estado |
|---|---|---|---|
| Sindicato → **CGT Confederal** | Responsable → Encargado | Contrato Art. 28.3 | ⚠️ **PENDIENTE — bloqueante** |
| Confederal → **Empresa de impresión** | Encargado → Subencargada | Contrato Art. 28.4 + **autorización de los sindicatos** (Art. 28.2) | ⚠️ **PENDIENTE — bloqueante** |
| Confederal → **Proveedor de alojamiento** | Encargado → Subencargado | Contrato + autorización | Pendiente |
| Confederal → **Custodia de claves** | Encargado → Subencargado | Contrato + autorización, si es servicio gestionado | Según modalidad |
| Correo SMTP interno de CGT | — | No hay tratamiento de datos de afiliados | No aplica |

> **Sobre la autorización de subencargados (Art. 28.2).** Un encargado no puede subcontratar por su cuenta. CGT Confederal necesita **autorización de los sindicatos responsables** para recurrir a la imprenta y a los proveedores de infraestructura. La vía practicable, dado el número de sindicatos, es una **autorización general** incorporada al propio contrato del primer eslabón, con la relación de subencargados en anexo y el compromiso de comunicar cualquier alta o cambio con antelación suficiente para que un sindicato pueda oponerse. Sin esa cláusula, cada nuevo proveedor exigiría recabar firmas una por una.

#### Los dos contratos que faltan

Son el hallazgo principal de esta revisión y el motivo de que la recomendación del resumen ejecutivo esté condicionada.

**Primer eslabón: sindicatos → CGT Confederal.** Hoy los sindicatos trasladan a Confederal datos de categoría especial de sus personas afiliadas sin ningún instrumento que documente en qué condición los recibe, para qué puede usarlos, cuánto puede conservarlos ni qué debe hacer al terminar. Es la carencia más básica de las dos, y la que menos se nota, porque todo ocurre dentro de la casa.

**Segundo eslabón: CGT Confederal → empresa de impresión.** Descrito a continuación.

**Qué recibe realmente.** La acción «Descargar Excel para Máquina de Carnets» genera un archivo con los datos **descifrados** —incluidos nombre y apellidos completos— de las personas afiliadas seleccionadas, que se entrega a la empresa de impresión. Es la operación más sensible del sistema: el único punto por el que los datos de categoría especial salen del ámbito cifrado y del control técnico. A partir de ahí, ninguna de las medidas de la sección 4 sigue protegiéndolos.

Adicionalmente, la empresa dispone de una cuenta con un panel de solo lectura donde ve el código de sindicato y el nº de afiliado de los lotes ya remitidos. Ese panel **no muestra nombres**, y no muestra nada de lo que aún no se le ha enviado.

**Por qué el contrato no es un formalismo.** La licitud descansa en el Art. 9.2.d, que ampara al sindicato *siempre que los datos no se comuniquen a terceros sin consentimiento del interesado*. Una imprenta que actúa como **subencargada** —bajo instrucciones documentadas, sin finalidad propia— no es un tercero a estos efectos. Sin contrato que lo acredite, la entrega es una comunicación a un tercero y el amparo del 9.2.d decae **para el tratamiento en su conjunto**.

**Y el contrato no basta por sí solo**: al ser subencargo, requiere además la autorización de los sindicatos responsables. Un contrato impecable entre Confederal y la imprenta, sin esa autorización, sigue dejando el eslabón sin cobertura.

**Lo que el contrato debe fijar como mínimo** (Art. 28.3): objeto, duración y finalidad; prohibición de usar los datos para fin propio o cederlos; deber de confidencialidad del personal; medidas de seguridad concretas para el archivo recibido; régimen de subcontratación ulterior; asistencia ante ejercicios de derechos y ante brechas; **supresión certificada de los archivos al terminar cada encargo**; y sometimiento a auditoría.

**Medida compensatoria inmediata**, mientras el contrato se tramita: acordar por escrito un canal de entrega cifrado y un plazo máximo de borrado. Enviar el archivo por correo electrónico ordinario deja copias en servidores intermedios y en buzones fuera de todo control, indefinidamente.

---

## 8. CONSULTA CON LA AUTORIDAD DE PROTECCIÓN DE DATOS

### 8.1 ¿Se Requiere EIPD?
Sí, conforme a Art. 35.4 RGPD: el tratamiento de datos de **categoría especial a gran escala** requiere EIPD obligatoria.

### 8.2 ¿Se Requiere Consulta Previa a APD?
**Según Art. 36 RGPD**, se requiere consulta previa si la EIPD indica riesgos altos y las medidas propuestas no los mitigan suficientemente.

**En este caso**: las medidas técnicas que la v1.0 condicionaba están implementadas y el riesgo residual técnico es bajo (§9.1), de modo que **no se aprecia la situación de riesgo alto no mitigado** que obliga a la consulta previa.

Ahora bien, esa conclusión presupone resolver los puntos bloqueantes del §10.2. Mientras la empresa de impresión —que recibe nombres en claro— carezca de contrato de encargado, subsiste un riesgo alto **de naturaleza jurídica**, no técnica, y la valoración sobre la consulta previa debería rehacerse. La decisión final corresponde a asesoría jurídica.

**Recomendación**: no iniciar consulta previa, sino cerrar primero los cinco puntos bloqueantes. Si tras ello se desea contacto voluntario con la AEPD, presentar esta EIPD junto con el registro de actividades y los contratos suscritos.

---

## 9. EVALUACIÓN DE IMPACTO RESIDUAL (Después de Medidas)

### 9.1 Riesgos Residuales

| Riesgo | Nivel v1.0 | Nivel actual | Aceptabilidad |
|---|---|---|---|
| Brecha en reposo (robo de BD o backup) | ALTO | Bajo | ✓ |
| Brecha en tránsito | Medio | Bajo | ✓ |
| Credencial robada del administrador | ALTO | Bajo | ✓ |
| Inyección SQL / XSS | Bajo | Bajo | ✓ |
| Acceso horizontal (IDOR) | Bajo | Bajo | ✓ |
| Fuerza bruta | Medio | Bajo | ✓ |
| Conservación indefinida | ALTO | Bajo | ✓ |
| **Cadena de encargo sin formalizar** | No evaluado | **ALTO** | ✗ **No aceptable: faltan los dos contratos (§7.3)** |
| **Fuga por la exportación a imprenta** | Alto (no evaluado) | **ALTO** | ✗ **No aceptable sin contrato y autorización (§7.3)** |
| **Personas afiliadas sin informar** | No evaluado | **ALTO** | ✗ **No aceptable: incumple el Art. 13 (§5.8)** |
| **Manipulación del registro de auditoría** | Medio | **Medio** | Condicionado al envío externo |
| **Pérdida de datos** | Medio | **Medio** | Condicionado a probar una restauración |
| Denegación de servicio | Medio | Medio | Aceptable: mitigación en infraestructura |

**Los riesgos que no bajan a «bajo» tienen algo en común**: ninguno se resuelve escribiendo código. Tres necesitan firmas, uno una configuración en el servidor, otro ejecutar una restauración de prueba y anotar el resultado, y otro que los sindicatos entreguen un papel a quien se afilia. Es donde debe ir el esfuerzo ahora, y conviene no confundir el trabajo técnico ya hecho con conformidad completa: **un sistema técnicamente sólido cuya cadena de encargo no está documentada no está conforme**, por bien cifrado que esté.

### 9.2 Proporcionalidad de las Medidas

Las medidas técnicas descritas están implementadas y su coste recurrente se limita al alojamiento y la custodia de claves. Frente al perjuicio que causaría la divulgación de un archivo de afiliación sindical —que en el ámbito laboral puede traducirse en represalias sobre personas concretas, además de la responsabilidad administrativa de CGT—, son proporcionadas y no requieren mayor justificación.

Las tres medidas pendientes tienen coste bajo o nulo: un contrato, una configuración y una prueba de restauración. **No hay aquí ninguna disyuntiva entre coste y cumplimiento**; solo trabajo por hacer.

---

## 10. CONCLUSIÓN Y RECOMENDACIONES

### 10.1 Estado de Conformidad

| Aspecto | v1.0 | Actual (v1.1) |
|---|---|---|
| **Base legal (Art. 6 + 9)** | Invocaba preceptos equivocados | ✓ Corregida (§2.1, §2.2) |
| **Necesidad y proporcionalidad** | ✓ Cumple | ✓ Cumple |
| **Seguridad en tránsito (Art. 32)** | Parcial | ✓ Cumple, y el despliegue se detiene si falta |
| **Seguridad en reposo (Art. 32)** | ✗ Incumplía | ✓ Cumple (AES-256-GCM + KMS) |
| **Autenticación del acceso privilegiado** | Solo contraseña | ✓ Segundo factor obligatorio |
| **Registro de accesos (Art. 30)** | Parcial | ✓ Implementado · ⚠️ pendiente el destino externo |
| **Plazo de conservación (Art. 5.1.e)** | Documentado pero inaplicable | ✓ Implementado y ejecutable |
| **Capacidad de restaurar (Art. 32.1.c)** | ✗ | ✓ Backups cifrados · ⚠️ **sin restauración probada** |
| **Verificación periódica (Art. 32.1.d)** | ✗ | ✓ Pruebas, SAST y auditoría de dependencias en cada cambio |
| **Reparto de papeles (Arts. 4.7, 4.8, 28)** | ✗ Incorrecto | ✓ Corregido (Nota Preliminar) |
| **Información al interesado (Art. 13)** | ✗ (no detectado) | ✗ **Pendiente — obligación de los sindicatos** (§5.8) |
| **Contrato sindicatos → Confederal (Art. 28.3)** | ✗ (no detectado) | ✗ **Pendiente y bloqueante** (§7.3) |
| **Contrato y autorización de la imprenta (Arts. 28.2 y 28.4)** | ✗ (no identificada) | ✗ **Pendiente y bloqueante** (§7.3) |
| **Registro de actividades (Arts. 30.1 y 30.2)** | ✗ (no detectado) | ✗ **Pendiente** — uno por sindicato y otro de Confederal |

**Veredicto**: las medidas **técnicas** del Art. 32 están cubiertas y verificadas de forma continua. Lo que falta es **documental y organizativo**, y es lo que impide declarar conformidad. El orden en que se resuelva no cambia esa conclusión.

### 10.2 Recomendaciones Prioritarias

#### Bloqueante antes de producción

**A cargo de CGT Confederal:**
1. **Suscribir el contrato de encargado con cada sindicato** (Art. 28.3), incluyendo la autorización general de subencargados. Es el instrumento que da cobertura al traslado de datos que hoy ya ocurre.
2. **Suscribir el contrato de subencargo con la empresa de impresión** (Art. 28.4) y recabar la autorización de los sindicatos (Art. 28.2).
3. **Acordar por escrito el canal cifrado de entrega** del archivo de impresión y el plazo de borrado, aunque el contrato tarde. Es la medida compensatoria de coste inmediato.
4. **Elaborar su registro de encargado** (Art. 30.2).
5. **Poner esta EIPD a disposición de los sindicatos** para su adopción, en cumplimiento del Art. 28.3.f.

**A cargo de cada sindicato:**
6. **Entregar la información del Art. 13** a sus personas afiliadas (§5.8), usando el modelo facilitado.
7. **Llevar su registro de actividades** (Art. 30.1). Es obligatorio: la exención para organizaciones de menos de 250 empleados no aplica cuando se tratan datos del Art. 9.
8. **Adoptar y firmar esta EIPD.** Un borrador sin firmar no acredita haber realizado la evaluación que exige el Art. 35, y la obligación es del responsable.

#### Antes de dar el despliegue por terminado
6. **Programar las tres tareas periódicas** (§4.3). Sin ellas, tres controles descritos en esta EIPD no se ejecutan nunca.
7. **Configurar el envío del registro de auditoría a destino externo de solo-adición.** Mientras viva solo en el servidor, quien tenga acceso puede borrar su propio rastro.
8. **Restaurar un backup en un entorno de pruebas y anotar la fecha.** Una copia nunca restaurada es una hipótesis.
9. **Valorar la designación de delegado de protección de datos** (Art. 37.1.c). El tratamiento a gran escala de datos del Art. 9 apunta a que es obligatorio; la valoración corresponde a asesoría jurídica.

#### Continuo
10. Revisar los avisos automáticos de acceso anómalo y actuar sobre ellos.
11. Actualizar dependencias cuando `pip-audit` lo señale.
12. Rotar las claves de cifrado con la periodicidad prevista; el formato admite rotación sin parada.
13. Revisar esta EIPD anualmente, o antes si cambian los datos tratados, las finalidades o los encargados.

### 10.3 Firmantes

**Por CGT Confederal**, que la elabora en su condición de encargado del tratamiento:

| Rol | Nombre | Firma | Fecha |
|---|---|---|---|
| Responsable técnico del sistema | [Nombre] | _____ | |
| Delegado de Protección de Datos, si se designa | [Nombre] | _____ | |
| Por la Confederación | [Nombre] | _____ | |

**Adopción por el sindicato responsable.** La evaluación no se tiene por realizada respecto de un sindicato hasta que este la adopta. Cada sindicato que utilice el servicio cumplimenta y conserva:

| Concepto | Dato |
|---|---|
| Sindicato | [denominación y NIF] |
| Persona que la adopta en su nombre | [nombre y cargo] |
| Fecha de adopción | |
| Firma | _____ |
| Base legal que hace suya | Arts. 6.1.b y 9.2.d (§2), salvo indicación distinta |
| Plazo de conservación que fija | [ ] años desde la baja (por defecto 3, §6.1) |
| Canal de ejercicio de derechos que publica | [correo y dirección postal] |

> Los dos últimos campos no son trámite: **el plazo de conservación y el canal de derechos los decide el responsable**, no el software ni Confederal. El sistema viene configurado a tres años porque hay que configurarlo a algo, no porque esa sea una decisión ya tomada por nadie con competencia para tomarla.

---

## ANEXOS

### Anexo A: Registro de Cambios en la EIPD
Cada revisión de esta EIPD se registrará aquí:

| Versión | Fecha | Cambios | Autor |
|---|---|---|---|
| 1.0 | 2026-08-21 | EIPD inicial, estado v1.0 + roadmap v2.0 | [Autor] |
| 1.2 | 2026-08-26 | **Corregido el reparto de papeles.** Las versiones anteriores atribuían a CGT Confederal la condición de responsable del tratamiento. Los datos los recaban los sindicatos de rama y provincia, entidades con personalidad jurídica propia, y los trasladan a Confederal solo para la confección del carnet: los sindicatos son **responsables**, Confederal es **encargada** y la imprenta pasa de encargada a **subencargada**. De ahí se sigue que hacen falta dos contratos y no uno, que la imprenta requiere además autorización de los sindicatos (Art. 28.2), que quien informa a la persona afiliada es su sindicato y por el **Art. 13** y no el 14 (§5.8), que los derechos se ejercen ante el sindicato (§5), y que el registro de actividades se desdobla en uno de responsable por sindicato (Art. 30.1) y uno de encargado en Confederal (Art. 30.2) | [Autor] |
| 1.1 | 2026-08-26 | Reclasificadas como implementadas las medidas que la v1.0 daba por planificadas (cifrado en reposo, KMS, segundo factor, backups cifrados, verificación continua). Implementado el expurgado por vencimiento del plazo, que la v1.0 describía sobre un campo inexistente. Corregida la base legal (§2.1: no hay consentimiento del afiliado; §2.2: la excepción es el Art. 9.2.d, no el 9.2.c). Identificada la empresa de impresión como encargada del tratamiento y su contrato como pendiente y bloqueante (§7.3). Añadida la obligación de información del Art. 14 como pendiente (§5.8). Actualizado el alojamiento previsto de PythonAnywhere (RU) a proveedor de la UE | [Autor] |

### Anexo B: Referencias Legales
- Reglamento (UE) 2016/679 — RGPD
- Directiva (UE) 2016/680 — Protección datos ley enforcement
- Ley Orgánica 3/2018 (LOPDGDD) — implementación RGPD en España
- Ley de Convenios Colectivos — retención datos afiliados sindicales
- ISO 27001 — gestión seguridad información (referencia)

### Anexo C: Procedimiento ante una Brecha de Seguridad (Art. 33 y 34)

**El plazo de 72 horas cuenta desde que se tiene constancia de la brecha, no desde que se termina de investigarla.** Si a las 72 horas no se conoce el alcance, se notifica igual, de forma escalonada, indicando que la información se completará. Esperar a tener el cuadro completo es el error habitual.

#### Paso 1 — Contener (inmediato)
Cortar el acceso comprometido: desactivar la cuenta, revocar la sesión, rotar la clave de cifrado si se sospecha que ha quedado expuesta. **No borrar registros**: son la prueba de qué ocurrió.

#### Paso 2 — Valorar el alcance (primeras horas)
El registro de auditoría es la fuente principal. Debe responder a: qué cuentas, qué operaciones, sobre cuántos registros y desde qué direcciones IP. Preguntas a resolver:

- ¿Hubo exportación de afiliados (`afiliados.exportados`)? El recuento y los identificadores están en el registro.
- ¿Se accedió a la base de datos directamente o a través de la aplicación?
- **¿Estaban comprometidas también las claves de cifrado?** Es la pregunta que decide la gravedad: una base de datos sustraída sin las claves expone texto cifrado; con las claves, expone el archivo de afiliación. Se responden por separado porque residen en sistemas distintos, y esa separación es el motivo de que el KMS exista.

#### Paso 3 — Decidir si se notifica

| Situación | ¿Notificar a la AEPD? | ¿Notificar a los afiliados? |
|---|---|---|
| Datos cifrados expuestos, claves **no** comprometidas | Sí, indicando esa circunstancia | Probablemente no (Art. 34.3.a) |
| Datos en claro, o claves comprometidas | Sí | **Sí** — Art. 9 y riesgo alto |
| Archivo de impresión extraviado o enviado por error | Sí | **Sí** — va en claro y con nombres |
| Acceso indebido de un sindicato a datos de otro | Sí | Valorar según alcance |

Que los datos estuvieran cifrados y las claves a salvo es la circunstancia que puede eximir de comunicar a los afiliados (Art. 34.3.a). Es la razón práctica por la que el cifrado en reposo importa incluso asumiendo que un servidor puede ser comprometido.

#### Paso 4 — Notificar
A la **AEPD** por su sede electrónica, dentro de las 72 horas. A los **afiliados afectados**, sin dilación indebida cuando proceda, en lenguaje claro y sin tecnicismos.

#### Paso 5 — Registrar
Toda brecha se documenta **aunque no se notifique**, con la justificación de por qué no se notificó (Art. 33.5). Ese registro interno es lo que la autoridad pedirá si algún día revisa el tratamiento.

#### Contenido mínimo de la notificación (Art. 33.3)

```
Asunto: Notificación de violación de seguridad de datos personales (Art. 33 RGPD)

Responsable del tratamiento: [CGT — razón social y NIF]
Contacto para esta notificación: [nombre, cargo, correo, teléfono]

1. FECHA Y HORA de la brecha (o de su detección, si aquella se desconoce)
2. NATURALEZA de la violación: [acceso no autorizado / divulgación / pérdida /
   alteración], y cómo se detectó
3. CATEGORÍAS Y NÚMERO APROXIMADO de interesados afectados
4. CATEGORÍAS Y NÚMERO APROXIMADO de registros afectados
   IMPORTANTE: indicar si se trata de datos de AFILIACIÓN SINDICAL (Art. 9)
5. ESTADO DE CIFRADO de los datos afectados y si las claves resultaron
   comprometidas
6. CONSECUENCIAS PROBABLES de la violación
7. MEDIDAS ADOPTADAS o propuestas, incluidas las de mitigación del perjuicio
8. Datos de contacto del delegado de protección de datos, si se ha designado

Si algún dato no se conoce todavía, indicarlo expresamente y comprometer una
notificación complementaria. No es motivo para retrasar esta.
```

---

**FIN DE LA EIPD**

*Este documento debe revisarse anualmente o cuando haya cambios significativos en el tratamiento (nuevos datos, nuevas finalidades, cambios de infraestructura, etc).*

---

> **Sobre la elaboración de este documento.** Las secciones que describen el funcionamiento del sistema (§4, §6.2, §7.3 y la matriz de riesgos) se han contrastado contra el código fuente y están cubiertas por pruebas automáticas. Las secciones de calificación jurídica —base legal, excepciones del Art. 9, obligatoriedad de designar delegado de protección de datos y necesidad de consulta previa— son **borradores de trabajo redactados con apoyo técnico, no asesoramiento jurídico**, y deben ser revisadas y asumidas por quien lleve la asesoría legal de CGT antes de firmar. La v1.0 contenía errores en precisamente esas secciones, lo que ilustra por qué esa revisión hace falta.
