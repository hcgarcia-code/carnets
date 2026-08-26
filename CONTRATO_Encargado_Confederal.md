# CONTRATO DE ENCARGADO DEL TRATAMIENTO

## Servicio confederal de confección de carnets de afiliación

**Entre el SINDICATO (responsable) y CGT CONFEDERAL (encargada)**
**Artículo 28.3 del Reglamento (UE) 2016/679 (RGPD)**

**Borrador · versión 1.0 · 2026-08-26**

---

> ## ⚠️ LEER ANTES DE USAR
>
> **Este es un borrador de trabajo, no un contrato listo para firmar.** Lo ha redactado el equipo técnico para que la asesoría jurídica de CGT parta de algo concreto, y para dejar constancia exacta de qué hace el sistema con los datos —información que la parte técnica conoce y la jurídica necesita—.
>
> **Qué carencia cubre.** Los sindicatos ya están trasladando a CGT Confederal datos de afiliación —categoría especial del Art. 9— sin ningún instrumento que documente en qué condición los recibe, para qué puede usarlos, cuánto puede conservarlos o qué debe hacer al terminar. Es la carencia más básica de todo el cumplimiento y la que menos se nota, porque todo ocurre dentro de la organización. El Art. 28.3 exige que esa relación conste **por escrito**.
>
> **Se firma uno por cada sindicato** que use el servicio. Como el contenido es idéntico para todos, lo practicable es aprobar el modelo en el órgano confederal competente y que cada sindicato se adhiera.
>
> **No lo firmes sin revisión legal.** Los campos entre corchetes deben cumplimentarse.

---

## REUNIDOS

**De una parte**, [denominación del sindicato de rama o provincia], con NIF [—] y domicilio en [—], representado por [—] en calidad de [—], en adelante **el RESPONSABLE**.

**De otra parte**, CGT Confederal, con NIF [—] y domicilio en [—], representada por [—] en calidad de [—], en adelante **el ENCARGADO**.

Ambas partes se reconocen capacidad legal suficiente y

## EXPONEN

**I.** Que el RESPONSABLE es una organización sindical con personalidad jurídica propia que mantiene el registro de sus personas afiliadas, cuyos datos **recaba directamente de ellas** en el momento de la afiliación, en el marco de la relación asociativa que las vincula.

**II.** Que dichos datos revelan afiliación sindical y constituyen por ello **categoría especial** conforme al Art. 9.1 del RGPD.

**III.** Que el ENCARGADO presta a los sindicatos confederados un servicio común de confección de carnets de afiliación, mediante una aplicación de su titularidad.

**IV.** Que el RESPONSABLE desea utilizar dicho servicio y, a tal fin, trasladar al ENCARGADO los datos estrictamente necesarios, **sin que ello suponga cesión ni transmisión de titularidad alguna**.

**V.** Que el ENCARGADO trata dichos datos **exclusivamente por cuenta del RESPONSABLE y para la finalidad indicada**, sin determinar por sí mismo los fines del tratamiento, lo que le confiere la condición de encargado del tratamiento del Art. 4.8 del RGPD.

**VI.** Que ambas partes son conscientes de que el amparo del Art. 9.2.d del RGPD exige que los datos **no se comuniquen a terceros sin consentimiento del interesado**, y de que es precisamente la condición de encargado —y no de tercero— del ENCARGADO lo que permite el traslado. Este contrato es el instrumento que acredita dicha condición.

Y en su virtud, acuerdan las siguientes

---

## CLÁUSULAS

### PRIMERA — Objeto y finalidad

El ENCARGADO tratará por cuenta del RESPONSABLE los datos personales de sus personas afiliadas **con la finalidad única de confeccionar y gestionar la emisión de sus carnets de afiliación**.

Queda comprendido en el objeto: el almacenamiento de los datos remitidos, la formación de lotes de impresión, la remisión a la empresa de impresión de lo necesario para imprimir, el registro de trazabilidad de los accesos, la supresión automatizada al vencer el plazo y la conservación de copias de seguridad.

**Queda excluido cualquier otro tratamiento.**

### SEGUNDA — Datos y categorías de interesados

**Interesados**: personas afiliadas al RESPONSABLE, actuales y antiguas.

**Datos**: nombre y apellidos; nº de afiliado; códigos de confederación territorial, federación local, federación sectorial y sindicato; lengua; estado de afiliación y fecha de baja; fecha de expedición; notas de reemisión; estado y fecha de impresión.

El RESPONSABLE **no remitirá** datos distintos de los enumerados. Si remitiera alguno por error, el ENCARGADO se lo comunicará y lo suprimirá.

