# REGISTRO DE ACTIVIDADES DE TRATAMIENTO

**Artículo 30.1 del Reglamento (UE) 2016/679 (RGPD)**

**Responsable del tratamiento**: CGT (Confederación General del Trabajo)
**Versión**: 1.0 · **Fecha**: 2026-08-26
**Última revisión**: — · **Próxima revisión**: 2027-08-26

---

> **Por qué este documento es obligatorio.** El Art. 30.5 exime de llevar registro a las organizaciones de menos de 250 empleados, **salvo** —entre otros supuestos— cuando el tratamiento incluya categorías especiales de datos del Art. 9. La afiliación sindical es una de ellas, de modo que la exención no resulta aplicable con independencia del tamaño de CGT.
>
> Este registro debe poder entregarse a la autoridad de control si lo requiere (Art. 30.4). Es un documento vivo: cada cambio en las finalidades, las categorías de datos, los destinatarios o los plazos obliga a actualizarlo.

---

## Datos de contacto

| Concepto | Dato |
|---|---|
| **Responsable del tratamiento** | CGT — [razón social completa] |
| **NIF** | [—] |
| **Domicilio** | [—] |
| **Correo de contacto en materia de protección de datos** | [—] |
| **Delegado de Protección de Datos** | [Nombre y contacto, o «no designado» con la motivación] |
| **Representante del responsable** (si procede) | No aplica |

> **Sobre el delegado de protección de datos.** El Art. 37.1.c obliga a designarlo cuando las actividades principales consistan en el tratamiento a gran escala de categorías especiales de datos. Si CGT concluye que no procede designarlo, **la motivación debe constar por escrito**: la ausencia de motivación es en sí misma un incumplimiento verificable en una inspección.

---

## ACTIVIDAD 1 — Gestión de afiliación y emisión de carnets sindicales

### 1. Fines del tratamiento
- Emisión, reemisión y entrega del carnet acreditativo de afiliación.
- Mantenimiento del registro de personas afiliadas (altas y bajas).
- Trazabilidad de las operaciones sobre los datos, exigida por el Art. 5.2.

### 2. Base jurídica
- **Art. 6.1.b RGPD** — ejecución de la relación asociativa entre la persona afiliada y la organización sindical, de la que la emisión del carnet es prestación característica.
- **Art. 6.1.c RGPD**, complementariamente — obligaciones de registro derivadas de la normativa sindical y de la propia normativa de protección de datos.
- **Art. 9.2.d RGPD** — excepción aplicable a las categorías especiales: tratamiento efectuado en el ámbito de sus actividades legítimas y con las debidas garantías por un organismo sin ánimo de lucro de finalidad sindical, referido exclusivamente a sus miembros actuales o antiguos, y sin comunicación a terceros sin consentimiento.

> La condición «sin comunicación a terceros» es la que exige que la empresa de impresión esté vinculada por contrato de encargado del tratamiento. Ver Actividad 2.

### 3. Categorías de interesados
Personas trabajadoras afiliadas a CGT, actuales y antiguas.

### 4. Categorías de datos personales

| Categoría | Datos | ¿Art. 9? | ¿Cifrado en reposo? |
|---|---|---|---|
| Identificativos | Nombre y apellidos | Sí, por asociación | **Sí** |
| Identificativos | Nº de afiliado | Sí, por asociación | **Sí** |
| Afiliación | Estado (alta / baja), fecha de baja | **Sí** | Fecha, no |
| Afiliación | Notas de reemisiones | **Sí** | **Sí** |
| Estructura organizativa | Códigos de confederación territorial, federación local, federación sectorial y sindicato | **Sí** | No — códigos numéricos administrativos |
| Emisión | Lengua, fecha de expedición, estado y fecha de impresión | No | No |

**No se tratan**: DNI o pasaporte, datos bancarios, domicilio, teléfono, correo del afiliado, historial laboral ni datos de menores.

### 5. Destinatarios
- **Empresa de impresión de carnets**, en calidad de encargada del tratamiento. Recibe nombre y apellidos, nº de afiliado, códigos de estructura, lengua y fecha de expedición de los lotes que se le remiten. Ver Actividad 2.
- **Proveedor de alojamiento**, en calidad de encargado. Los datos identificativos residen cifrados en su infraestructura y las claves no se custodian en ella.
- No se prevén otras comunicaciones. **No hay cesiones a terceros por cuenta propia.**

### 6. Transferencias internacionales
Ninguna. Alojamiento y custodia de claves en la Unión Europea, por decisión expresa documentada en `deploy/RESTRICCION_UE.md`.

### 7. Plazos de supresión
- **Tres años desde la fecha de baja.** Vencido el plazo, los datos identificativos se anonimizan de forma automatizada, tanto en la ficha como en su historial de cambios.
- Se conserva el recuento agregado de carnets emitidos, que no permite identificar a nadie.
- Procedimiento y su verificación: §6.2 de la EIPD.

### 8. Medidas técnicas y organizativas de seguridad (Art. 32)
Resumen; el detalle completo y su verificación están en la §4 de la EIPD.

