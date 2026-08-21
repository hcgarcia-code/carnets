# Despliegue en Scaleway (60k afiliados, 3k/mes hasta octubre)

Scaleway: francés, EU + no sujeto a CLOUD Act, API buena, precio bajo. Se monta en ~15 minutos.

---

## 1. Crear la VPC privada

```bash
# CLI de Scaleway (instala: npm install -g scaleway-cli)
scw vpc create name=carnets-vpc

# Anota el VPC-ID
VPC_ID=vpc-xxx
```

## 2. PostgreSQL Managed (en la VPC)

```bash
scw rdb instance create \
  name=carnets-db \
  engine=PostgreSQL-15 \
  node-type=db-gp-xs \
  volume-size=100 \
  vpc-id=$VPC_ID \
  backup-retention-days=30
```

Espera a que esté GREEN (~5 min). Nota:
- **db-gp-xs**: 2 CPU, 2 GB RAM, ~€40/mes. Sobra para 60k.
- **volume-size=100GB**: crece con el historial de auditoría (simple_history). Monitorealo a los 3 meses; si pasa 80GB, escala a 150GB.
- **backup-retention-days=30**: Scaleway hace backups diarios automáticos, pero **no están cifrados**. Ver sección 4 para backups cifrados reales.

Configura:
```bash
# Usuario y BD (desde la consola, o:)
scw rdb user create instance-id=$INSTANCE_ID name=carnets_app password=$(openssl rand -base64 32)
scw rdb database create instance-id=$INSTANCE_ID name=carnets
```

## 3. Instancia app + Vault en la VPC

```bash
scw instance server create \
  name=carnets-app \
  image=ubuntu-jammy \
  type=DEV1-S \
  vpc-id=$VPC_ID \
  root-volume-size=50
```

- **DEV1-S**: 2 CPU, 2 GB RAM, ~€12/mes. Instancia bare; va Python + Vault + app.
- **Sin IP pública.** Acceso solo desde tu bastión (sección 5).

SSH (vía Private Network o Bastion):

```bash
# 1. Instala dependencias
sudo apt update
sudo apt install -y python3.11 python3-pip python3-venv postgresql-client docker.io

# 2. Clona el código
git clone https://github.com/hcgarcia-code/carnets.git /opt/carnets
cd /opt/carnets

# 3. Entorno Python
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install psycopg[binary]==3.2.*  # driver de PostgreSQL

# 4. Crea el .env
cat > .env << 'INNEREOF'
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DEBUG=False
ALLOWED_HOSTS=carnets-app.internal  # o tu dominio

DATABASE_ENGINE=postgresql
DATABASE_NAME=carnets
DATABASE_USER=carnets_app
DATABASE_PASSWORD=<GENERADA_ARRIBA>
DATABASE_HOST=<IP_PRIVADA_DE_RDS>
DATABASE_PORT=5432
DATABASE_SSLMODE=verify-full
DATABASE_SSLROOTCERT=/etc/ssl/certs/rds-ca-bundle.pem

CARNETS_ENCRYPTION_KEYS=<GENERADA_LOCALMENTE>

# Backups cifrados (sección 4)
AUDITORIA_LOG_PATH=/var/log/carnets/auditoria.jsonl
BACKUP_S3_BUCKET=carnets-backups-<TIMESTAMP>
BACKUP_S3_REGION=fr-par  # región de Scaleway más cercana
BACKUP_VAULT_ADDR=https://localhost:8200
BACKUP_VAULT_ROLE_ID=<DEL_VAULT_ABAJO>
BACKUP_VAULT_SECRET_ID=<DEL_VAULT_ABAJO>
INNEREOF

# 5. Vault en Docker (autoalojado en la misma instancia)
# CRÍTICO: Vault maneja las claves de cifrado. Corre ANTES de la migración.
docker run -d \
  --name vault \
  -p 8200:8200 \
  -e VAULT_API_ADDR=http://0.0.0.0:8200 \
  -v vault-data:/vault/file \
  vault:latest server -config=/vault/config/vault.hcl

# Inicializa Vault (una sola vez):
docker exec vault vault operator init \
  --key-shares=3 \
  --key-threshold=2 \
  > /opt/vault-init.txt  # GUARDA ESTO EN UN LUGAR SEGURO (no en git, no en el servidor)

# Desbloquea Vault (cada restart):
docker exec vault vault operator unseal <shard-1>
docker exec vault vault operator unseal <shard-2>

# Configura el motor Transit (claves de cifrado):
docker exec vault vault login <ROOT_TOKEN>
docker exec vault vault secrets enable transit
docker exec vault vault write -f transit/keys/carnets

# AppRole para la app:
docker exec vault vault auth enable approle
docker exec vault vault write auth/approle/role/carnets-app \
  token_ttl=1h policies=carnets-transit
docker exec vault vault read auth/approle/role/carnets-app/role-id
docker exec vault vault generate-secret auth/approle/role/carnets-app/secret-id

# Guarda role-id y secret-id en el .env (arriba).

# 6. Migra la BD
python manage.py migrate

# 7. Arranca la app (gunicorn + supervisor, ver abajo)
```

## 4. Backups cifrados a Object Storage (URGENTE antes de octubre)

Ver `deploy/backups_cifrados_s3.md`. Resume:

```bash
# Semanalmente (cron):
python manage.py backup_a_s3_cifrado --vault-addr $BACKUP_VAULT_ADDR
```

Se genera: `dumpdata` → se cifra con Vault → sube a S3 de Scaleway.

Retención: 90 días (puedes prolongar después de octubre, según EIPD).

## 5. Bastión (acceso a la VPC desde fuera)

La instancia app no tiene IP pública. Para SSH:

```bash
# Opción A: Bastion en Scaleway (otra instancia con IP pública)
scw instance server create \
  name=carnets-bastion \
  image=ubuntu-jammy \
  type=DEV1-S \
  root-volume-size=20
  # SÍ tiene IP pública

# Opción B: Usar Scaleway Private Networks + Tailscale (más fácil si trabajas desde casa)
```

## 6. Actualiza settings.py

En `sistema_carnets/settings.py`, añade:

```python
if os.environ.get('ENVIRONMENT') == 'production':
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
```

## 7. Presupuesto mensual (hasta octubre + 3 meses después)

| Servicio | Precio | Notas |
|---|---|---|
| PostgreSQL db-gp-xs | €40 | crece a €60 si subes a db-gp-s a los 3 meses |
| Instancia app DEV1-S | €12 | |
| Object Storage | €5-10 | 60GB de backups/mes, retención 90 días |
| **TOTAL** | **€57-65/mes** | Sin bastión (si necesitas, +€12 más) |

Comparado a PythonAnywhere (donde está ahora): probablemente similar o menos, pero con **control total** de la DB y los backups cifrados.

---

## Checklist

- [ ] VPC creada
- [ ] PostgreSQL Managed en GREEN
- [ ] Instancia app SSH-able
- [ ] Vault inicializado y desbloqueado (guarda los shards en Bitwarden o análogo)
- [ ] `.env` con todas las variables
- [ ] `python manage.py migrate` completó sin error
- [ ] Backup S3 cifrado funciona (`python manage.py backup_a_s3_cifrado --dry-run`)
- [ ] App arranca en gunicorn
- [ ] Probaste un login y una exportación de imprenta desde el navegador
