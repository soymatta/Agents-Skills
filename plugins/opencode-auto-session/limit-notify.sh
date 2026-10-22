#!/usr/bin/env sh
# Aviso de limite + recuperacion (Linux/macOS). Equivalente funcional de
# limit-notify.ps1. Lo lanza el servidor de OpenCode cuando el proveedor
# devuelve un limite/cuota (ver autosession.ts).
#
# Uso:  limit-notify.sh [SessionID] [DumpFile] [KeepOpenSeconds]
#       (sin argumentos usa OPENCODE_LIMIT_SESSION / OPENCODE_LIMIT_DUMP /
#        OPENCODE_LIMIT_KEEP_OPEN, que es como lo lanza el plugin)
#
# QUE HACE
#   1. Deja SIEMPRE el aviso en limit-notify.log (junto al dump, o en $TMPDIR):
#      un proceso en segundo plano sin consola no puede imprimir en ningun sitio.
#   2. Si no tiene terminal (lo normal al lanzarlo el servidor), se re-ejecuta
#      dentro de un emulador: asi sus pasos se ven y no muere cuando cierra
#      OpenCode.
#   3. Rota la VPN de Proton (solo si su CLI esta instalada).
#   4. Cierra OpenCode y sus procesos Node, y limpia caches.
#
# VARIABLES
#   OPENCODE_LIMIT_RECOVER=1     cerrar OpenCode, limpiar cache y rotar la VPN.
#                                Por defecto 0 (solo avisar): el limite gratuito
#                                es de la CUENTA y salta muchas veces al dia, asi
#                                que cerrar OpenCode en cada salto tira la sesion
#                                en la que estas trabajando. Se activa cuando de
#                                verdad quieres el reinicio duro.
#   OPENCODE_LIMIT_COOLDOWN=90   segundos minimos entre recuperaciones (0 = sin tope)
#   OPENCODE_LIMIT_KILL_WAIT=2   segundos de gracia tras SIGTERM antes de SIGKILL
#   OPENCODE_LIMIT_KILL_NODE=0   1 = cierra tambien todo proceso Node del sistema
#   OPENCODE_LIMIT_WINDOW=1      0 = no abre ventana propia (sesiones sin escritorio)
#
# POR QUE NO HACE CIERTAS COSAS (errores del script original, corregidos)
#   - No mata por patron en la linea de comandos (el `pgrep -f "opencode|node"`
#     original): ese patron alcanza la propia terminal, la shell del script,
#     otros editores y cualquier proceso cuyo directorio contenga "opencode"
#     (este mismo script). Mata por NOMBRE EXACTO de ejecutable y nunca a si
#     mismo.
#   - No borra con `rm -rf "$VAR"/*`: si $VAR viene vacio eso apunta a la raiz.
#     Cada ruta se valida (no vacia, existe, su ultimo componente es de cache) y
#     se borra solo su CONTENIDO, nunca el directorio.
#   - No borra .opencode entero: ahi viven skills/, plugins/, commands/ y
#     agents/ del proyecto. Solo limpia subcarpetas de cache y temporales.
#   - No instala nada ni usa sudo.
#   - No entra en bucle: si el limite sigue activo, el enfriamiento (cooldown)
#     evita volver a cerrar OpenCode cada vez que se reabre.
#   - No perdona al proceso padre: el servidor de OpenCode es justo quien lanza
#     este script, y es lo que hay que cerrar. Lo protege el filtro por nombre
#     (una terminal o una shell jamas se llaman "opencode"), no un PID.

set -u

export PATH="$PATH:/usr/bin:/usr/local/bin:${HOME:-}/.local/bin"

SESSION_ID="${1:-${OPENCODE_LIMIT_SESSION:-}}"
DUMP_FILE="${2:-${OPENCODE_LIMIT_DUMP:-}}"
KEEP_OPEN_SECONDS="${3:-${OPENCODE_LIMIT_KEEP_OPEN:-20}}"
RECOVER="${OPENCODE_LIMIT_RECOVER:-0}"
COOLDOWN="${OPENCODE_LIMIT_COOLDOWN:-90}"
KILL_WAIT="${OPENCODE_LIMIT_KILL_WAIT:-2}"
KILL_NODE="${OPENCODE_LIMIT_KILL_NODE:-0}"
SHOW_WINDOW="${OPENCODE_LIMIT_WINDOW:-1}"

