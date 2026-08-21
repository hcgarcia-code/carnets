# Despliegue de Carnets (Seguridad Art. 9 RGPD)

Índice de documentación de despliegue. Léelo en este orden:

## 1. Decisiones de arquitectura

| Documento | Resuelve |
|---|---|
| [`RESTRICCION_UE.md`](RESTRICCION_UE.md) | Por qué el proveedor de claves debe estar en la UE |
| [`claves_y_kms.md`](claves_y_kms.md) | Del `.env` al KMS (Vault recomendado) |
| [`postgresql_vpc.md`](postgresql_vpc.md) | Base de datos en red privada, usuarios con permisos mínimos |

## 2. Implementación: Scaleway (recomendado)

| Documento | Resuelve |
|---|---|
| [`scaleway_setup.md`](scaleway_setup.md) | Levanta VPC + PostgreSQL + app + Vault en 15 minutos |
| [`backups_cifrados_s3.md`](backups_cifrados_s3.md) | Backups automáticos cifados con rotación (URGENTE antes de octubre) |

## 3. Operaciones

| Documento | Qué hacer |
|---|---|
| [`auditoria_centralizada.md`](auditoria_centralizada.md) | Logs de acceso, retención, destino externo en la UE |
| [`desplegar_pythonanywhere.sh`](desplegar_pythonanywhere.sh) | Script de despliegue automatizado (si sigues con PythonAnywhere) |

## 4. Pendiente post-octubre

- Auto-desbloqueo de Vault (integración con Bitwarden)
- Snapshots de PostgreSQL en S3 (pgbackrest)
- Seudonimización (UUID interno vs. num_afiliado)
- Alertas sobre patrones de acceso (exportaciones fuera de horario)

---

## Hitos hasta octubre

```
Semana 1: Infraestructura
  ├─ VPC + PostgreSQL Managed en Scaleway ✓
  ├─ Instancia app + Vault en Docker ✓
  └─ .env + migración + prueba (python manage.py migrate)

Semanas 2-3: Backups cifrados
  ├─ Bucket S3 + credenciales ✓
  ├─ Comando backup_a_s3_cifrado --dry-run ✓
  ├─ Cron configurado ✓
  └─ Recuperación desde backup (test en BD auxiliar)

Semanas 4-16: Producción
  ├─ Lotes 3k/mes de afiliados nuevos
  ├─ Backups semanales automáticos
  └─ Monitoreo: logs de auditoría + alertas
```

---

## Coste estimado (mes)

| Servicio | Precio |
|---|---|
| PostgreSQL db-gp-xs | €40 |
| Instancia app (DEV1-S) | €12 |
| Object Storage (backups) | €1 |
| **Total** | **€53** |

Comparado a PythonAnywhere: similar o menos, pero con control total de cifrado y backups.

---

## Preguntas frecuentes

**P: ¿Puedo no usar Vault y meter la clave en el .env?**  
R: No. El .env del servidor lo puede leer quien comprometa el servidor, y no queda auditoría. Vault está en la misma instancia (no añade costo), pero audita accesos y permite revocar sin redesplegar.

**P: ¿Y si me olvido de rotar la clave?**  
R: Los backups antiguos seguirán descifrable. Lo nuevo se cifra con la activa. Con Vault, la rotación es trivial (generar clave nueva, ponerla la primera, ejecutar `reencriptar_afiliados`). Trimestral.

**P: ¿Qué pasa si se cae Vault?**  
R: La app no arranca (validación en `GestionConfig.ready()`). Es deliberado: antes que servir datos en claro por un fallo de configuración. Si reinicia la instancia, necesitas desbloquear Vault manualmente (2 shards). Post-octubre hay auto-desbloqueo.

**P: ¿El backup se descarga al servidor o sale directo a S3?**  
R: Sale directo. `dumpdata` genera JSON, se cifra en memoria con Vault, se sube a S3, y se limpia `/tmp`. Nunca sale descifrado del servidor.


---

## Alta autoservicio y panel de la imprenta (2026-08-21)

Dos flujos nuevos, con requisitos de seguridad opuestos:

**Alta de sindicatos** (`/alta/`): pública, sin login. La cuenta nace **inactiva**
(`User.is_active=False`); solo puede iniciar sesión después de que un
administrador la revise en `/admin/auth/user/` (columna "Sindicato/rama
declarado", acción "Aprobar cuentas seleccionadas") y la active. Límite de 5
intentos/hora por IP para que el formulario público no sea una vía de
inyección masiva de cuentas.

**Panel de la imprenta** (`/panel-imprenta/`): cuenta de confianza que creas tú
a mano y añades al grupo Django `Imprenta` (Admin → Grupos). Ve número de
afiliado + código de sindicato + fecha de envío, **nunca nombres**, y solo de
lo que ya está marcado como `IMPRESO` — antes de que decidas enviarlo, la
imprenta no sabe ni que esos números existen. Esa misma cuenta tiene
bloqueado `/subir-datos/`: si sus credenciales se filtran, el daño se limita
a lectura.

Setup de la cuenta de imprenta:

```bash
python manage.py shell -c "
from django.contrib.auth.models import User, Group
grupo, _ = Group.objects.get_or_create(name='Imprenta')
usuario = User.objects.create_user('imprenta_xyz', password='<clave-larga>')
usuario.groups.add(grupo)
"
```
