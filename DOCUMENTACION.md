# Documentación: Sistema de Gestión de Carnets

Esta carpeta contiene la documentación completa del sistema. Hay tres documentos principales, cada uno dirigido a una audiencia diferente.

---

## 📋 Documentos

### 1. **Documento Técnico** 🔐
[Ver documento](https://claude.ai/code/artifact/816c4a73-c504-4914-9b97-250af0ad9b96)

**Para:** Desarrolladores, responsables técnicos, auditores de seguridad

**Contenido:**
- Arquitectura general del sistema
- Encriptación AES-256-GCM de datos personales
- Auditoría inmutable con django-simple-history
- Autenticación y control de acceso
- Flujos de datos críticos (registro, subida, impresión)
- Compliance RGPD y normativa
- Guía de despliegue seguro
- Stack recomendado (nginx + gunicorn + PostgreSQL)

**Leer cuando:**
- Necesites entender cómo funciona el cifrado
- Revises la implementación de seguridad
- Planees desplegar a producción
- Audites el cumplimiento normativo

---

### 2. **Manual del Administrador** 👨‍💼
[Ver documento](https://claude.ai/code/artifact/761d319a-de7e-47c6-ab13-bda555ca3ffb)

**Para:** Administrador del sistema, DPO, responsable de seguridad

**Contenido:**
- Cómo crear cuenta de admin
- Gestión de solicitudes de acceso (flujo de aprobación)
- Cómo ver y desencriptar datos en django-admin
- Auditoría e investigación de cambios
- Rotación de claves de cifrado
- Procedimientos de incidentes (contraseña comprometida, brecha, etc.)
- Mantenimiento periódico (semanal, mensual, anual)
- Troubleshooting común
- Comandos útiles (Django shell, Bash)

**Leer cuando:**
- Seas admin y necesites revisar una solicitud de alta
- Tengas que investigar un acceso sospechoso
- Vayas a rotar claves de cifrado anualmente
- Sucedan incidentes de seguridad

---

### 3. **Manual del Usuario** 👥
[Ver documento](https://claude.ai/code/artifact/06d23bcc-5791-4c06-b049-67ce6b8b0cdc)

**Para:** Sindicatos e imprenta (usuarios finales)

**Contenido:**
- Cómo solicitar acceso (registro)
- Primer login y activación de cuenta
- Aceptación de términos legales
- Preparar y subir archivo de afiliados (Excel)
- Validaciones que hace el sistema
- Ver notificaciones de progreso
- Panel de imprenta (acceso restringido)
- Guía de seguridad (contraseñas, datos personales)
- Preguntas frecuentes
- Checklist: primer uso

**Leer cuando:**
- Eres sindicato y quieres solicitar acceso
- Necesitas subir datos de afiliados
- Eres imprenta y necesitas acceder al panel
- Tienes dudas sobre seguridad o protección de datos

> **Este es el único de los tres que se publica en la propia aplicación**, en
> `/ayuda/manual/`, enlazado desde la página de ayuda. No es una copia: la página
> renderiza este mismo `MANUAL_USUARIO.md`, así que editarlo aquí lo actualiza
> allí. Los otros dos volúmenes no se publican: uno explica cómo está construido
> el sistema y el otro cómo administrarlo, y ninguna de las dos cosas tiene por
> qué estar al alcance de quien pase por la web.

---

## ⚖️ Documentos de cumplimiento (RGPD)

Los tres manuales de arriba explican **cómo funciona** el sistema. Estos cuatro acreditan **que su uso es lícito**, y son los que hay que poder enseñar si la Agencia Española de Protección de Datos lo pide.

### Quién es quién

Esto determina todo lo demás, y las primeras versiones de estos documentos lo tenían mal:

```
Persona afiliada → SINDICATO de rama/provincia → CGT CONFEDERAL → IMPRENTA
                     (RESPONSABLE)                 (ENCARGADA)     (SUBENCARGADA)
                     recaba los datos          solo confecciona     solo imprime
                                                   el carnet
```

Los datos **no los recaba CGT Confederal**. Los recaban los sindicatos, que tienen personalidad jurídica propia y son los responsables del tratamiento. Confederal los recibe después, con una finalidad única y acotada.

### Los documentos

| Documento | Qué es | Quién lo asume | Estado |
|---|---|---|---|
| [`EIPD_...`](EIPD_Evaluacion_Impacto_Proteccion_Datos.md) | Evaluación de impacto (Art. 35). Obligatoria por tratarse de datos de categoría especial | La elabora Confederal; **la adopta cada sindicato** | v1.2 · sin firmar |
| [`RAT_...`](RAT_Registro_Actividades_Tratamiento.md) | Registros de actividades. **Son dos**: uno de responsable por sindicato (Art. 30.1) y uno de encargada en Confederal (Art. 30.2) | Ambos | v2.0 · borrador |
| [`CONTRATO_Encargado_Confederal.md`](CONTRATO_Encargado_Confederal.md) | Contrato sindicato → Confederal (Art. 28.3) | Cada sindicato y Confederal | Borrador · **bloqueante** |
| [`CONTRATO_Encargado_Imprenta.md`](CONTRATO_Encargado_Imprenta.md) | Contrato Confederal → imprenta (Art. 28.4) | Confederal y la imprenta | Borrador · **bloqueante** |
| [`INFORMACION_Afiliados_Art13.md`](INFORMACION_Afiliados_Art13.md) | Texto que se entrega al afiliarse. Lo redacta Confederal, **lo entrega el sindicato** | Cada sindicato | Borrador |

### Orden de firma

**Primero los contratos sindicato → Confederal, después el de la imprenta.** No es preferencia: al ser Confederal una encargada, no puede subcontratar a la imprenta sin autorización previa de los sindicatos (Art. 28.2). Firmar el de la imprenta primero deja ese eslabón sin cobertura.

**Todos los borradores necesitan revisión de la asesoría jurídica antes de adoptarse o firmarse.** Están redactados con apoyo técnico para no partir de una página en blanco y para dejar constancia exacta de qué datos salen del sistema y por qué vía; las calificaciones jurídicas que contienen son propuestas, no asesoramiento.

**Por qué esto no es papeleo.** La licitud del tratamiento se apoya en el Art. 9.2.d del RGPD, que ampara al sindicato *siempre que los datos no se comuniquen a terceros*. Un encargado no es un tercero — pero solo si hay contrato que lo acredite. Sin él, cada traslado es una comunicación a un tercero y decae el amparo **del tratamiento entero**, no solo de ese tramo. Ver §7.3 de la EIPD.

---

## 🗂️ Estructura Local de Archivos

```
Carnets definitivo/
├── DOCUMENTACION.md  ← Estás aquí
├── CLAUDE.md  [instrucciones del proyecto]
├── requirements.txt
├── pyproject.toml  [config de pytest, ruff y bandit]
│
├── EIPD_Evaluacion_Impacto_Proteccion_Datos.md   ┐
├── RAT_Registro_Actividades_Tratamiento.md       │ documentos
├── CONTRATO_Encargado_Confederal.md              │ de cumplimiento
├── CONTRATO_Encargado_Imprenta.md                │ (RGPD)
├── INFORMACION_Afiliados_Art13.md                ┘
├── DOCUMENTO_TECNICO.md
├── MANUAL_ADMINISTRADOR.md
├── MANUAL_USUARIO.md
│
├── tests/  [la suite vive en la raíz, no dentro de la app]
│   ├── conftest.py  [fixtures: cache_limpia, entrar_en_el_admin]
│   └── test_*.py
│
├── deploy/  [ver deploy/README.md para el índice]
│   ├── tareas_programadas.md  [las tres entradas de cron]
│   ├── claves_y_kms.md · RESTRICCION_UE.md
│   ├── scaleway_setup.md · postgresql_vpc.md
│   ├── backups_cifrados_s3.md · auditoria_centralizada.md
│   └── waf_y_ddos.md
│
└── sistema_carnets/
    ├── manage.py
    ├── db.sqlite3
    │
    ├── sistema_carnets/  [configuración Django]
    │   ├── settings.py
    │   └── urls.py, wsgi.py, asgi.py
    │
    └── gestion/  [aplicación principal]
        ├── models.py  [Afiliado, PerfilSindicato, RegistroSubida...]
        ├── views.py  [registro, subida, panel_imprenta]
        ├── forms.py · services.py
        ├── crypto.py  [AES-256-GCM, CampoTextoCifrado]
        ├── auditoria.py  [registro de accesos]
        ├── middleware.py  [CSP, límite de tamaño]
        ├── auth_views.py  [login con límite de intentos]
        ├── checks.py  [comprobaciones de despliegue]
        ├── admin.py  [admin con segundo factor]
        │
        ├── management/commands/
        │   ├── activar_2fa.py
        │   ├── expurgar_afiliados.py  [plazo de conservación]
        │   ├── revisar_auditoria.py
        │   ├── backup_a_s3_cifrado.py
        │   ├── reencriptar_afiliados.py  [rotación de claves]
        │   └── preparar_pruebas.py
        │
        ├── templates/gestion/
        │   ├── login.html · registro.html · acuerdo_legal.html
        │   ├── subir_excel.html · notificaciones.html
        │   └── panel_imprenta.html
        │
        └── static/documentos/
            ├── plantilla_sindicatos.xls
            └── texto_afiliacion.pdf
```

---

## 🚀 Flujo Típico (Resumen)

```
1. SINDICATO solicita alta en /registro/
   ↓
2. ADMIN revisa en django-admin y aprueba/rechaza
   ↓
3. SINDICATO logueado acepta términos legales
   ↓
4. SINDICATO sube archivo Excel con afiliados
   ├─ Sistema valida formato y cifra datos
   ├─ Se crea RegistroSubida (auditoría)
   └─ Afiliados quedan en estado PENDIENTE
   ↓
5. ADMIN marca afiliados como IMPRESO (para enviar)
   ├─ Sistema actualiza fecha_envio_imprenta
   └─ Auditoría registra el cambio
   ↓
6. IMPRENTA accede a panel (números cifrados, nombres NO visibles)
   └─ Ve lote listo para imprimir
```

---

## 🔒 Garantías de Seguridad

✓ **Datos personales cifrados en reposo** — AES-256-GCM, nonce nuevo en cada escritura
✓ **Auditoría de lecturas y escrituras** — sin datos personales dentro, por diseño
✓ **Segundo factor (TOTP) en el admin** — la única cuenta que descifra
✓ **Control de acceso por roles** — Admin, Sindicato, Imprenta
✓ **Validación estricta de entrada** — Excel, contraseñas, formatos
✓ **Limitadores de intentos** — 5 fallos de login = 5 min bloqueado; 5 altas/hora por IP
✓ **Content-Security-Policy** — el navegador no ejecuta scripts ajenos al sitio
✓ **Protección CSRF** — token en todos los formularios
✓ **HTTPS/HSTS** — obligatorio en producción, comprobado antes de desplegar
✓ **Alertas automáticas** — `revisar_auditoria` avisa por correo de rachas sospechosas

> **Cifrado en reposo, no extremo a extremo.** El servidor puede leer los datos: los necesita
> para imprimir los carnets. Lo que protege el cifrado es el disco y las copias de seguridad.

### Lo que la aplicación NO puede hacer sola

Un ataque volumétrico (DDoS) no se para dentro de Django: para cuando la petición llega al
proceso de Python, ya ha consumido red y servidor web. Eso es infraestructura —
ver [`deploy/waf_y_ddos.md`](deploy/waf_y_ddos.md).

---

## 📞 Contactos Rápidos

| Rol | Problema | Contacto |
|-----|----------|----------|
| Sindicato | No puedo entrar | **soporte-carnets@cgt.org.es** · 918 055 047 |
| Sindicato | Error al subir el Excel | **soporte-carnets@cgt.org.es** · 918 055 047 |
| Sindicato | Olvidé la contraseña | Ninguno: se repone solo, en `/recuperar-password/` |
| Imprenta | No veo el panel | **soporte-carnets@cgt.org.es** |
| Admin | Brecha de seguridad | El **sindicato responsable** (es quien notifica a la AEPD) + DPO |

Todo esto está también en la web, en `/ayuda/`, que se ve sin tener cuenta.

---

## 📅 Mantenimiento Recomendado

- **Cada hora (cron):** `revisar_auditoria` — avisa de rachas de bloqueos y de cada exportación
- **Diario (cron):** `backup_a_s3_cifrado` — copia cifrada a Object Storage en la UE
- **Semanal:** Revisar solicitudes de alta nuevas
- **Mensual:** Auditar accesos de imprenta, revisar logs, comprobar que los backups existen
- **Trimestral (cron):** `expurgar_afiliados` — plazo de conservación, 3 años desde la baja
- **Trimestral:** Revisar incidentes, comprobar que el segundo factor del admin sigue vivo
- **Anualmente:** Rotación de claves, auditoría de seguridad completa

---

## 📖 Versión

- **Documentación v2.0** — 2026-08-27 (los tres volúmenes revisados contra el código)
- **Sistema Django 5.2** con django-simple-history y cryptography
- **Python 3.12+**
- **Compliance:** RGPD, Art. 9 (datos de categoría especial)

---

**Última actualización:** 2026-08-21

Para dudas o actualizaciones de documentación, contacta al administrador del sistema.
