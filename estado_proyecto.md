# Estado del Proyecto — App CarnetsCGT

_Última actualización: 2026-08-06_

## 1. Resumen

Aplicación Django `sistema_carnets` (gestión de altas/bajas de afiliados sindicales mediante carga de Excel, con notificaciones a cada sindicato cuando su lote se envía a imprenta). Partiendo de un proyecto que **no arrancaba** (error estructural + `SyntaxError`), se ha llevado a un estado funcional, con entorno de desarrollo reproducible, varias rondas de blindaje de seguridad (estática y dinámica/pentest) y una función nueva construida con TDD.

## 2. Hallazgo crítico — RESUELTO

`sistema_carnets/db.sqlite3` estaba commiteado en el historial de git (`main` y la rama de feature) con datos reales: un afiliado real y hashes de contraseña de 2 usuarios reales, uno de ellos superusuario.

**Purgado del historial** con `git-filter-repo --path sistema_carnets/db.sqlite3 --invert-paths`, aplicado a `main` y a la rama de feature, con `force-push` a ambas (autorizado explícitamente). Verificado que ni el blob ni el nombre del afiliado quedan en ningún commit alcanzable. Pendiente por parte del usuario: rotar las contraseñas de esos 2 usuarios (un force-push no deshace una posible copia previa) y, opcionalmente, pedir a GitHub Support que limpie cachés de commits colgantes.

## 3. Corrección estructural crítica — RESUELTA

`settings.py`/`urls.py`/`wsgi.py`/`asgi.py` estaban sueltos junto a `manage.py` en vez de en el subpaquete `sistema_carnets/sistema_carnets/` que `DJANGO_SETTINGS_MODULE` esperaba. Se movieron con `git mv`, lo que también corrigió `BASE_DIR`.

## 4. Medidas de seguridad implementadas

### Ronda 1 — auditoría estática inicial
1. `SECRET_KEY` (antes vacío, `SyntaxError`), `DEBUG` y `ALLOWED_HOSTS` cargados desde `.env` vía `python-dotenv`.
2. Confirmado: 0 SQL crudo (todo ORM parametrizado), 0 riesgo de path traversal (el Excel se procesa en memoria).
3. Carga de Excel: valida extensión `.xlsx`, límite de 5 MB, columnas requeridas, y cada fila pasa por `full_clean()` (antes `.objects.create()` no ejecutaba los `RegexValidator` del modelo).
4. Ya no se filtran detalles internos de excepciones al usuario (se loguean server-side).
5. `db.sqlite3` y `__pycache__/*.pyc` desatrackeados de git.
6. `DEFAULT_AUTO_FIELD` explícito.

### Ronda 2 — funcionalidad de impresión/notificaciones (TDD)
7. `Afiliado.estado_impresion` / `fecha_envio_imprenta` + modelo `Notificacion`, con tests escritos primero (fallaron por `ImportError`, confirmado antes de implementar).
8. `gestion/services.py::marcar_como_impresos_y_notificar` agrupa por sindicato; el mensaje de notificación **nunca interpola texto libre del afiliado** — solo un contador y una fecha — así que no hay vector de inyección hacia el mensaje (verificado con payloads SQLi/XSS/SSTI/path traversal).
9. Vista `/notificaciones/` con `login_required`, scoped estrictamente por `request.user.notificaciones` (sin aceptar ningún id desde la petición → anti-IDOR entre sindicatos).
10. `estado_impresion`/`fecha_envio_imprenta` son de solo lectura en el admin.

### Ronda 3 — pentest dinámico contra servidor real (`tests/test_pentest.py`)
Suite con `httpx` contra un `manage.py runserver` real (BD sqlite temporal y aislada, nunca la de desarrollo). Se detectaron y corrigieron dos gaps reales (confirmados por ablación: se desactivó cada protección a propósito, se comprobó que el test correspondiente fallaba, y se restauró):

11. **Fuerza bruta / rate limiting en el login — no existía.** Nuevo `gestion/auth_views.py::LoginConLimiteDeIntentos`: tras 5 intentos fallidos para el mismo par (IP real de conexión, usuario) en 5 minutos, bloquea con `429` sin ni siquiera comprobar la contraseña. Se usa `REMOTE_ADDR` (no `X-Forwarded-For`, falsificable) y se clave por IP+usuario para no bloquear cuentas legítimas que comparten IP con un atacante que ataca OTRA cuenta.
    - **Nota de despliegue**: el contador vive en el cache framework de Django (por defecto `LocMemCache`, en memoria del proceso). Válido para un único proceso; si el despliegue final usa varios workers (p. ej. gunicorn con `--workers > 1`), hace falta un backend de cache compartido (Redis/Memcached) para que el límite aplique de verdad entre todos los workers.
12. **Sin límite de tamaño de petición a nivel de transporte.** Nuevo middleware `gestion/middleware.py::LimiteTamanoPeticionMiddleware`: rechaza con `413` cualquier petición cuyo `Content-Length` supere 10 MB, **antes** de que Django lea/bufferice el cuerpo — complementa (no sustituye) el límite de 5 MB ya existente a nivel de vista para el Excel.
13. Confirmado sin cambios: inyección SQLi/XSS en login y en el Excel nunca produce 500 ni se refleja sin escapar; las rutas protegidas nunca sirven contenido sin sesión (devuelven 302 al login, la respuesta correcta y segura para una app basada en cookies — ver nota más abajo); la cookie de sesión es `HttpOnly`.

