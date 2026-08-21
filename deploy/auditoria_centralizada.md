# Auditoría de accesos: del log local a un destino inmutable

`gestion/auditoria.py` emite un registro por cada acceso a datos personales. Este documento
explica qué se registra, qué no, y cómo llevarlo a un destino que sirva como prueba.

---

## 1. Por qué hacía falta

`django-simple-history` registra los **cambios** en los datos, pero no las **lecturas**. Hasta
ahora, alguien con acceso al admin podía consultar y exportar los expedientes de los 3.000
afiliados sin dejar el menor rastro. Para datos de categoría especial hay que poder demostrar
también quién consultó qué.

## 2. Qué se registra

| Acción | Cuándo |
|---|---|
| `afiliados.consultados` | Alguien abre el listado de afiliados en el admin |
| `afiliado.abierto` | Alguien abre la ficha de un afiliado concreto |
| `afiliados.exportados` | Se descarga el Excel para la imprenta (la operación más sensible) |
| `afiliados.cargados` | Un sindicato sube un Excel de altas |
| `login.correcto` / `login.fallido` / `login.bloqueado` | Autenticación |

Cada registro es una línea de JSON:

```json
{"accion":"afiliados.exportados","cantidad":312,"ids":[...],"ip":"203.0.113.7",
 "ts":"2026-08-21T14:32:07.123456+00:00","usuario":"CONFEDERAL"}
```

## 3. Qué NO se registra, y por qué

**Ningún dato personal.** Ni nombres, ni números de afiliado, ni contraseñas —tampoco las
fallidas, que suelen ser la de otra cuenta o la correcta con una errata—.

No es un descuido: un registro de auditoría con los datos dentro sería una **segunda copia sin
cifrar** de justo lo que se acaba de cifrar, guardada además en un sistema pensado para replicarse
y conservarse años. Ampliaría la superficie expuesta en vez de reducirla. Hay un test que lo
comprueba (`test_exportar_no_escribe_datos_personales_en_el_registro`).

Se registran identificadores internos y recuentos. Para saber *a quién* corresponde un
identificador hay que entrar en la aplicación, con sus permisos y dejando a su vez rastro.

> La IP es siempre `REMOTE_ADDR`, no `X-Forwarded-For`: esa cabecera la pone el cliente y sería
> falsificable, con lo que cualquiera podría falsear su propio rastro.

## 4. Configuración

```
AUDITORIA_LOG_PATH=/var/log/carnets/auditoria.jsonl
```

Sin esa variable los registros van solo a la salida estándar (lo normal en desarrollo). Con ella,
además se escriben en ese archivo, una línea de JSON por evento.

## 5. Hacer que el archivo sea prueba, no apunte

**Un archivo local no vale por sí solo**: quien tenga acceso al servidor puede editarlo, y
precisamente alguien que se lleve datos indebidamente tendrá interés en borrar su línea. Hay dos
medidas, complementarias:

### 5.1 Solo-adición en el propio servidor

```bash
sudo mkdir -p /var/log/carnets
sudo touch /var/log/carnets/auditoria.jsonl
sudo chown www-data:adm /var/log/carnets/auditoria.jsonl
sudo chmod 640 /var/log/carnets/auditoria.jsonl
sudo chattr +a /var/log/carnets/auditoria.jsonl   # solo se puede añadir, no reescribir
```

Con `chattr +a`, ni siquiera el proceso de la aplicación puede modificar lo ya escrito. Por eso el
manejador configurado es `WatchedFileHandler` y no `RotatingFileHandler`: la rotación la hace
`logrotate` desde fuera, y así la aplicación nunca necesita reabrir ni truncar el archivo.

`/etc/logrotate.d/carnets`:

```
/var/log/carnets/auditoria.jsonl {
    daily
    rotate 730          # 2 años de retención (ver EIPD)
    compress
    missingok
    notifempty
    copytruncate
    su root adm
}
```

> `chattr +a` requiere quitar y volver a poner el atributo al rotar. Si el hosting no permite
> `chattr` (PythonAnywhere no lo permite), el envío a un destino externo del punto 5.2 deja de ser
> opcional: es lo único que da inmutabilidad real.

### 5.2 Envío a un destino externo

Que los registros salgan del servidor es lo que impide que quien lo comprometa borre su rastro.

**Restricción: el destino debe estar en la UE.** Los registros no contienen datos personales
directos, pero sí metadatos de tratamiento (quién accede a datos sindicales y cuándo), y su
tratamiento sigue sujeto al RGPD. Es la misma restricción que la del KMS (ver `RESTRICCION_UE.md`).

- ✗ **AWS CloudWatch**, **Splunk Cloud** (por defecto EEUU)
- ✓ **Grafana Loki autoalojado** — el más ligero; una sola instancia basta para este volumen
- ✓ **Elastic Stack autoalojado**
- ✓ Cualquier servicio de logs con datacenter en la UE contratado con su DPA firmado

Con Loki, basta con apuntar Promtail al archivo:

```yaml
# promtail.yaml
scrape_configs:
  - job_name: carnets_auditoria
    static_configs:
      - targets: [localhost]
        labels:
          job: carnets_auditoria
          __path__: /var/log/carnets/auditoria.jsonl
```

El destino debe tener credenciales **distintas** a las del servidor de aplicación: si son las
mismas, quien comprometa la aplicación puede borrar también lo enviado.

## 6. Retención

**2 años**, según la política de la EIPD. Ni menos (no cubriría una inspección) ni
indefinidamente: un histórico de accesos también es información sensible sobre las personas que
usan el sistema, y conservarlo más de lo necesario contradice el principio de minimización.

## 7. Pendiente

- **Alertas.** Registrar no es vigilar. Merece la pena avisar automáticamente ante patrones que
  casi siempre significan un problema: una exportación fuera de horario, muchos
  `login.bloqueado` seguidos, o un volumen de consultas muy por encima de lo habitual.
- **Revisión periódica.** Un registro que nadie mira no detecta nada. Conviene fijar quién lo
  revisa y cada cuánto, y dejarlo escrito en la EIPD.
