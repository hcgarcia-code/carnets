# Claves de cifrado: del `.env` a un KMS

Los datos personales del afiliado van cifrados en reposo (ver `gestion/crypto.py`).
Este documento explica de dónde salen las claves y cómo pasar de la
configuración de desarrollo a una válida para datos reales.

## ⚠️ Restricción de cumplimiento RGPD

**Las claves no pueden custodiarse fuera de la UE.** Ver `deploy/RESTRICCION_UE.md`.

Descartadas: AWS KMS (EEUU).  
Viable: HashiCorp Vault autoalojado, o Azure Key Vault en datacenter EU.

---

## 1. El contrato: qué es un proveedor de claves

Un proveedor es **un invocable sin argumentos que devuelve una cadena**:

```
id_clave:clave_en_base64,id_clave:clave_en_base64,...
```

- La **primera** es la clave activa: la que cifra todo lo que se guarda a partir de ahora.
- Las **siguientes** solo sirven para poder leer lo que se guardó antes de la última rotación.
- Cada clave son 32 bytes (AES-256) codificados en base64.
- El identificador puede ser cualquier texto sin `$` (`2026q3`, `kms-1`, ...). Viaja dentro de
  cada dato cifrado, y por eso se sabe con cuál descifrar.

Se selecciona con el ajuste `CARNETS_KEY_PROVIDER`, que contiene la ruta del invocable:

```
CARNETS_KEY_PROVIDER=gestion.proveedores_kms.proveedor_vault
```

El valor por defecto es `gestion.crypto.proveedor_desde_entorno`, que lee la variable
`CARNETS_ENCRYPTION_KEYS` del `.env`. **No es válido para datos reales.**

**A la aplicación no le afecta cuál se use.** Cambiar de proveedor es cambiar ese ajuste; ni
`crypto.py` ni los modelos ni las vistas se enteran.

> El resultado del proveedor se cachea en memoria: se le pregunta **una sola vez** por proceso.
> Sin esa caché, un proveedor de KMS haría una llamada de red por cada campo descifrado (miles en
> una sola búsqueda del admin). La contrapartida es que **tras rotar hay que reiniciar** el
> proceso para que lea las claves nuevas.

---

## 2. Desarrollo local (situación actual)

```bash
# Generar una clave
python -c "import base64,os; print(base64.b64encode(os.urandom(32)).decode())"
```

En el `.env`:

```
CARNETS_ENCRYPTION_KEYS=local1:LA_CLAVE_QUE_ACABAS_DE_GENERAR
```

**Esto no vale para datos reales.** La clave queda en un archivo del servidor: quien pueda leer el
`.env` puede descifrar toda la base de datos, y no queda registro de que lo haya hecho.

---

## 3. Qué aporta de verdad un KMS

| | `.env` | KMS |
|---|---|---|
| Dónde vive el material de clave | En disco, en el servidor | Solo dentro del KMS; nunca se escribe en el servidor |
| Quién ha accedido | No se sabe | Cada acceso queda auditado, con identidad y hora |
| Revocar el acceso | Rotar la clave y redesplegar | Quitar el permiso; efecto inmediato |
| Rotación | Manual | Programable, con historial de versiones |

### La letra pequeña: riesgo residual con credenciales en el servidor

Con **HashiCorp Vault autoalojado en infraestructura propia** (la opción recomendada por restricción
EU), sigue habiendo una credencial de acceso en el servidor del .env. Pero:

1. La credencial es pequeña (role-id + secret-id), frente a la clave maestra en sí.
2. Está limitada a permisos mínimos (solo descifrar/cifrar), no acceso administrativo.
3. Rota automáticamente cada hora (token_ttl).
4. Todo acceso queda auditado en Vault.
5. El material criptográfico nunca sale de tu infraestructura.

El secreto inicial **se sustituye, no desaparece**. Pero la mayoría de mejoras listadas arriba
(auditoría, revocación, material de clave nunca en disco) se cumplen igual.

---

## 4. Implementaciones

Crea `sistema_carnets/gestion/proveedores_kms.py` con la función que corresponda y apunta
`CARNETS_KEY_PROVIDER` a ella. Añade también la dependencia a `requirements.txt`.

### 4.1 HashiCorp Vault (recomendado)

La única opción que mantiene el material criptográfico bajo control de CGT al 100%. Protege
contra exfiltración sin crear dependencias de proveedores cloud ni análisis complejos de
transferencia de datos.

**Setup (una vez):**

```bash
# En tu servidor EU:
docker run -d -p 8200:8200 vault:latest
vault operator init --key-shares 3 --key-threshold 2  # genera 3 shards, necesita 2 para desbloquear
vault operator unseal <shard-1>  # dar 2 de los 3 shards
vault operator unseal <shard-2>
vault login <root-token>
vault secrets enable transit
vault write -f transit/keys/carnets

# Crear credencial de acceso (AppRole) para la app:
vault auth enable approle
vault write auth/approle/role/carnets-app \
  token_ttl=1h \
  policies="carnets-transit"

# Política mínima (transit.hcl):
path "transit/encrypt/carnets" {
  capabilities = ["create", "update"]
}
path "transit/decrypt/carnets" {
  capabilities = ["create", "update"]
}
```

