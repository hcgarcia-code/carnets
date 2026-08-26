# Tareas programadas

Tres comandos de este proyecto no los lanza nadie a mano: si no están en el
`crontab` del servidor, no se ejecutan nunca. Dos de ellos son controles de
cumplimiento, y un control que no corre es peor que no tenerlo, porque figura
en la documentación como si estuviera cubierto.

| Comando | Cadencia | Qué pasa si no corre |
|---|---|---|
| `revisar_auditoria` | cada hora | Un ataque de fuerza bruta o una exportación masiva quedan anotados y nadie los lee |
| `backup_a_s3_cifrado` | diaria | No hay de dónde restaurar (RGPD Art. 32.1.c) |
| `expurgar_afiliados` | trimestral | Los datos se conservan más allá del plazo (RGPD Art. 5.1.e) |

## crontab

Ajusta las rutas a las de tu servidor. `cd` al directorio del proyecto es
necesario: los comandos leen el `.env` desde ahí.

```cron
# m  h  dom mon dow
  5  *  *   *   *   cd /srv/carnets && venv/bin/python sistema_carnets/manage.py revisar_auditoria
  30 3  *   *   *   cd /srv/carnets && venv/bin/python sistema_carnets/manage.py backup_a_s3_cifrado
  0  4  1   */3 *   cd /srv/carnets && venv/bin/python sistema_carnets/manage.py expurgar_afiliados
```

La salida de cron va al correo del usuario del sistema. Si ese buzón no lo lee
nadie, redirige a un archivo y vigílalo, o los fallos del propio cron —que son
los que dejan el control muerto sin avisar— pasarán desapercibidos.

## Antes de la primera pasada del expurgado

`expurgar_afiliados` anonimiza de forma irreversible. Ejecútalo una vez a mano
con `--dry-run` antes de meterlo en cron:

```bash
python sistema_carnets/manage.py expurgar_afiliados --dry-run
```

Te dirá a cuántos afectaría y, por separado, cuántos afiliados de baja no
tienen `fecha_baja`. Esos segundos son filas anteriores a que el campo
existiera: no se pueden expurgar porque no hay fecha desde la que contar el
plazo. Si el número no es cero, hay que decidir a mano qué hacer con ellos
—normalmente mirar el historial del afiliado para ver cuándo pasó a BAJA— antes
de dar el plazo por implantado.

## Verificar que corren

Cron falla en silencio (ruta mal puesta, permisos, venv que no existe). Una vez
al mes:

```bash
grep CRON /var/log/syslog | tail -20
```

Y para el backup, que es el único cuyo fallo no se nota hasta que hace falta:
restaura una copia en un entorno de pruebas y anota la fecha. Ver
[`backups_cifrados_s3.md`](backups_cifrados_s3.md). Un backup que nunca se ha
restaurado es una hipótesis, no una copia de seguridad.
