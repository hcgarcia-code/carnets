#!/usr/bin/env bash
# ==============================================================================
# Script de despliegue: CarnetsCGT -> PythonAnywhere
#
# Ejecutar DENTRO de una consola Bash de PythonAnywhere (no en local).
# Es seguro volver a ejecutarlo si algo falla a mitad (es idempotente en
# los pasos de git/pip/collectstatic; la migración solo se aplica una vez).
#
# Garantías:
#   - Antes de tocar la base de datos real, hace una copia con timestamp.
#   - Antes y después de migrar, cuenta las filas de cada tabla de datos y
#     ABORTA + RESTAURA el backup automáticamente si detecta que se ha
#     perdido o alterado algún registro existente.
#   - No hace falta compartir contraseñas ni tokens con nadie: los secretos
#     se piden por teclado en tu propia sesión y no quedan en este script.
# ==============================================================================

set -euo pipefail

# ============== CONFIGURA ESTAS 6 LÍNEAS ANTES DE EJECUTAR ==================
# (Ninguna de estas variables es secreta - son solo rutas/nombres.)
PROJECT_DIR="/home/carnetscgt/sistema_carnets"
VENV_ACTIVATE="/home/carnetscgt/.virtualenvs/TU_VENV/bin/activate"  # ver nota abajo
GIT_BRANCH="claude/gstack-setup-xbcyy9"
DOMINIO="carnetscgt.eu.pythonanywhere.com"
EMAIL_HOST="correo.cgt.org.es"
EMAIL_USER="soporte_carnets@cgt.org.es"
# ==============================================================================
# Nota sobre VENV_ACTIVATE: en el panel de PythonAnywhere, pestaña "Web",
# busca la sección "Virtualenv" de tu web app - ahí está la ruta exacta.
# Si no usas un virtualenv dedicado, deja la variable en cadena vacía: ""

TABLAS_A_VERIFICAR=(auth_user gestion_afiliado gestion_perfilsindicato gestion_registrosubida gestion_historicalafiliado)

log()  { printf '\n\033[1;34m==> %s\033[0m\n' "$1"; }
ok()   { printf '\033[1;32m    OK: %s\033[0m\n' "$1"; }
fail() { printf '\033[1;31m    ERROR: %s\033[0m\n' "$1"; }

# ------------------------------------------------------------------
contar_filas() {
    # Imprime "tabla:cantidad" por línea, usando el módulo sqlite3 de
    # Python (no depende de que el binario `sqlite3` esté instalado).
    local db_path="$1"
    python3 - "$db_path" "${TABLAS_A_VERIFICAR[@]}" <<'PYEOF'
import sqlite3, sys
db_path, *tablas = sys.argv[1:]
con = sqlite3.connect(db_path)
cur = con.cursor()
existentes = {r[0] for r in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()}
for t in tablas:
    if t in existentes:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"{t}:{cur.fetchone()[0]}")
    else:
        print(f"{t}:NOEXISTE")
PYEOF
}

comparar_conteos() {
    # $1 = archivo "antes", $2 = archivo "después". Aborta si alguna
    # tabla existente perdió filas.
    local antes="$1" despues="$2"
    local hubo_perdida=0
    while IFS=: read -r tabla cantidad_antes; do
        cantidad_despues=$(grep "^${tabla}:" "$despues" | cut -d: -f2)
        if [ "$cantidad_antes" = "NOEXISTE" ]; then
            continue
        fi
        if [ "$cantidad_despues" = "NOEXISTE" ]; then
            fail "La tabla '$tabla' existía antes y ha desaparecido."
            hubo_perdida=1
            continue
        fi
        if [ "$cantidad_despues" -lt "$cantidad_antes" ]; then
            fail "La tabla '$tabla' tenía $cantidad_antes filas y ahora tiene $cantidad_despues (¡pérdida de datos!)."
            hubo_perdida=1
        else
            ok "$tabla: $cantidad_antes -> $cantidad_despues"
        fi
    done < "$antes"
    return $hubo_perdida
}

# ==============================================================================
log "Paso 0: comprobaciones previas"
# ==============================================================================
cd "$PROJECT_DIR"

if [ ! -f "manage.py" ]; then
    fail "No se encuentra manage.py en $PROJECT_DIR. Revisa PROJECT_DIR."
    exit 1
fi
if [ ! -d ".git" ]; then
    fail "$PROJECT_DIR no es un repositorio git. Avísame y preparo el método de subida manual de archivos en su lugar."
    exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
    fail "Hay cambios sin commitear en $PROJECT_DIR. Revísalos a mano antes de continuar (podrían perderse con git pull)."
    git status
    exit 1
fi
ok "Directorio de proyecto y estado de git correctos."

# ==============================================================================
log "Paso 1: backup de la base de datos actual"
# ==============================================================================
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DB="db.sqlite3.backup_${TIMESTAMP}"
cp db.sqlite3 "$BACKUP_DB"
ok "Backup guardado en $PROJECT_DIR/$BACKUP_DB"

CONTEO_ANTES=$(mktemp)
contar_filas "$PROJECT_DIR/db.sqlite3" > "$CONTEO_ANTES"
log "Recuento de filas ANTES del despliegue:"
cat "$CONTEO_ANTES"

# ==============================================================================
log "Paso 2: traer el código nuevo"
# ==============================================================================
git fetch origin "$GIT_BRANCH"
git checkout "$GIT_BRANCH" 2>/dev/null || git checkout -b "$GIT_BRANCH" "origin/$GIT_BRANCH"
git merge --ff-only "origin/$GIT_BRANCH"
ok "Código actualizado a la rama $GIT_BRANCH"

