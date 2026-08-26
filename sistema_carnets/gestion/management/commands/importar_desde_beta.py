"""Importa las cuentas y los afiliados del despliegue beta.

El beta (carnetscgt.eu.pythonanywhere.com) tiene sindicatos que ya se dieron de
alta, firmaron el acuerdo y subieron sus listas. El objetivo es que la
migracion les resulte invisible: **misma contrasena, mismo acuerdo ya firmado,
mismos afiliados**. Si alguna de esas tres cosas se pierde, hay que pedirles
que repitan el proceso, y en la practica eso significa perder a parte de ellos.

Como obtener el volcado, desde una consola bash del beta:

    cd ~/ruta/del/proyecto
    python manage.py dumpdata auth.User gestion.PerfilSindicato gestion.Afiliado \\
        --natural-foreign --indent 2 > beta.json

Y aqui:

    python manage.py importar_desde_beta beta.json --dry-run   # primero esto
    python manage.py importar_desde_beta beta.json

Tres decisiones que conviene no deshacer sin pensarlo:

**Las contrasenas se copian tal cual.** Django guarda en `password` un hash con
su algoritmo y su sal por delante. Copiarlo sin tocarlo hace que la contrasena
de siempre siga valiendo; pasarlo otra vez por `set_password` lo cifraria dos
veces y nadie podria entrar. Por eso se asigna al campo directamente.

**Los afiliados entran por el ORM, uno a uno.** El volcado es anterior al
cifrado en reposo y trae los nombres legibles. Pasar por el ORM es lo que hace
que `CampoTextoCifrado` los cifre al guardarlos. Seria mas rapido con SQL
directo o con `bulk_create` sin senales, y en ambos casos se replicaria en la
base nueva justo el problema que el cifrado existe para evitar.

**No se importan cuentas de administracion.** El admin de este sistema exige
segundo factor, que un superusuario del beta no tiene configurado: la cuenta
entraria con todos los privilegios y sin poder acceder, y ahi se quedaria sin
que nadie la revisara. Las cuentas de administracion se crean a mano y se
habilitan con `activar_2fa`.
"""

import json
from pathlib import Path

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gestion.auditoria import ACCIONES, registrar
from gestion.models import Afiliado, PerfilSindicato

MODELO_USUARIO = "auth.user"
MODELO_PERFIL = "gestion.perfilsindicato"
MODELO_AFILIADO = "gestion.afiliado"

# Campos del volcado que se copian tal cual a PerfilSindicato. persona_contacto
# no esta: el beta lo recogia con otro nombre y se resuelve aparte.
CAMPOS_PERFIL = ("nombre_identificativo", "acuerdo_aceptado", "fecha_aceptacion",
                 "ip_aceptacion")

# Nombres que el beta puede haber usado para la persona de contacto. Se prueban
# en orden; el volcado no esta bajo nuestro control y conviene ser tolerante.
ALIAS_PERSONA_CONTACTO = ("persona_contacto", "nombre_solicitante", "nombre_persona",
                          "solicitante", "nombre_contacto")

CAMPOS_AFILIADO = ("confederacion_territorial", "federacion_local", "federacion_sectorial",
                   "sindicato_codigo", "num_afiliado", "nombre_apellidos", "lengua",
                   "estado", "fecha_expedicion", "notas_historicas")