### TERCERA — Duración

Vigencia indefinida mientras el RESPONSABLE utilice el servicio. Cualquiera de las partes podrá resolverlo con un preaviso de [90] días.

Las obligaciones de confidencialidad (QUINTA) y de restitución y supresión (DECIMOPRIMERA) **subsisten tras la extinción**.

### CUARTA — Obligación de seguir instrucciones

El ENCARGADO tratará los datos **únicamente conforme a las instrucciones documentadas** del RESPONSABLE. Tienen tal consideración este contrato, sus anexos y las que el RESPONSABLE curse por escrito.

El ENCARGADO **no podrá**:

a) Usar los datos para finalidad propia o distinta de la pactada.
b) Comunicarlos ni permitir su acceso a terceros, salvo lo previsto en la cláusula SÉPTIMA.
c) Cruzarlos con los de otros sindicatos ni con ficheros propios, salvo lo imprescindible para la formación de lotes de impresión, que **en ningún caso permitirá a un sindicato acceder a datos de otro**.
d) Elaborar perfiles ni estadísticas nominativas. Los recuentos agregados y anonimizados quedan permitidos.
e) Conservarlos más allá de lo previsto en la cláusula DÉCIMA.

Si el ENCARGADO considera que una instrucción infringe la normativa de protección de datos, lo comunicará de inmediato (Art. 28.3, párrafo segundo).

### QUINTA — Confidencialidad

El ENCARGADO garantiza que toda persona autorizada para tratar estos datos se ha comprometido expresamente por escrito a respetar su confidencialidad, con carácter indefinido y subsistente tras el fin de su relación.

El acceso a los datos **sin cifrar** queda limitado al personal de administración del servicio estrictamente necesario, del que se mantendrá relación actualizada a disposición del RESPONSABLE.

**Advertencia expresa**: la divulgación de la afiliación sindical de una persona puede exponerla a represalias laborales. No es un dato administrativo ordinario.

### SEXTA — Medidas de seguridad (Art. 32)

El ENCARGADO aplica y mantiene, como mínimo:

1. **Cifrado en reposo** de nombre, nº de afiliado y notas, mediante AES-256-GCM a nivel de columna.
2. **Custodia de las claves fuera de la aplicación**, en sistema de gestión de claves, de modo que el acceso a la base de datos no baste para leer los datos.
3. **Segundo factor de autenticación obligatorio** en el punto donde los datos se muestran descifrados.
4. **Aislamiento entre responsables**: cada sindicato accede exclusivamente a sus propias personas afiliadas.
5. **Cifrado en tránsito obligatorio**, comprobado de forma automática antes de cada despliegue.
6. **Registro de trazabilidad** de accesos, consultas y exportaciones, que por diseño **no contiene datos personales**, con revisión automática y alerta ante patrones anómalos.
7. **Copias de seguridad cifradas** antes de salir del servidor.
8. **Verificación continua** del código mediante pruebas automatizadas, análisis estático de seguridad y auditoría de vulnerabilidades en las dependencias.

El ENCARGADO informará al RESPONSABLE de cualquier cambio sustancial que reduzca el nivel de protección descrito.

### SÉPTIMA — Subencargados: autorización general

El RESPONSABLE **autoriza con carácter general** al ENCARGADO a recurrir a los subencargados relacionados en el **Anexo I**, con sujeción a las siguientes condiciones:

a) El ENCARGADO suscribirá con cada uno contrato escrito que le imponga obligaciones **no menos protectoras** que las de este contrato, y responderá plenamente ante el RESPONSABLE del cumplimiento por aquellos (Art. 28.4).
b) El ENCARGADO comunicará al RESPONSABLE toda incorporación o sustitución de subencargados con una antelación mínima de **[30] días**.
c) Dentro de ese plazo el RESPONSABLE podrá **oponerse motivadamente**. De hacerlo, las partes buscarán una solución alternativa; de no alcanzarse, el RESPONSABLE podrá resolver este contrato sin penalización.
d) Todos los subencargados tratarán los datos **dentro del Espacio Económico Europeo**.

> La autorización general del Art. 28.2 es la vía practicable cuando un mismo servicio sirve a muchos responsables. Recabar firma individual por cada cambio de proveedor haría el servicio ingobernable; el derecho de oposición previa preserva el control del responsable.

### OCTAVA — Asistencia al Responsable

El ENCARGADO asistirá al RESPONSABLE:

a) **En la atención de los derechos** de las personas afiliadas (Arts. 15 a 22): localización de registros, extracción de datos en formato utilizable y ejecución de rectificaciones o supresiones que el RESPONSABLE acuerde.
b) **Trasladando sin resolver** cualquier solicitud que una persona afiliada le dirija directamente, en el plazo de **[5] días hábiles**. El ENCARGADO **no atenderá solicitudes por su cuenta**: hacerlo sería actuar como responsable.
c) En el cumplimiento de los Arts. 32 a 36, incluida la elaboración y puesta a disposición de la evaluación de impacto del servicio, que el RESPONSABLE adopta como propia (Art. 28.3.f).
d) Poniendo a su disposición toda la información necesaria para demostrar el cumplimiento del Art. 28.

### NOVENA — Notificación de violaciones de seguridad

El ENCARGADO notificará al RESPONSABLE **sin dilación indebida y, en todo caso, dentro de las 24 horas** siguientes a tener conocimiento de cualquier violación de seguridad que afecte a sus datos.

> El plazo es inferior al que el RGPD impone al encargado por acuerdo de las partes: el RESPONSABLE dispone de 72 horas para notificar a la autoridad **desde que tiene constancia**, y necesita margen para valorar el alcance.

La notificación incluirá naturaleza de la violación, categorías y número aproximado de interesados y registros afectados, **si los datos afectados estaban cifrados y si las claves resultaron comprometidas**, consecuencias probables y medidas adoptadas.

Se notificará **igualmente** aunque el alcance no se conozca todavía. La notificación a la autoridad de control y a los interesados corresponde al RESPONSABLE.

### DÉCIMA — Plazo de conservación

El ENCARGADO conservará los datos durante **[3] años desde la fecha de baja** de cada persona afiliada, transcurridos los cuales los anonimizará de forma automatizada, **incluido su historial de cambios**.

El plazo lo fija el RESPONSABLE. Si designa uno distinto, lo comunicará por escrito y el ENCARGADO ajustará la configuración del sistema.

### DECIMOPRIMERA — Restitución y supresión al finalizar

Extinguido este contrato, el ENCARGADO, **a elección del RESPONSABLE**:

a) Le devolverá la totalidad de los datos en formato estructurado y de uso común, y los suprimirá de sus sistemas; o
b) Los suprimirá directamente.

En ambos casos expedirá **certificado escrito de supresión**, comprensiva de las copias de seguridad conforme a su ciclo de rotación, en un plazo máximo de **[90] días**. Solo podrá conservar aquello que le imponga una obligación legal, indicando cuál y por cuánto tiempo, y manteniéndolo bloqueado.

### DECIMOSEGUNDA — Auditoría

El RESPONSABLE podrá verificar el cumplimiento de este contrato mediante auditorías o inspecciones, por sí o por auditor designado, previo aviso de [15] días naturales.

Se admite que el ENCARGADO atienda esta obligación mediante **informe de auditoría común puesto a disposición de todos los sindicatos responsables**, sin perjuicio del derecho de cualquiera de ellos a solicitar verificación específica cuando concurra causa justificada.

### DECIMOTERCERA — Responsabilidad

Cada parte responde de los daños causados por el incumplimiento de las obligaciones que este contrato y el RGPD le imponen.

Si el ENCARGADO tratara los datos determinando por su cuenta fines y medios, será considerado **responsable del tratamiento** respecto de dicho tratamiento (Art. 28.10).

### DECIMOCUARTA — Legislación y jurisdicción

Rigen el RGPD, la Ley Orgánica 3/2018 y la legislación española. Las partes se someten a los Juzgados y Tribunales de [—].

---

En [—], a [—] de [—] de [—].

| **EL RESPONSABLE** | **EL ENCARGADO** |
|---|---|
| [Sindicato] | CGT Confederal |
| | |
| Fdo.: [—] | Fdo.: [—] |

---

## ANEXO I — Subencargados autorizados

| Subencargado | NIF | Función | Ubicación |
|---|---|---|---|
| [Empresa de impresión] | [—] | Impresión física de los carnets | [UE — verificar] |
| [Proveedor de alojamiento] | [—] | Infraestructura de aplicación y base de datos | UE |
| [Custodia de claves] | [—] | Custodia de las claves de cifrado | UE |
| [Registro externo de auditoría] | [—] | Destino de solo-adición del registro de accesos | UE |

## ANEXO II — Datos de contacto operativos

| Concepto | RESPONSABLE | ENCARGADO |
|---|---|---|
| Contacto en protección de datos | [—] | [—] |
| Contacto para notificar brechas (24 h) | [—] | [—] |
| Personas autorizadas a subir y consultar listas | [—] | — |
| Plazo de conservación fijado | [3] años desde la baja | — |
