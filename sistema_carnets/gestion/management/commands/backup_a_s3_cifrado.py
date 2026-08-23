"""Backup cifrado de la BD a Object Storage (S3) de Scaleway.

dumpdata -> cifra con Vault -> sube a S3 -> retira los caducados.

Todo ocurre en memoria: el volcado en claro no se escribe en disco en ningun
momento. dumpdata lee a traves del ORM, asi que sale con los datos personales
ya descifrados, y dejarlo en un archivo convertiria el backup en la via mas
comoda para saltarse el cifrado de la base de datos.

Pensado para ejecutar en cron, semanalmente. Mantiene 90 dias de retencion.

Requiere en el entorno: BACKUP_VAULT_ROLE_ID, BACKUP_VAULT_SECRET_ID,
AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY y BACKUP_S3_BUCKET.
"""

import base64
import os
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
        self.stdout.write(f"  Volcado generado en memoria ({len(json_plaintext)} bytes)")

        # El volcado NO se escribe en disco en ningun momento, a proposito.
        #
        # dumpdata lee a traves del ORM, asi que sale con los nombres y numeros
        # de afiliado ya descifrados: es exactamente el texto en claro que el
        # cifrado en reposo existe para que no quede escrito en ninguna parte.
        # Un volcado en el disco convierte el backup en la via mas comoda para
        # saltarse el cifrado de la base de datos.
        #
        # Antes se escribia en un temporal que no leia nadie (Vault cifra desde
        # memoria, y a S3 sube el resultado), y se borraba en la ultima linea
        # del camino de exito: cualquier fallo intermedio --Vault caido,
        # credenciales caducadas, un corte de red-- lo dejaba ahi, y al correr
        # desde cron se acumulaba uno por semana. Como el archivo no cumplia
        # ninguna funcion, se elimina en vez de envolverlo en un try/finally:
        # asi no hay ventana que estrechar.

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
            self.stdout.write(self.style.WARNING(f"DRY-RUN: no se subiria a {filename_s3}"))
            self.stdout.write(self.style.SUCCESS("Simulacion completada."))
            return

        s3 = boto3.client(
            "s3",
            endpoint_url="https://s3.fr-par.scw.cloud",  # Scaleway, region Paris
            region_name="fr-par",
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        )

        self.stdout.write(f"Subiendo a S3 ({s3_bucket}/{filename_s3})...")
        s3.put_object(
            Bucket=s3_bucket,
            Key=filename_s3,
            Body=ciphertext,
            ServerSideEncryption="AES256",  # cifrado de S3, encima del de Vault
        )
        self.stdout.write("  Subido a S3.")

        # 4. Retencion: borra backups de mas de 90 dias
        self.stdout.write("Aplicando retencion (90 dias)...")
        limite = datetime.now(timezone.utc) - timedelta(days=90)
        borrados = 0
        # Paginado: list_objects_v2 devuelve como mucho 1000 claves por llamada,
        # y sin recorrer las paginas los backups mas antiguos --justo los que
        # hay que retirar-- nunca se borrarian.
        for pagina in s3.get_paginator("list_objects_v2").paginate(
            Bucket=s3_bucket, Prefix="backups/",
        ):
            for obj in pagina.get("Contents", []):
                if obj["LastModified"] < limite:
                    s3.delete_object(Bucket=s3_bucket, Key=obj["Key"])
                    borrados += 1
        if borrados:
            self.stdout.write(f"  Borrados {borrados} backups antiguos.")

        # Solo ASCII en esta salida: la consola de Windows usa cp1252 y un
        # caracter fuera de ese juego aborta el comando con UnicodeEncodeError.
        # Aqui lo hacia DESPUES de haber subido ya el objeto: el operador veia
        # una traza de error y concluia que el backup habia fallado cuando
        # estaba hecho. Hay una prueba que lo comprueba.
        self.stdout.write(self.style.SUCCESS(f"Backup completado: {filename_s3}"))