### Nota de diseño: 302 vs. 401/403 en rutas protegidas
El pentest pedía verificar `401`/`403` estrictos. Esta app es un sitio web tradicional basado en sesión/cookies (no una API), así que Django responde a un acceso sin sesión con un `302` al login — es el comportamiento **correcto y seguro** para este tipo de app (nunca se filtra contenido protegido; un `403` en su lugar solo cambiaría la página de error mostrada, sin ganancia real de seguridad, y rompería la navegación normal del navegador). Los tests aceptan `302` (verificando que redirige al login, nunca a otro sitio) junto con `401`/`403` por si alguna ruta se expone como API en el futuro.

### Fuera de alcance (recomendaciones, no aplicadas)
- Cifrado en reposo de los datos personales de `Afiliado` (nombre, nº de afiliado) — CLAUDE.md lo sugiere para datos sensibles; requiere decidir estrategia (cifrado a nivel de aplicación vs. de disco) con el usuario.
- Confianza en `X-Forwarded-For` para el registro legal de IP en `acuerdo_legal` (distinto del rate limiter, que ya usa `REMOTE_ADDR`) — revisar según el proxy real del despliegue final.
- Rate limiting combinado por IP (además de por IP+usuario) para mitigar spraying de credenciales contra muchas cuentas distintas desde una misma IP.

## 5. Estructura de archivos

```
carnets/
├── .env                     # Secretos reales (NO versionado)
├── .env.example              # Plantilla de variables de entorno (versionado)
├── .gitignore
├── CLAUDE.md
├── estado_proyecto.md        # Este documento
├── pyproject.toml            # Config de bandit, ruff y pytest (+ pytest-django)
├── requirements.txt
├── tests/
│   ├── __init__.py
│   ├── test_seguridad.py             # config, validación de inputs, ausencia de SQL crudo
│   ├── test_impresion_notificaciones.py  # estado impresión + notificaciones (BD real, pytest-django)
│   └── test_pentest.py               # pentest dinámico contra servidor real (httpx)
├── venv/                     # Entorno virtual (NO versionado)
└── sistema_carnets/          # Carpeta del proyecto Django (contiene manage.py)
    ├── manage.py
    ├── db.sqlite3              # Base de datos local (NO versionado)
    ├── sistema_carnets/        # Paquete de configuración Django
    │   ├── settings.py          # SECRET_KEY/DEBUG/ALLOWED_HOSTS/DATABASE_NAME/*_COOKIE_SECURE desde .env
    │   ├── urls.py               # login ahora usa LoginConLimiteDeIntentos
    │   ├── wsgi.py / asgi.py
    └── gestion/
        ├── models.py            # Afiliado (+estado_impresion), PerfilSindicato, Notificacion
        ├── views.py             # acuerdo_legal, cargar_datos_sindicato, listar_notificaciones
        ├── auth_views.py        # LoginConLimiteDeIntentos (rate limiting)
        ├── middleware.py        # LimiteTamanoPeticionMiddleware
        ├── services.py          # marcar_como_impresos_y_notificar
        ├── admin.py             # exportar_imprenta ahora marca+notifica
        ├── migrations/
        └── templates/gestion/   # login, acuerdo_legal, subir_excel, notificaciones
```

## 6. Entorno de desarrollo

Sesión en contenedor Linux; venv creado con los comandos equivalentes de Linux. Los comandos Windows de `CLAUDE.md` funcionan igual en local, toda la config vive en `requirements.txt`/`pyproject.toml`.

Dependencias (`requirements.txt`):
- **Producción**: `Django==5.2.17`, `pandas==3.0.5`, `openpyxl==3.1.5`, `python-dotenv==1.2.2`
- **Calidad/seguridad/tests**: `pytest==9.1.1`, `pytest-django==4.13.0` (tests con BD real), `httpx==0.28.1` (pentest dinámico), `ruff==0.16.1`, `bandit==1.9.4`

## 7. Verificación final

| Comando | Resultado |
|---|---|
| `pytest tests/ -v` | **52 passed** — código de salida 0 (incluye 20 tests de pentest contra servidor real) |
| `ruff check .` | All checks passed! — código de salida 0 |
| `bandit -r . -c pyproject.toml` | No issues identified — código de salida 0 |
| `manage.py check` | System check identified no issues (0 silenced) |
| `manage.py makemigrations --check` | No changes detected |

## 8. Próximos pasos sugeridos

1. Rotar las contraseñas de `CONFEDERAL` y `sindicato_madrid` (post-purga de historial).
2. Si el despliegue final usa varios workers, configurar un backend de cache compartido (Redis/Memcached) para que el rate limiter de login funcione entre procesos.
3. Evaluar cifrado en reposo para los campos personales de `Afiliado`.
4. Revisar la confianza en `X-Forwarded-For` en `acuerdo_legal` según el proxy real de despliegue.
5. Considerar añadir un límite adicional por IP (sin combinar con usuario) si preocupa el spraying de credenciales contra muchas cuentas.