- Cifrado AES-256-GCM a nivel de columna sobre los datos identificativos, con claves servidas por un sistema de gestión de claves externo a la aplicación.
- Segundo factor de autenticación obligatorio en el único punto donde los datos se muestran descifrados.
- Control de acceso por rol; ninguna vista acepta identificadores procedentes del usuario.
- Cifrado en tránsito obligatorio, verificado automáticamente antes de cada despliegue.
- Registro de auditoría de accesos y exportaciones que **no contiene datos personales**, con alertas automáticas ante patrones anómalos.
- Copias de seguridad cifradas antes de salir del servidor.
- Verificación continua: pruebas automatizadas, análisis estático de seguridad y auditoría de vulnerabilidades en dependencias en cada modificación del código.

---

## ACTIVIDAD 2 — Remisión de datos a la empresa de impresión

Se registra por separado por ser la única operación en que los datos abandonan el entorno cifrado y el control técnico de CGT.

| Concepto | Contenido |
|---|---|
| **Fin** | Impresión física de los carnets |
| **Base jurídica** | Art. 6.1.b; Art. 9.2.d con la garantía del contrato de encargado (Art. 28.3) |
| **Interesados** | Personas afiliadas incluidas en cada lote de impresión |
| **Datos** | Nombre y apellidos, nº de afiliado, códigos de estructura, lengua, fecha de expedición. **Se remiten sin cifrar**, por ser necesarios en claro para la impresión |
| **Destinatario** | [Razón social de la empresa de impresión] — encargada del tratamiento |
| **Transferencias internacionales** | Ninguna, siempre que la empresa esté establecida en la UE. **Verificar** |
| **Plazo de supresión** | El encargado debe suprimir cada lote al concluir el encargo, con confirmación por escrito |
| **Medidas de seguridad** | Generación restringida a personal autorizado; cada exportación queda auditada con autor, momento y recuento; canal de entrega cifrado acordado con el encargado |

> ⚠️ **Estado**: el contrato del Art. 28.3 **está pendiente de suscripción**. Hasta entonces esta actividad carece de la garantía que le da cobertura jurídica. Es el punto bloqueante señalado en la §10.2 de la EIPD.

---

## ACTIVIDAD 3 — Gestión de cuentas de usuario del sistema

| Concepto | Contenido |
|---|---|
| **Fin** | Control de acceso a la aplicación y trazabilidad de las operaciones |
| **Base jurídica** | Art. 6.1.f — interés legítimo en la seguridad del tratamiento, expresamente reconocido por el Considerando 49 |
| **Interesados** | Personal de sindicatos locales, de la empresa de impresión y de administración de CGT |
| **Datos** | Nombre de usuario, contraseña almacenada mediante función de derivación con sal, nombre identificativo del sindicato, fecha y dirección IP de aceptación del acuerdo de confidencialidad, secreto del segundo factor en las cuentas de administración |
| **Destinatarios** | Ninguno |
| **Plazo de supresión** | Mientras la cuenta esté activa; se desactiva y anonimiza al cesar la relación |
| **Medidas** | Contraseñas nunca almacenadas en claro; limitación de intentos de acceso; caducidad de sesión por inactividad |

---

## ACTIVIDAD 4 — Registro de auditoría de accesos

| Concepto | Contenido |
|---|---|
| **Fin** | Acreditar quién accedió o exportó qué y cuándo (Art. 5.2, 30 y 32.1.d); detectar accesos indebidos |
| **Base jurídica** | Art. 6.1.c — obligación legal derivada de los Arts. 5.2 y 32 |
| **Interesados** | Usuarios del sistema |
| **Datos** | Identificador de usuario, dirección IP, momento, operación e identificadores de los registros afectados. **Por diseño no contiene nombres ni números de afiliado**, verificado por prueba automática |
| **Destinatarios** | Sistema externo de registro de solo-adición, ubicado en la UE, en calidad de encargado |
| **Plazo de supresión** | 2 años |
| **Medidas** | Destino de solo-adición para impedir que quien tenga acceso al servidor borre su propio rastro; revisión automática horaria con alerta por correo |

> ⚠️ **Estado**: el envío al destino externo **está pendiente de configuración** en el servidor de producción. Mientras el registro resida únicamente en el servidor, no cumple su función probatoria.

---

## Control de versiones

| Versión | Fecha | Cambios | Autor |
|---|---|---|---|
| 1.0 | 2026-08-26 | Registro inicial. Cuatro actividades identificadas | [Autor] |

---

> **Naturaleza de este documento.** Las descripciones técnicas (categorías de datos, medidas de seguridad, plazos y flujos) se han contrastado contra el código fuente del sistema. Las calificaciones jurídicas —bases de licitud, encaje de las excepciones del Art. 9, condición de encargado de cada proveedor— son **propuestas de trabajo, no asesoramiento jurídico**, y requieren revisión y asunción por la asesoría legal de CGT antes de que el registro se dé por adoptado. Los campos entre corchetes deben cumplimentarse antes de su entrega a cualquier autoridad.
