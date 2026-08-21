"""Backup cifrado de la BD a Object Storage (S3) de Scaleway.

dumpdata (JSON plaintext) → cifra con Vault → sube a S3 → limpia lo local.

Pensado para ejecutar en cron, semanalmente. Mantiene 90 días de retención.
"""

import base64
import os
import tempfile
from datetime import datetime, timedelta, timezone

import boto3
import hvac
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from io import StringIO


class Command(BaseCommand):
    help = "Genera un backup cifrado de la BD y lo sube a S3."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Genera el backup local pero no lo sube a S3.",
        )
        parser.add_argument(
            "--vault-addr",
            default=os.environ.get("BACKUP_VAULT_ADDR", "https://localhost:8200"),
            help="Dirección del Vault (defecto: env BACKUP_VAULT_ADDR)",
        )
        parser.add_argument(
            "--s3-bucket",
            default=os.environ.get("BACKUP_S3_BUCKET", ""),
            help="Bucket de S3 (defecto: env BACKUP_S3_BUCKET)",
        )

    def handle(self, *args, **opciones):
        solo_simular = opciones["dry_run"]
        vault_addr = opciones["vault_addr"]
        s3_bucket = opciones["s3_bucket"]

        if not s3_bucket:
            raise CommandError(
                "BACKUP_S3_BUCKET no configurado. Pónlo en el .env o --s3-bucket."
            )

        # 1. Genera el dumpdata
        self.stdout.write("Generando dumpdata...")
        buffer = StringIO()
        call_command(
            "dumpdata",
            "--exclude", "contenttypes",
            "--exclude", "auth.permission",
            "--natural-foreign",
            "--natural-primary",
            "--indent", "2",
            stdout=buffer,
        )
        json_plaintext = buffer.getvalue()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename_s3 = f"backups/carnets_{timestamp}.json.enc"

        # tempfile.mkstemp (no una ruta fija en /tmp): un nombre predecible
        # sería susceptible a un ataque de symlink por parte de otro proceso
        # del mismo sistema; mkstemp crea el archivo de forma atómica y solo
        # accesible por el usuario que lo generó.
        descriptor, filename_local = tempfile.mkstemp(
            prefix="backup_carnets_", suffix=".json",
        )
        with os.fdopen(descriptor, "w") as f:
            f.write(json_plaintext)
        self.stdout.write(f"  JSON local: {filename_local} ({len(json_plaintext)} bytes)")

        # 2. Cifra con Vault
        self.stdout.write("Cifrando con Vault...")
        vault = hvac.Client(url=vault_addr)
        vault.auth.approle.login(
            role_id=os.environ["BACKUP_VAULT_ROLE_ID"],
            secret_id=os.environ["BACKUP_VAULT_SECRET_ID"],
        )

        respuesta = vault.secrets.transit.encrypt_data(
            path="transit",
            mount_point="transit",
            name="carnets",
            plaintext=base64.b64encode(json_plaintext.encode()).decode(),
        )
        ciphertext = respuesta["data"]["ciphertext"]
        self.stdout.write(f"  Cifrado: {len(ciphertext)} bytes")

        # 3. Sube a S3
        if solo_simular:
            self.stdout.write(self.style.WARNING(f"DRY-RUN: no se subiría a {filename_s3}"))
        else:
            self.stdout.write(f"Subiendo a S3 ({s3_bucket}/{filename_s3})...")
            s3 = boto3.client(
                "s3",
                endpoint_url="https://s3.fr-par.scw.cloud",  # Scaleway, región París
                region_name="fr-par",
                aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            )
            s3.put_object(
                Bucket=s3_bucket,
                Key=filename_s3,
                Body=ciphertext,
                ServerSideEncryption="AES256",  # S3 encryption adicional (encima del Vault)
            )
            self.stdout.write(self.style.SUCCESS("  ✓ Subido a S3"))

        # 4. Limpia el local
        os.remove(filename_local)
        self.stdout.write(f"  Local limpiado: {filename_local}")

        # 5. Retención: borra backups > 90 días (si no es dry-run)
        if not solo_simular:
            self.stdout.write("Aplicando retención (90 días)...")
            s3 = boto3.client(
                "s3",
                endpoint_url="https://s3.fr-par.scw.cloud",
                region_name="fr-par",
                aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            )
            respuesta = s3.list_objects_v2(Bucket=s3_bucket, Prefix="backups/")
            if "Contents" in respuesta:
                ahora = datetime.now(timezone.utc)
                limite = ahora - timedelta(days=90)
                borrados = 0
                for obj in respuesta["Contents"]:
                    if obj["LastModified"].replace(tzinfo=timezone.utc) < limite:
                        s3.delete_object(Bucket=s3_bucket, Key=obj["Key"])
                        borrados += 1
                if borrados:
                    self.stdout.write(f"  Borrados {borrados} backups antiguos")

        self.stdout.write(self.style.SUCCESS(f"✓ Backup completado: {filename_s3}"))
