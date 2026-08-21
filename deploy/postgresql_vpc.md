# PostgreSQL en subred privada

Hoy la base de datos es un archivo SQLite **en el mismo servidor que la aplicación**: cualquier
brecha en Django da acceso directo a los datos de todos los afiliados, sin necesidad de ninguna
credencial adicional. Este documento describe el paso a PostgreSQL aislado en red.

---

## 1. Configuración en la aplicación (ya soportada)

`settings.py` ya admite ambos motores. Con estas variables en el `.env` del servidor:

```
DATABASE_ENGINE=postgresql
DATABASE_NAME=carnets
DATABASE_USER=carnets_app
DATABASE_PASSWORD=...
DATABASE_HOST=10.0.1.20          # IP privada, nunca pública
DATABASE_PORT=5432
DATABASE_SSLMODE=verify-full
DATABASE_SSLROOTCERT=/etc/ssl/certs/carnets-db-ca.pem
DATABASE_CONN_MAX_AGE=60
```

Añade el driver a `requirements.txt`:

```
psycopg[binary]==3.2.*
```

**TLS es obligatorio.** La conexión ya no es un archivo local: cruza la red llevando nombres y
números de afiliado. `verify-full` cifra **y** comprueba que el servidor al otro lado es realmente
el nuestro; `require` solo cifra, y deja la puerta abierta a que alguien se interponga. Si
`DATABASE_SSLMODE` empieza por `verify` y falta el certificado raíz, la aplicación se niega a
arrancar en vez de degradarse en silencio.

## 2. Aislamiento de red

- La base de datos vive en una **subred privada**, sin IP pública y sin ruta desde internet.
- Solo acepta conexiones desde el grupo de seguridad del servidor de aplicación, al puerto 5432.
- La administración se hace por **bastión o VPN**, con clave SSH y segundo factor. Nunca
  exponiendo 5432, ni siquiera "temporalmente".
- Copias de seguridad cifradas y con acceso restringido (fase 5 del plan).

## 3. Usuario de aplicación con permisos mínimos

Dos roles distintos: uno que es dueño del esquema y solo se usa para migrar, y otro para el día a
día que **no puede modificar la estructura**. Si alguien roba las credenciales de la aplicación, no
puede borrar tablas ni alterar el esquema.

```sql
CREATE ROLE carnets_owner LOGIN PASSWORD 'una-contrasena-larga-y-aleatoria';
CREATE ROLE carnets_app   LOGIN PASSWORD 'otra-distinta-igual-de-larga';

CREATE DATABASE carnets OWNER carnets_owner;
\c carnets

-- Nadie tiene nada por defecto.
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO carnets_app;

-- La aplicación solo manipula filas, nunca la estructura.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO carnets_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO carnets_app;

-- Y lo mismo para las tablas que creen las migraciones futuras.
ALTER DEFAULT PRIVILEGES FOR ROLE carnets_owner IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO carnets_app;
ALTER DEFAULT PRIVILEGES FOR ROLE carnets_owner IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO carnets_app;
```

> **Sobre `DELETE`**: el requisito hablaba de dejar solo `SELECT/INSERT/UPDATE`, pero Django
> necesita `DELETE` para el borrado en cascada, la limpieza de sesiones caducadas y el expurgado
> por retención. Lo que de verdad importa —y esto sí se cumple— es que el rol de la aplicación no
> tenga **DDL**: nada de `CREATE`, `ALTER` ni `DROP`.

Las migraciones se ejecutan aparte, con `carnets_owner`:

```bash
DATABASE_USER=carnets_owner DATABASE_PASSWORD=... python manage.py migrate
```

## 4. Traslado de los datos desde SQLite

Los campos cifrados no complican el traslado: `dumpdata` lee por el ORM (descifra) y `loaddata`
escribe por el ORM (vuelve a cifrar con la clave activa).

```bash
# 1. Con la configuración actual de SQLite y las claves de cifrado disponibles:
python manage.py dumpdata --natural-foreign --natural-primary \
    --exclude contenttypes --exclude auth.permission \
    --indent 2 -o traslado.json

# 2. Cambia el .env a PostgreSQL y crea el esquema:
DATABASE_USER=carnets_owner ... python manage.py migrate

# 3. Carga los datos:
python manage.py loaddata traslado.json

# 4. Comprueba los recuentos antes de dar por bueno el traslado.
```

> ⚠️ **`traslado.json` contiene los datos personales EN CLARO**, de todos los afiliados. Es, durante
> el rato que exista, el archivo más peligroso del proyecto. Genéralo en un directorio con permisos
> `700`, no lo copies a ningún sitio intermedio, y **destrúyelo en cuanto termines**
> (`shred -u traslado.json`). No debe acabar en un backup ni, por supuesto, en git.

Si prefieres evitarlo del todo, la alternativa es copiar tabla a tabla con los valores ya cifrados
(sin pasar por el ORM), pero entonces la clave de cifrado debe ser la misma a ambos lados.

## 5. Comprobaciones tras el traslado

```bash
python manage.py check --deploy          # sin avisos
python manage.py showmigrations gestion  # todas aplicadas
python manage.py shell -c "from gestion.models import Afiliado; a=Afiliado.objects.first(); print(bool(a.nombre_apellidos))"
```

Lo último confirma que los datos se descifran correctamente contra la base nueva. El recuento de
filas por sí solo no lo detectaría: las filas estarían ahí, pero ilegibles.

Comprueba además que el usuario de la aplicación **no** puede tocar el esquema:

```sql
-- Conectado como carnets_app, esto DEBE fallar:
CREATE TABLE prueba (id int);
DROP TABLE gestion_afiliado;
```
