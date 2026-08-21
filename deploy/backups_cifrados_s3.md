# Backups cifrados a S3 (antes de octubre)

Con 60.000 afiliados y 3.000 nuevos cada mes, una brecha sin backups cifrados es un escenario de pesadilla: los datos personales de decenas de miles de trabajadores en manos de alguien que los comprometió.

Este documento describe el flujo: `dumpdata` → Vault (cifra) → S3 (Scaleway) → rotación.

---

## 1. Configuración inicial (una sola vez)

### 1.1 Bucket de S3 en Scaleway

```bash
# Desde la consola de Scaleway o:
scw object create bucket name=carnets-backups-$(date +%Y%m%d)

# Anota el bucket ID. Ponlo en .env:
BACKUP_S3_BUCKET=carnets-backups-20261001
```

### 1.2 Credenciales S3 (no son credenciales de tu cuenta)

En Scaleway:

```
Console → Object Storage → Credentials → Create New Application Key
```

Genera un par `access_key` / `secret_key`. **NO son credenciales de tu cuenta;
son específicas de S3 y pueden revocar sin tocar nada más.** Guarda en `.env`:

```
AWS_ACCESS_KEY_ID=<SCW_ACCESS_KEY>
AWS_SECRET_ACCESS_KEY=<SCW_SECRET_KEY>
```

### 1.3 Vault está ya corriendo (setup de Scaleway)

`backup_a_s3_cifrado` espera que Vault esté en `BACKUP_VAULT_ADDR` (por defecto
`https://localhost:8200`) y tenga disponibles los role-id y secret-id de la app.
Si corriste el setup de Scaleway, ya está: el Vault corre en Docker en la
instancia app.

---

## 2. Prueba local (antes de octubre)

```bash
# 1. Instala deps
pip install -r requirements.txt

# 2. Genera un backup (sin subirlo aún)
python manage.py backup_a_s3_cifrado --dry-run

# 3. Si todo OK, sube de verdad
python manage.py backup_a_s3_cifrado

# 4. Verifica en Scaleway que el archivo aparece en el bucket
scw object ls s3://carnets-backups-<tu-timestamp>/
```

Expected output:

```
Generando dumpdata...
  JSON local: /tmp/backup_carnets_20261001_120000.json (125MB)
Cifrando con Vault...
  Cifrado: 185MB
Subiendo a S3 (carnets-backups-20261001/backups/carnets_20261001_120000.json.enc)...
  ✓ Subido a S3
  Local limpiado: /tmp/backup_carnets_20261001_120000.json
✓ Backup completado: backups/carnets_20261001_120000.json.enc
```

---

## 3. Automatización: cron en la instancia

En la instancia app (vía SSH o bastión):

```bash
# Crea un script wrapper que no deje variables sensibles colgadas
cat > /opt/carnets/bin/backup_semanal.sh << 'CRON_EOF'
#!/bin/bash
set -e

cd /opt/carnets
source venv/bin/activate

# Vault es local, pero lo desbloqueas manualmente (ver sección 4)
# AUNQUE PUEDAS auto-desbloquear, es menos seguro: deja la contraseña en el script.
# Aquí asumimos que está siempre desbloqueado (tienes que restartear manualmente
# si falla, y estará en la lista de TODOs del incident).

python manage.py backup_a_s3_cifrado >> /var/log/carnets/backup.log 2>&1
CRON_EOF

chmod +x /opt/carnets/bin/backup_semanal.sh

# Cron: cada domingo a las 2am (evita horario de carga de datos)
crontab -e

# Añade:
0 2 * * 0 /opt/carnets/bin/backup_semanal.sh
```

Logs: `/var/log/carnets/backup.log`.

---

## 4. Desbloqueo de Vault después de reinicio

**Problema:** Si reinicia la instancia, Vault se bloquea y necesita los 2 shards.

**Solución temporal (hasta octubre):** Vault está en una instancia que rara vez
reinicia. Si reinicia, necesitas acceder por SSH y ejecutar:

```bash
docker exec vault vault operator unseal <SHARD-1>
docker exec vault vault operator unseal <SHARD-2>
```

Los shards los guardaste en Bitwarden (o la bóveda de secretos) cuando inicializaste
Vault, ¿no?

**Solución robusta (después de octubre):** integrar con Vault Enterprise o usar
un bastion que guarde los shards encriptados en Bitwarden y los inyecte en un
webhook post-restart. Por ahora, es aceptable manual.

---

## 5. Recuperación de un backup

Si necesitas restaurar desde un backup (brecha, pérdida de BD, error catastrófico):

```bash
# 1. Descarga el archivo de S3
scw object get \
  s3://carnets-backups-<tu-bucket>/backups/carnets_<TIMESTAMP>.json.enc \
  > /tmp/backup_descargado.json.enc

# 2. Descifra con Vault (localhost)
# (Aquí necesitarías implementar un helper; el mismo código del comando, invertido)
curl -X POST http://localhost:8200/v1/transit/decrypt/carnets \
  -H "X-Vault-Token: <ROOT_TOKEN>" \
  -d "{\"ciphertext\":\"$(cat /tmp/backup_descargado.json.enc)\"}" \
  | jq -r '.data.plaintext' | base64 -d > /tmp/backup_descifrado.json

# 3. Restaura (ojo: esto sobreescribe la BD actual)
python manage.py loaddata /tmp/backup_descifrado.json

# 4. Verifica que se descifró correctamente
python manage.py shell -c "from gestion.models import Afiliado; print(Afiliado.objects.count())"
```

---

## 6. Checklist antes de octubre

- [ ] `BACKUP_S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` en `.env`
- [ ] `pip install boto3 hvac` en la instancia
- [ ] `python manage.py backup_a_s3_cifrado --dry-run` completa sin errores
- [ ] `python manage.py backup_a_s3_cifrado` sube a S3 real
- [ ] Cron configurado y probado (ejecuta `bin/backup_semanal.sh` a mano para verificar)
- [ ] Logs `/var/log/carnets/backup.log` existen y muestran éxito
- [ ] Intentaste descifrar un backup y restaurarlo en una BD de test

---

## 7. Coste

- Object Storage: €0.006 por GB/mes. Asumiendo 120GB de backups acumulados (90 días):
  **~€0.70/mes**. Negligible.
- Almacenamiento en Vault: libre (corre en tu instancia).

---

## 8. Pendiente después de octubre

- **Snapshots de BD en S3:** además de `dumpdata`, hacer snapshots de PostgreSQL
  (pgbackrest + S3) para recuperación más rápida en caso de brecha.
- **Encryption at rest en S3:** hoy usamos `ServerSideEncryption=AES256` (S3 nativo).
  Vault también cifra encima, así que es doble. Se puede simplificar después de
  octubre si haces pruebas de recuperación exitosas.
- **Webhooks de alertas:** si un backup falla 3 veces seguidas, te avisa. Automático
  con Grafana si centralizas los logs.
