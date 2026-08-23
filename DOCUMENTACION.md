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

---

## 🗂️ Estructura Local de Archivos

```
Carnets definitivo/
├── DOCUMENTACION.md  ← Estás aquí
├── CLAUDE.md  [instrucciones del proyecto]
├── README.md  [introducción al proyecto]
├── requirements.txt
├── pyproject.toml
├── pytest.ini
├── setup_local.md  [guía de ambiente local]
│
└── sistema_carnets/
    ├── manage.py
    ├── db.sqlite3
    │
    ├── sistema_carnets/  [configuración Django]
    │   ├── settings.py
    │   ├── urls.py
    │   ├── wsgi.py
    │   └── asgi.py
    │
    └── gestion/  [aplicación principal]
        ├── models.py  [Afiliado, PerfilSindicato, ...]
        ├── views.py  [registro, subida, panel_imprenta]
        ├── forms.py
        ├── crypto.py  [AES-256-GCM, CampoTextoCifrado]
        ├── auditoria.py  [logging de acciones]
        ├── admin.py  [customización django-admin]
        ├── tests/
        │   ├── test_*.py
        │   └── conftest.py  [cache_limpia fixture]
        │
        ├── management/commands/
        │   └── preparar_pruebas.py  [setup de pruebas]
        │
        ├── templates/gestion/
        │   ├── login.html
        │   ├── registro.html
        │   ├── acuerdo_legal.html
        │   ├── subir_excel.html
        │   ├── notificaciones.html
        │   └── panel_imprenta.html
        │
        └── static/gestion/
            └── styles.css
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
| Sindicato | No puedo loguear | admin@sistema |
| Sindicato | Error en Excel | admin@sistema |
| Admin | Brecha de seguridad | DPO, AEPD (urgente) |
| Imprenta | No veo el panel | admin@sistema |

---

## 📅 Mantenimiento Recomendado

- **Semanal:** Revisar solicitudes de alta nuevas
- **Mensual:** Auditar accesos de imprenta, revisar logs
- **Trimestral:** Revisar incidentes, verificar capacidad de almacenamiento
- **Anualmente:** Rotación de claves, auditoría de seguridad completa

---

## 📖 Versión

- **Documentación v1.0** — 2026-08-21
- **Sistema Django 5.2** con django-simple-history y cryptography
- **Python 3.12+**
- **Compliance:** RGPD, Art. 9 (datos de categoría especial)

---

**Última actualización:** 2026-08-21

Para dudas o actualizaciones de documentación, contacta al administrador del sistema.