class Command(BaseCommand):
    help = "Importa cuentas y afiliados desde un volcado (dumpdata) del despliegue beta."

    def add_arguments(self, parser):
        parser.add_argument("archivo", help="Ruta del JSON generado con dumpdata en el beta.")
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Dice que se importaria sin escribir nada.",
        )

    def handle(self, *args, **opciones):
        registros = self._leer(opciones["archivo"])
        por_modelo = {MODELO_USUARIO: [], MODELO_PERFIL: [], MODELO_AFILIADO: []}
        for fila in registros:
            modelo = str(fila.get("model", "")).lower()
            if modelo in por_modelo:
                por_modelo[modelo].append(fila)

        if opciones["dry_run"]:
            self._informar_de_lo_que_haria(por_modelo)
            return

        with transaction.atomic():
            usuarios, omitidos_admin, ya_existian = self._importar_usuarios(
                por_modelo[MODELO_USUARIO],
            )
            perfiles = self._importar_perfiles(por_modelo[MODELO_PERFIL], usuarios)
            afiliados, fallidos, sin_sindicato = self._importar_afiliados(
                por_modelo[MODELO_AFILIADO], usuarios,
            )

        self._resumen(usuarios, ya_existian, omitidos_admin, perfiles,
                      afiliados, fallidos, sin_sindicato)

        if afiliados:
            # Entran datos personales de golpe: tiene que constar, igual que
            # una carga por Excel.
            registrar(
                ACCIONES.AFILIADOS_CARGADOS,
                usuario="importar_desde_beta",
                cantidad=afiliados,
                origen="beta",
            )

    # --- Lectura ---

    def _leer(self, ruta_texto):
        ruta = Path(ruta_texto)
        if not ruta.is_file():
            raise CommandError(f"El archivo no existe: {ruta}")
        try:
            contenido = json.loads(ruta.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(
                f"No se puede leer el archivo como JSON: {exc}. "
                "Comprueba que es la salida de dumpdata y que se copio entera.",
            ) from exc
        if not isinstance(contenido, list):
            raise CommandError(
                "El JSON no tiene el formato de dumpdata (se esperaba una lista).",
            )
        return contenido

    # --- Usuarios ---

    def _importar_usuarios(self, filas):
        """Devuelve (mapa pk_del_beta -> User, omitidos_admin, ya_existian)."""
        mapa = {}
        omitidos_admin = 0
        ya_existian = 0

        for fila in filas:
            campos = fila.get("fields", {})
            if campos.get("is_superuser") or campos.get("is_staff"):
                omitidos_admin += 1
                continue

            username = campos.get("username")
            if not username:
                continue

            existente = User.objects.filter(username=username).first()
            if existente is not None:
                # Ni la contrasena ni el correo se pisan: si esta cuenta ya
                # existe aqui, lo que tenga es mas reciente que el beta.
                mapa[fila.get("pk")] = existente
                ya_existian += 1
                continue

            usuario = User(
                username=username,
                email=campos.get("email", "") or "",
                is_active=bool(campos.get("is_active", True)),
                first_name=campos.get("first_name", "") or "",
                last_name=campos.get("last_name", "") or "",
            )
            # El hash se copia SIN volver a cifrarlo: es lo que hace que la
            # contrasena de siempre siga valiendo. Ver la cabecera del modulo.
            usuario.password = campos.get("password", "")
            if campos.get("date_joined"):
                usuario.date_joined = campos["date_joined"]
            usuario.save()
            mapa[fila.get("pk")] = usuario

        return mapa, omitidos_admin, ya_existian

    # --- Perfiles ---

    def _importar_perfiles(self, filas, usuarios):
        creados = 0
        con_perfil = set()

        for fila in filas:
            campos = fila.get("fields", {})
            usuario = usuarios.get(campos.get("usuario"))
            if usuario is None:
                continue

            valores = {c: campos[c] for c in CAMPOS_PERFIL if campos.get(c) is not None}
            for alias in ALIAS_PERSONA_CONTACTO:
                if campos.get(alias):
                    valores["persona_contacto"] = campos[alias]
                    break
            valores.update(self._identidad_desde_la_cuenta(usuario, valores))

            _, creado = PerfilSindicato.objects.update_or_create(
                usuario=usuario, defaults=valores,
            )
            con_perfil.add(usuario.pk)
            creados += 1 if creado else 0

        # En el volcado real hay 56 cuentas y solo 39 perfiles. Las 17 restantes
        # se quedarian sin nombre de sindicato ni persona, y el administrador no
        # tendria con que decidir a quien aprueba. Se les crea el perfil con lo
        # que se sepa; el acuerdo queda sin firmar, que es lo correcto si no
        # consta que lo firmaran.
        for usuario in usuarios.values():
            if usuario.pk in con_perfil:
                continue
            _, creado = PerfilSindicato.objects.update_or_create(
                usuario=usuario, defaults=self._identidad_desde_la_cuenta(usuario, {}),
            )
            con_perfil.add(usuario.pk)
            creados += 1 if creado else 0

        return creados

    def _identidad_desde_la_cuenta(self, usuario, ya_puestos):
        """Recupera el sindicato y la persona de contacto desde la cuenta.

        El `perfilsindicato` del beta no guarda ninguno de los dos, pese a que
        su formulario de alta pedia ambos: acabaron en `first_name` y
        `last_name` de `auth.user`. Sin recuperarlos de ahi, los perfiles
        migrados quedan anonimos.

        **El reparto va al reves de lo que sugieren los nombres de Django**:
        el sindicato esta en `last_name` y la persona en `first_name`.
        Comprobado sobre el volcado real: 39 de 56 `last_name` contienen SOV,
        CGT, federacion o similar --justo los 39 que tienen perfil--, frente a
        1 de los `first_name`.
        """
        valores = {}
        if not ya_puestos.get("nombre_identificativo") and usuario.last_name:
            valores["nombre_identificativo"] = usuario.last_name
        if not ya_puestos.get("persona_contacto") and usuario.first_name:
            valores["persona_contacto"] = usuario.first_name
        return valores

    # --- Afiliados ---

    def _importar_afiliados(self, filas, usuarios):
        creados = 0
        fallidos = []
        sin_sindicato = 0
        # `fecha_creacion` es auto_now_add: al guardar, Django ignora el valor
        # que traiga el volcado y pone el de hoy. Se repone despues con un
        # bulk_update, que no aplica auto_now_add. Sin esto, los afiliados
        # figurarian como dados de alta el dia de la migracion y se perderia la
        # antiguedad de cada persona en su sindicato, que no se recupera.
        a_reponer_fecha = []

        # La deduplicacion no puede hacerse con `filter(num_afiliado=...)`:
        # `CampoTextoCifrado` prohibe expresamente consultar por su contenido
        # desde SQL, porque en la base de datos solo hay texto cifrado y una
        # busqueda ahi no encontraria nada aunque el dato exista. Se lee una vez
        # el conjunto de pares (sindicato, numero) ya presentes y se compara en
        # memoria. El conjunto crece tambien con lo que se va creando, para que
        # un volcado con filas repetidas no las duplique.
        vistos = {
            (a.sindicato_usuario_id, a.num_afiliado)
            for a in Afiliado.objects.all().only("sindicato_usuario", "num_afiliado")
        }

        for fila in filas:
            campos = fila.get("fields", {})
            usuario = usuarios.get(campos.get("sindicato_usuario"))
            if usuario is None:
                # Importarlo bajo otro sindicato seria mucho peor que no
                # importarlo: rompe el aislamiento entre sindicatos.
                sin_sindicato += 1
                continue

            datos = {c: campos.get(c) for c in CAMPOS_AFILIADO if campos.get(c) is not None}
            afiliado = Afiliado(sindicato_usuario=usuario, **datos)

            try:
                # full_clean valida y ademas sella fecha_baja si viene de BAJA:
                # el beta no tenia ese campo, y sin el esos afiliados quedarian
                # fuera del plazo de conservacion para siempre.
                afiliado.full_clean(exclude=["sindicato_usuario"])
            except ValidationError:
                # Solo la referencia del volcado, nunca el dato: este mensaje
                # acaba en la consola y en los registros del operador.
                fallidos.append(fila.get("pk"))
                continue

            huella = (usuario.pk, afiliado.num_afiliado)
            if huella in vistos:
                continue

            afiliado.save()
            vistos.add(huella)
            creados += 1

            if campos.get("fecha_creacion"):
                afiliado.fecha_creacion = campos["fecha_creacion"]
                a_reponer_fecha.append(afiliado)

        if a_reponer_fecha:
            Afiliado.objects.bulk_update(a_reponer_fecha, ["fecha_creacion"], batch_size=500)

        return creados, fallidos, sin_sindicato

    # --- Salida ---

    def _informar_de_lo_que_haria(self, por_modelo):
        usuarios = por_modelo[MODELO_USUARIO]
        normales = [f for f in usuarios
                    if not (f.get("fields", {}).get("is_superuser")
                            or f.get("fields", {}).get("is_staff"))]
        self.stdout.write("[dry-run] No se ha escrito nada. Se importarian:")
        self.stdout.write(f"  Cuentas de sindicato: {len(normales)}")
        self.stdout.write(f"  Perfiles: {len(por_modelo[MODELO_PERFIL])}")
        self.stdout.write(f"  Afiliados: {len(por_modelo[MODELO_AFILIADO])}")
        if len(usuarios) != len(normales):
            self.stdout.write(
                f"  Se omitirian {len(usuarios) - len(normales)} cuenta(s) de "
                "administrador: el admin exige segundo factor y hay que darlas "
                "de alta a mano con activar_2fa.",
            )

    def _resumen(self, usuarios, ya_existian, omitidos_admin, perfiles,
                 afiliados, fallidos, sin_sindicato):
        nuevos = len(usuarios) - ya_existian
        self.stdout.write(f"Cuentas importadas: {nuevos}")
        if ya_existian:
            self.stdout.write(
                f"Cuentas que ya existian y no se han tocado: {ya_existian} "
                "(ni su contrasena ni su correo se han sobrescrito).",
            )
        if omitidos_admin:
            self.stdout.write(
                f"AVISO: {omitidos_admin} cuenta(s) de administrador NO importadas. "
                "El admin exige segundo factor; creala a mano y ejecuta activar_2fa.",
            )
        self.stdout.write(f"Perfiles de sindicato importados: {perfiles}")
        self.stdout.write(f"Afiliados importados: {afiliados}")
        if fallidos:
            self.stdout.write(
                f"AVISO: {len(fallidos)} afiliado(s) descartados por no pasar la "
                f"validacion. Referencias en el volcado: {fallidos[:20]}"
                + (" ..." if len(fallidos) > 20 else ""),
            )
        if sin_sindicato:
            self.stdout.write(
                f"AVISO: {sin_sindicato} afiliado(s) sin sindicato reconocible en el "
                "volcado. No se han importado: asignarlos a otro sindicato seria peor.",
            )