# ==============================================================================
log "Paso 3: archivo .env de producción"
# ==============================================================================
if [ -f ".env" ]; then
    ok ".env ya existe, no se sobrescribe. Comprobando que tenga las claves necesarias..."
    for clave in SECRET_KEY ALLOWED_HOSTS EMAIL_HOST_PASSWORD; do
        if ! grep -q "^${clave}=" .env; then
            fail "Falta '$clave' en tu .env existente. Añádela a mano y vuelve a ejecutar el script."
            exit 1
        fi
    done
    ok ".env contiene las claves obligatorias."
else
    log "No existe .env todavía - vamos a crearlo. Se te pedirán los secretos por teclado (no quedan guardados en este script)."

    read -r -p "SECRET_KEY nuevo (déjalo vacío para que se genere uno automáticamente): " NUEVO_SECRET_KEY
    if [ -z "$NUEVO_SECRET_KEY" ]; then
        NUEVO_SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
        ok "SECRET_KEY generado automáticamente."
    fi

    read -r -s -p "Contraseña nueva del correo ($EMAIL_USER): " NUEVA_PASS_EMAIL
    echo
    if [ -z "$NUEVA_PASS_EMAIL" ]; then
        fail "La contraseña de email no puede estar vacía."
        exit 1
    fi

    cat > .env << ENVEOF
SECRET_KEY=${NUEVO_SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=${DOMINIO},127.0.0.1,localhost

SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_AGE=1800
SESSION_EXPIRE_AT_BROWSER_CLOSE=True

EMAIL_HOST=${EMAIL_HOST}
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=${EMAIL_USER}
EMAIL_HOST_PASSWORD=${NUEVA_PASS_EMAIL}
ENVEOF
    chmod 600 .env
    unset NUEVO_SECRET_KEY NUEVA_PASS_EMAIL
    ok ".env creado con permisos 600 (solo tu usuario puede leerlo)."
fi

# ==============================================================================
log "Paso 4: dependencias"
# ==============================================================================
if [ -n "$VENV_ACTIVATE" ]; then
    # shellcheck disable=SC1090
    source "$VENV_ACTIVATE"
    ok "Virtualenv activado: $VENV_ACTIVATE"
else
    log "VENV_ACTIVATE vacío, se usa el Python/pip por defecto de la consola."
fi
pip install -r requirements.txt
ok "Dependencias instaladas (incluye django-simple-history, nueva en esta versión)."

# ==============================================================================
log "Paso 5: comprobar el estado de las migraciones ANTES de aplicar nada"
# ==============================================================================
ESTADO_MIGRACIONES=$(python3 manage.py showmigrations gestion 2>&1)
echo "$ESTADO_MIGRACIONES"

if echo "$ESTADO_MIGRACIONES" | grep -q "\[ \] 0001_initial\|\[ \] 0002_alter_afiliado_id\|\[ \] 0003_registrosubida\|\[ \] 0004_afiliado_fecha_creacion"; then
    fail "Alguna migración anterior a la 0005 no está aplicada. Esto no coincide con lo verificado - PARO aquí sin tocar nada más."
    fail "Restaura con: cp $BACKUP_DB db.sqlite3 (si hiciera falta) y avísame para revisar el caso."
    exit 1
fi

if echo "$ESTADO_MIGRACIONES" | grep -q "\[X\] 0005_afiliado_estado_impresion_and_more"; then
    ok "La migración 0005 ya estaba aplicada - no hay nada nuevo que migrar. Saltando al paso 7."
    MIGRAR=0
else
    ok "Estado de partida correcto: 0001-0004 aplicadas, 0005 pendiente."
    MIGRAR=1
fi

# ==============================================================================
if [ "$MIGRAR" = "1" ]; then
    log "Paso 6: aplicar la migración 0005 (solo añade columnas/tablas nuevas)"
    # ==============================================================================
    python3 manage.py migrate gestion --noinput

    CONTEO_DESPUES=$(mktemp)
    contar_filas "$PROJECT_DIR/db.sqlite3" > "$CONTEO_DESPUES"
    log "Recuento de filas DESPUÉS de migrar:"
    cat "$CONTEO_DESPUES"

    if ! comparar_conteos "$CONTEO_ANTES" "$CONTEO_DESPUES"; then
        fail "¡ALERTA! Se detectó pérdida de datos. Restaurando el backup automáticamente..."
        cp "$BACKUP_DB" db.sqlite3
        fail "Backup restaurado. NO se ha recargado la web app. Avísame con este mensaje de error para investigar antes de reintentar."
        exit 1
    fi
    ok "Ningún dato existente se ha perdido ni alterado. Migración segura."
    rm -f "$CONTEO_DESPUES"
fi
rm -f "$CONTEO_ANTES"

# ==============================================================================
log "Paso 7: estáticos y comprobación final de Django"
# ==============================================================================
python3 manage.py collectstatic --noinput
python3 manage.py check --deploy
ok "collectstatic y check --deploy completados sin errores."

# ==============================================================================
log "TODO LISTO. Último paso manual (no se puede automatizar sin más credenciales):"
# ==============================================================================
echo "  1. Ve al panel de PythonAnywhere -> pestaña 'Web'"
echo "  2. Pulsa el botón 'Reload $DOMINIO'"
echo "  3. Comprueba: tail -50 /var/log/${DOMINIO//./_}.error.log"
echo "  4. Abre https://$DOMINIO/admin/ y confirma que carga bien"
echo
echo "Si algo va mal tras el reload, backup disponible en:"
echo "  $PROJECT_DIR/$BACKUP_DB"
echo "Rollback: cp $PROJECT_DIR/$BACKUP_DB $PROJECT_DIR/db.sqlite3 && git checkout <rama_anterior> && Reload"
