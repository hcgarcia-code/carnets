# Protección frente a DDoS y abuso: lo que la aplicación no puede hacer

## Qué protege ya la aplicación, y qué no

La aplicación tiene tres controles contra el abuso, y conviene no confundirlos con
protección anti-DDoS:

| Control | Dónde | Qué evita |
|---|---|---|
| Limitador de login (5 intentos) | `gestion/auth_views.py` | Fuerza bruta sobre una cuenta |
| Limitador de alta (5/hora por IP) | `gestion/views.py` | Alta masiva de cuentas falsas |
| Rechazo de peticiones grandes (413) | `gestion/middleware.py` | Agotar memoria con un cuerpo enorme |

Los tres se ejecutan **dentro** del proceso de Python. Eso significa que, para que actúen,
la petición ya ha atravesado la red, el servidor web y Django. Contra un ataque volumétrico
—miles de peticiones por segundo desde muchas IP— eso llega tarde: el proceso se satura
antes de poder rechazar nada.

**Un DDoS no se para en la aplicación. Se para antes.** Este documento describe ese "antes".

> Nota: los limitadores dependen de una caché compartida entre workers. Con la caché en
> memoria del proceso, cada worker lleva su propia cuenta y el límite de 5 intentos pasa
> a ser 5 por worker. Está comprobado en `manage.py check --deploy` (ver `gestion/checks.py`);
> configúralo con `CACHE_BACKEND`/`CACHE_LOCATION`.

## Restricción de proveedor

Aplica el mismo criterio que `RESTRICCION_UE.md`: un WAF/CDN termina el TLS, así que **ve el
tráfico en claro**, incluidos los nombres y números de afiliado que viajan en los formularios.
Es un encargado del tratamiento de datos de categoría especial (RGPD Art. 9), no una simple
caché.

### Descartados

- **Cloudflare (plan estándar)**: sociedad estadounidense; el tráfico puede atravesar PoPs
  fuera de la UE. ✗ Solo considerable con *Data Localization Suite* (de pago) restringido a
  la UE, y aun así requiere análisis de transferencia internacional.
- **AWS CloudFront / Shield**: mismo problema de origen. ✗

### Opciones viables

| Opción | Dónde vive | Ventaja | Desventaja |
|---|---|---|---|
| **Scaleway Edge Services** | Francia | Mismo proveedor que el resto del despliegue; un solo encargado del tratamiento | Protección DDoS más básica que la de un especialista |
| **OVHcloud Anti-DDoS** | Francia | Incluido sin coste con el VPS; mitigación volumétrica seria | El WAF es aparte |
| **nginx + fail2ban en el propio servidor** | Tu infraestructura | Cero terceros, cero transferencia de datos | No protege del agotamiento del enlace de red |

### Recomendación

**OVHcloud Anti-DDoS (volumétrico) + nginx `limit_req` (capa 7)**, si el despliegue está en
OVHcloud. La mitigación volumétrica viene incluida y no añade ningún encargado nuevo, que es
justo lo que complica el cumplimiento.

Si el despliegue está en Scaleway, **Edge Services** por la misma razón: no añade un tercero
que no estuviera ya en el contrato.

## Capa 7: nginx delante de la aplicación

Esto sí hay que configurarlo a mano, y es lo que más rendimiento da por el esfuerzo invertido.

```nginx
# Un cubo por IP. 10 MB guardan del orden de 160.000 IP distintas.
limit_req_zone $binary_remote_addr zone=general:10m rate=30r/m;
limit_req_zone $binary_remote_addr zone=login:10m   rate=5r/m;

# Limita tambien el numero de conexiones simultaneas por IP: sin esto, una
# sola IP puede abrir cientos de conexiones lentas y ocupar todos los workers
# sin superar ningun limite de peticiones por minuto (Slowloris).
limit_conn_zone $binary_remote_addr zone=conexiones:10m;

server {
    listen 443 ssl http2;
    server_name carnets.example.es;

    # 413 antes de que el cuerpo llegue a Python. Duplica lo que ya hace
    # LimiteTamanoPeticionMiddleware, a proposito: aqui se corta sin gastar
    # un worker de la aplicacion.
    client_max_body_size 10m;

    # Corta las conexiones que envian la peticion gota a gota.
    client_body_timeout 10s;
    client_header_timeout 10s;

    limit_conn conexiones 20;

    location / {
        limit_req zone=general burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # OJO: esta cabecera la REESCRIBE nginx, no la reenvia desde el
        # cliente. Es la condicion para poder activar SECURE_PROXY_SSL_HEADER
        # en el .env; si se dejara pasar la del cliente, cualquiera podria
        # hacer creer a Django que su conexion en claro era segura.
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # El login y el alta son las dos puertas sin autenticar: mas estrictas.
    location ~ ^/(login|alta)/ {
        limit_req zone=login burst=3 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Con esto puesto, añade al `.env` del servidor:

```
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO:https
```

Sin él, `SECURE_SSL_REDIRECT=True` provoca un bucle de redirecciones (Django ve la petición
interna por HTTP y la vuelve a redirigir a HTTPS indefinidamente).

## fail2ban: banear al reincidente

nginx limita el ritmo, pero el atacante sigue llamando. fail2ban lee el registro de auditoría
—que ya emite JSON por línea, ver `auditoria_centralizada.md`— y bloquea la IP en el cortafuegos.

`/etc/fail2ban/filter.d/carnets.conf`:

```ini
[Definition]
failregex = ^.*"accion": "login\.bloqueado".*"ip": "<HOST>".*$
            ^.*"accion": "acceso\.denegado".*"ip": "<HOST>".*$
```

`/etc/fail2ban/jail.d/carnets.conf`:

```ini
[carnets]
enabled  = true
filter   = carnets
logpath  = /var/log/carnets/auditoria.jsonl
maxretry = 5
findtime = 600
bantime  = 3600
```

Encaja con `manage.py revisar_auditoria`, que lee el mismo archivo y avisa por correo: fail2ban
corta en el momento, el comando informa a un humano de que ha pasado.

## Lo que sigue sin estar cubierto

Conviene ser explícito sobre los límites de todo lo anterior:

- **Un ataque volumétrico que sature el enlace de red** solo lo para el proveedor, aguas arriba.
  nginx y fail2ban no ayudan si el cable está lleno.
- **Un ataque distribuido con una petición por IP** no lo detecta ningún limitador por IP.
  Ahí hace falta un WAF con reputación de IP y detección de patrones.
- **La disponibilidad no es un dato personal.** Un DDoS no expone información: el cifrado en
  reposo, la auditoría y el segundo factor siguen protegiendo lo que importa aunque el sitio
  esté caído. A la hora de priorizar presupuesto, esto va después de esos tres.