BANNER="LIMITE GRATIS ALCANZADO"

# Ruta absoluta del script: el emulador abre su propia terminal y puede tener
# otro directorio de trabajo.
SCRIPT_PATH="$0"
case "$SCRIPT_PATH" in
  /*) : ;;
  *) SCRIPT_PATH="$(cd "$(dirname "$SCRIPT_PATH")" 2>/dev/null && pwd)/$(basename "$SCRIPT_PATH")" ;;
esac

# Directorio del log: junto al dump; si no hay, $TMPDIR.
LOG_DIR=""
if [ -n "$DUMP_FILE" ]; then
  LOG_DIR="$(dirname "$DUMP_FILE" 2>/dev/null || true)"
fi
if [ -z "$LOG_DIR" ] || [ ! -d "$LOG_DIR" ]; then
  LOG_DIR="${TMPDIR:-/tmp}"
fi
LOG_FILE="$LOG_DIR/limit-notify.log"
STAMP_FILE="$LOG_DIR/.limit-notify.stamp"

step() { printf '==> %s\n' "$1"; }
note() { printf '    %s\n' "$1"; }

is_number() {
  case "$1" in
    ''|*[!0-9]*) return 1 ;;
  esac
  return 0
}

# Registro durable. Sin el, cuando el plugin lanza esto en segundo plano no
# queda ninguna prueba de que el limite se detecto y que se hizo.
log_line() {
  printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z' 2>/dev/null || echo '?')" "$1" \
    >> "$LOG_FILE" 2>/dev/null || true
}

# ── terminal ─────────────────────────────────────────────────────────────────
# Sin TTY no hay donde imprimir: abrir una ventana propia y re-ejecutarse dentro.
# La ventana sobrevive al cierre de OpenCode; una salida en segundo plano, no.
open_terminal() {
  [ -t 1 ] && return 1
  [ "$SHOW_WINDOW" = "1" ] || return 1
  for term in "${TERMINAL:-}" x-terminal-emulator gnome-terminal konsole xfce4-terminal mate-terminal lxterminal alacritty kitty foot xterm; do
    [ -n "$term" ] || continue
    command -v "$term" >/dev/null 2>&1 || continue
    # gnome-terminal y sus alias rechazan `-e` con varios argumentos (esperan un
    # unico comando); el resto usa `-e`. `--` ya separa comando y argumentos.
    case "$(basename "$term" 2>/dev/null || echo "$term")" in
      gnome-terminal|x-terminal-emulator|kitty|foot) launcher="--" ;;
      *) launcher="-e" ;;
    esac
    OPENCODE_LIMIT_LOGGED=1 "$term" "$launcher" sh "$SCRIPT_PATH" "$SESSION_ID" "$DUMP_FILE" "$KEEP_OPEN_SECONDS" >/dev/null 2>&1 &
    return 0
  done
  # macOS: Terminal via LaunchServices (los argumentos no viajan, el log si).
  if command -v open >/dev/null 2>&1; then
    OPENCODE_LIMIT_LOGGED=1 open -a Terminal "$SCRIPT_PATH" >/dev/null 2>&1 && return 0
  fi
  return 1
}

notice() {
  echo "$BANNER"
  echo "Fecha: $(date '+%Y-%m-%d %H:%M:%S' 2>/dev/null)"
  [ -n "$SESSION_ID" ] && echo "Sesion: $SESSION_ID"
  [ -n "$DUMP_FILE" ] && echo "Dump: $DUMP_FILE"
}

# ── enfriamiento ─────────────────────────────────────────────────────────────
# Un limite de plan gratuito es de la CUENTA, no de la IP: si se reabre OpenCode
# enseguida, el limite sigue ahi. Sin este tope el script cerraria OpenCode en
# bucle. Se puede desactivar con OPENCODE_LIMIT_COOLDOWN=0.
cooldown_active() {
  is_number "$COOLDOWN" || return 1
  [ "$COOLDOWN" -gt 0 ] || return 1
  [ -f "$STAMP_FILE" ] || return 1
  last="$(cat "$STAMP_FILE" 2>/dev/null || echo '')"
  is_number "$last" || return 1
  now="$(date +%s 2>/dev/null || echo '')"
  is_number "$now" || return 1
  [ "$((now - last))" -lt "$COOLDOWN" ]
}

mark_recovery() {
  date +%s > "$STAMP_FILE" 2>/dev/null || true
}

# ── cierre de procesos ───────────────────────────────────────────────────────
# PIDs por nombre EXACTO de ejecutable (nunca por patron de linea de comandos).
# Solo se excluye el propio script: el filtro por nombre ya garantiza que una
# terminal, una shell o un editor jamas entren en la lista.
pids_by_name() {
  command -v pgrep >/dev/null 2>&1 || return 0
  for name in $1; do
    for pid in $(pgrep -x "$name" 2>/dev/null || true); do
      [ "$pid" = "$$" ] && continue
      printf '%s\n' "$pid"
    done
  done
}

# Procesos Node/Bun que SI son de OpenCode (evita cerrar otros programas).
pids_opencode_runtime() {
  command -v pgrep >/dev/null 2>&1 || return 0
  for name in node bun; do
    for pid in $(pgrep -x "$name" 2>/dev/null || true); do
      [ "$pid" = "$$" ] && continue
      cmd="$(ps -o command= -p "$pid" 2>/dev/null || true)"
      case "$cmd" in
        *opencode*) printf '%s\n' "$pid" ;;
      esac
    done
  done
}

# Primero SIGTERM (OpenCode cierra la sesion de forma ordenada), luego SIGKILL
# solo a los que sigan vivos.
close_pids() {
  [ -n "$1" ] || return 0
  for pid in $1; do
    kill -TERM "$pid" >/dev/null 2>&1 || true
  done
  if is_number "$KILL_WAIT" && [ "$KILL_WAIT" -gt 0 ]; then
    sleep "$KILL_WAIT"
  fi
  for pid in $1; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill -KILL "$pid" >/dev/null 2>&1 || true
    fi
  done
}

close_opencode() {
  step "Cerrando procesos de OpenCode y Node..."

  # Windows / Git Bash / WSL: taskkill no puede filtrar por linea de comandos,
  # asi que solo se cierra node.exe entero si se pide explicitamente.
  if command -v taskkill >/dev/null 2>&1; then
    taskkill //F //IM "opencode.exe" //T >/dev/null 2>&1 || true
    if [ "$KILL_NODE" = "1" ]; then
      taskkill //F //IM "node.exe" //T >/dev/null 2>&1 || true
    fi
  fi

  # Linux/macOS
  targets="$(pids_by_name 'opencode' | tr '\n' ' ')"
  if [ "$KILL_NODE" = "1" ]; then
    targets="$targets $(pids_by_name 'node' | tr '\n' ' ')"
  fi
  targets="$targets $(pids_opencode_runtime | tr '\n' ' ')"
  count=0
  for pid in $targets; do count=$((count + 1)); done
  if [ "$count" -eq 0 ]; then
    note "No se encontro ningun proceso de OpenCode en ejecucion."
    return 0
  fi
  note "Cerrando $count proceso(s):$targets"
  close_pids "$targets"
  CLOSED_COUNT="$count"
  note "Cerrados."
}

# ── limpieza ─────────────────────────────────────────────────────────────────
# Borra SOLO el contenido de un directorio de cache. Se exige que el ultimo
# componente de la ruta sea de cache: asi una variable vacia (ruta raiz), un
# directorio de datos o un .opencode/skills jamas se tocan.
clean_dir() {
  dir="${1:-}"
  [ -n "$dir" ] || return 0
  [ -d "$dir" ] || return 0
  case "$(basename "$dir")" in
    cache|Cache|caches|Caches|tmp|temp|Temp|opencode) : ;;
    *)
      note "Se omite $dir (no es una cache)."
      return 0
      ;;
  esac
  find "$dir" -mindepth 1 -maxdepth 1 -exec rm -rf {} + >/dev/null 2>&1 || true
  CLEANED_DIRS="$CLEANED_DIRS $dir"
}

clean_caches() {
  step "Limpiando cache temporal (conservando sesiones)..."
  clean_dir "${LOCALAPPDATA:-}/OpenCode/Cache"
  clean_dir "${APPDATA:-}/OpenCode/Cache"
  clean_dir "${HOME:-}/.cache/opencode"
  # Del proyecto solo temporales: skills/, plugins/, commands/ y agents/ viven
  # en .opencode y son datos, no cache.
  clean_dir ".opencode/cache"
  clean_dir ".opencode/tmp"
  # Sanitiza opencode.db para remover cuentas y tokens de usuario conservando las sesiones
  if [ -n "${HOME:-}" ] && [ -f "${HOME}/.local/share/opencode/opencode.db" ]; then
    if command -v python3 >/dev/null 2>&1; then
      python3 -c "import sqlite3, sys; conn = sqlite3.connect(sys.argv[1]); [conn.execute(f'DELETE FROM {t}') for t in ['account', 'account_state', 'control_account', 'credential'] if conn.execute(f'SELECT 1 FROM sqlite_master WHERE type=''table'' AND name=''{t}''').fetchone()]; conn.commit(); conn.close()" "${HOME}/.local/share/opencode/opencode.db" >/dev/null 2>&1 || true
    elif command -v sqlite3 >/dev/null 2>&1; then
      sqlite3 "${HOME}/.local/share/opencode/opencode.db" "DELETE FROM account; DELETE FROM account_state; DELETE FROM control_account; DELETE FROM credential;" >/dev/null 2>&1 || true
    fi
  fi
  note "Sesiones y datos del proyecto intactos."
}

# ── VPN ──────────────────────────────────────────────────────────────────────
rotate_vpn() {
  step "Rotando salida de red con Proton VPN..."
  VPN_BIN=""
  if command -v proton-vpn-cli >/dev/null 2>&1; then
    VPN_BIN="proton-vpn-cli"
  elif command -v protonvpn-cli >/dev/null 2>&1; then
    VPN_BIN="protonvpn-cli"
  fi
  if [ -z "$VPN_BIN" ]; then
    note "No se encontro la CLI de Proton VPN en el PATH; se omite."
    VPN_BIN="(no instalada)"
    return 0
  fi
  note "Ejecutable: $VPN_BIN"
  "$VPN_BIN" disconnect >/dev/null 2>&1 || true
  if "$VPN_BIN" connect --fastest; then
    note "Conectado."
  else
    note "No conecto. Inicia sesion antes con '$VPN_BIN login'."
  fi
  note "El limite de plan gratuito es de la CUENTA, no de la IP: cambiar de salida"
  note "no lo reinicia, solo evita reutilizar la misma ruta de red."
}

# ── recuperacion ─────────────────────────────────────────────────────────────
CLOSED_COUNT=0
CLEANED_DIRS=""

recover() {
  mark_recovery
  rotate_vpn
  close_opencode
  clean_caches
  # Rastro de lo que se hizo: sin esto, un fallo a medias es invisible.
  log_line "recuperacion sesion=${SESSION_ID:-?} cerrados=$CLOSED_COUNT vpn=$VPN_BIN cache=$CLEANED_DIRS"
  echo ""
  echo "==> Proceso completado. Abre OpenCode e inicia un chat nuevo."
}

# ── principal ────────────────────────────────────────────────────────────────
# El log del aviso se escribe siempre, incluso si luego se delega en una ventana
# (la copia delegada hereda OPENCODE_LIMIT_LOGGED=1 y no repite la linea).
log_line "$BANNER sesion=${SESSION_ID:-?} dump=${DUMP_FILE:-?}"

if [ ! -t 1 ]; then
  open_terminal && exit 0
fi

notice

if [ "$RECOVER" != "1" ]; then
  step "Recuperacion desactivada (OPENCODE_LIMIT_RECOVER=$RECOVER): solo aviso."
  log_line "recuperacion omitida (RECOVER=$RECOVER)"
elif cooldown_active; then
  step "Recuperacion omitida: ya se ejecuto hace menos de ${COOLDOWN}s."
  note "El limite sigue activo. Espera a que reinicie la ventana del plan (o cambia de"
  note "cuenta/plan): cerrar OpenCode otra vez no lo reinicia."
  log_line "recuperacion omitida (enfriamiento ${COOLDOWN}s)"
else
  recover
fi

# La ventana se abre desde el servidor de OpenCode: mantenerla visible para que
# el aviso se pueda leer antes de que se cierre sola.
is_number "$KEEP_OPEN_SECONDS" || KEEP_OPEN_SECONDS=0
if [ "$KEEP_OPEN_SECONDS" -gt 0 ]; then
  sleep "$KEEP_OPEN_SECONDS"
fi