El `.env` del servidor:

```
CARNETS_KEY_PROVIDER=gestion.proveedores_kms.proveedor_vault
VAULT_ADDR=https://vault.tu-dominio-eu.es:8200
VAULT_ROLE_ID=<role-id-de-arriba>
VAULT_SECRET_ID=<secret-id-de-arriba>
```

**Proveedor:**

```python
import base64
import os

import hvac


def proveedor_vault_transit() -> str:
    """Lee las claves del motor Transit de Vault (autoalojado en EU)."""
    cliente = hvac.Client(
        url=os.environ["VAULT_ADDR"],
        auth=hvac.auth.AppRole(
            role_id=os.environ["VAULT_ROLE_ID"],
            secret_id=os.environ["VAULT_SECRET_ID"],
        ),
    )
    # Genera una clave "virtual" del Vault y la devuelve base64-encoded.
    # El Vault cifra los datos; la app solo coordina.
    r = cliente.secrets.transit.generate_data_key(
        name="carnets", key_type="aes256-gcm96",
    )
    clave = base64.b64encode(r["data"]["plaintext"]).decode()
    return f"vault-{r['data']['key_version']}:{clave}"
```

Dependencia: `hvac`. **Nota operativa**: los secrets ruedan cada hora (token_ttl), así que la
sesión de rotación de claves es corta. Sin este limite, una credencial comprometida viviría
indefinidamente.

### 4.2 Azure Key Vault (si está explícitamente en EU)

**Nota**: Azure KMS por defecto usa datacenters en EEUU. Solo es viable si está configurado
explícitamente en `westeurope` o `northeurope`.

```python
import os

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def proveedor_azure_key_vault() -> str:
    """Lee las claves de un secreto de Key Vault en EU."""
    # CRÍTICO: verifica que AZURE_VAULT_URL sea de un datacenter EU.
    cliente = SecretClient(
        vault_url=os.environ["AZURE_VAULT_URL"],  # debe ser https://*.westeurope.vault.azure.net
        credential=DefaultAzureCredential(),  # usa Managed Identity si la hay
    )
    return cliente.get_secret("carnets-claves-cifrado").value
```

El secreto contiene directamente la cadena `id:clave_base64,...`.

Dependencias: `azure-identity`, `azure-keyvault-secrets`. Permiso mínimo: `get` sobre ese secreto.

---

## 5. Rotación de claves (mínimo trimestral)

1. Genera una clave nueva (o una DEK nueva envuelta, según el proveedor).
2. Ponla **la primera** de la lista y deja la anterior detrás:
   `2026q4:CLAVE_NUEVA,2026q3:CLAVE_ANTERIOR`
3. **Reinicia la aplicación** (la caché de claves se llena al arrancar).

A partir de ahí todo lo que se guarde usa la clave nueva, y lo antiguo se sigue leyendo con la
anterior. La rotación ya es efectiva para los datos nuevos.

### Retirar del todo la clave antigua

Mientras quede una sola fila cifrada con la clave antigua, esa clave **no se puede borrar**: si
desaparece, ese dato es irrecuperable. Para poder retirarla hay que reescribir todo con la activa:

```bash
python manage.py reencriptar_afiliados --dry-run   # dice cuántas filas tocaría, sin escribir
python manage.py reencriptar_afiliados             # reescribe todo con la clave activa
```

Incluye la tabla de historial de auditoría. Si el comando termina bien, **por construcción no
queda nada bajo claves anteriores**: ya se pueden quitar de la lista y destruirlas en el KMS.

Hazlo con la clave antigua todavía configurada: el comando necesita poder descifrar para volver a
cifrar. Si alguna fila estuviera bajo una clave ya retirada, el comando se detiene sin escribir
nada y enumera los identificadores afectados, para que puedas reponer esa clave y repetir.

Si se retira una clave antes de tiempo, la aplicación no se queda inservible: las filas que no se
pueden descifrar se muestran como `⟨no descifrable⟩` y las demás siguen funcionando con
normalidad. Guardar una de esas filas se rechaza, para no escribir el marcador encima del dato
original y destruirlo. La reparación consiste en volver a poner la clave que falta.

---

## 6. Puesta en marcha en el servidor

`CARNETS_ENCRYPTION_KEYS` (o lo que use el proveedor elegido) **debe existir antes de migrar**.
Sin claves, la aplicación se niega a arrancar a propósito: guardar datos personales en claro por un
descuido de configuración es el peor fallo posible.

Orden correcto:

1. Configurar el proveedor y sus variables.
2. `python manage.py migrate` — la migración `0007` cifra los afiliados que ya había.
3. Reiniciar la aplicación.

La migración es reversible (`migrate gestion 0006` descifra de vuelta), siempre que las claves
sigan disponibles.

---

## 7. Pendiente

- **Backups.** El script de despliegue copia `db.sqlite3` antes de migrar. Las copias hechas
  *antes* de la migración contienen los datos en claro y siguen en el servidor. Cifrar los backups
  y darles una política de retención es la fase siguiente del plan de la EIPD.
- **Seudonimización.** Cifrar protege frente a quien se lleve el archivo; no desvincula el número
  de afiliado de la identidad dentro de la propia aplicación. Es una fase aparte.
