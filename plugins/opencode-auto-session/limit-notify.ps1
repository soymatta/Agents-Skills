<#
  Aviso de limite + recuperacion (Windows). Equivalente funcional de
  limit-notify.sh. Lo lanza el servidor de OpenCode cuando el proveedor devuelve
  un limite/cuota (ver autosession.ts).

  Uso:  limit-notify.ps1 [-SessionID x] [-DumpFile ruta] [-KeepOpenSeconds 20]
        (sin argumentos usa OPENCODE_LIMIT_SESSION / OPENCODE_LIMIT_DUMP /
         OPENCODE_LIMIT_KEEP_OPEN, que es como lo lanza el plugin)

  QUE HACE
    1. Deja SIEMPRE el aviso en limit-notify.log (junto al dump, o en %TEMP%).
    2. Rota la VPN de Proton (solo si su CLI esta instalada).
    3. Cierra OpenCode y sus procesos Node, y limpia caches.

  VARIABLES
    OPENCODE_LIMIT_RECOVER=1     cerrar OpenCode, limpiar cache y rotar la VPN.
                                 Por defecto 0 (solo avisar): el limite gratuito
                                 es de la CUENTA y salta muchas veces al dia, asi
                                 que cerrar OpenCode en cada salto tira la sesion
                                 en la que estas trabajando.
    OPENCODE_LIMIT_COOLDOWN=90   segundos minimos entre recuperaciones (0 = sin tope)
    OPENCODE_LIMIT_KILL_NODE=0   1 = cierra tambien todo node.exe del sistema

  POR QUE NO HACE CIERTAS COSAS
    - No cierra node.exe en bloque: ese `taskkill /IM node.exe /T` del script
      original se lleva por delante editores, servidores MCP y cualquier otra
      aplicacion Node. Solo cierra los procesos Node cuya linea de comandos
      menciona OpenCode (o todos si se pide con OPENCODE_LIMIT_KILL_NODE=1).
    - No borra con `Remove-Item "$env:X\*" -Recurse`: si la variable viene vacia
      la ruta apunta a una raiz. Cada ruta se valida (existe, es un directorio,
      su ultimo componente es de cache) y se borra solo su CONTENIDO.
    - No borra .opencode entero: ahi viven skills/, plugins/, commands/ y
      agents/ del proyecto. Solo limpia subcarpetas de cache y temporales.
    - No instala nada ni pide elevacion.
    - No entra en bucle: si el limite sigue activo, el enfriamiento (cooldown)
      evita volver a cerrar OpenCode cada vez que se reabre.
#>
param(
  [string]$SessionID = $env:OPENCODE_LIMIT_SESSION,
  [string]$DumpFile = $env:OPENCODE_LIMIT_DUMP,
  [int]$KeepOpenSeconds = $(if ($env:OPENCODE_LIMIT_KEEP_OPEN) { [int]$env:OPENCODE_LIMIT_KEEP_OPEN } else { 20 }),
  [string]$Recover = $(if ($env:OPENCODE_LIMIT_RECOVER) { $env:OPENCODE_LIMIT_RECOVER } else { "0" }),
  [int]$Cooldown = $(if ($env:OPENCODE_LIMIT_COOLDOWN) { [int]$env:OPENCODE_LIMIT_COOLDOWN } else { 90 }),
  [string]$KillNode = $(if ($env:OPENCODE_LIMIT_KILL_NODE) { $env:OPENCODE_LIMIT_KILL_NODE } else { "0" })
)

$ErrorActionPreference = "Continue"
$banner = "LIMITE GRATIS ALCANZADO"

function Write-Step([string]$text) { Write-Output ("==> " + $text) }
function Write-Note([string]$text) { Write-Output ("    " + $text) }

# Registro durable: si la ventana no llega a verse, queda constancia de que el
# limite se detecto y de lo que se hizo.
try {
  $logDir = if ($DumpFile) { Split-Path -Parent $DumpFile } else { $env:TEMP }
  if (-not $logDir -or -not (Test-Path -LiteralPath $logDir)) { $logDir = $env:TEMP }
  $script:logFile = Join-Path $logDir "limit-notify.log"
  $script:stampFile = Join-Path $logDir ".limit-notify.stamp"
} catch {
  $script:logFile = $null
  $script:stampFile = $null
}

function Write-Log([string]$text) {
  if (-not $script:logFile) { return }
  try {
    $line = ("{0} {1}" -f (Get-Date -Format "o"), $text)
    Add-Content -LiteralPath $script:logFile -Value $line -ErrorAction SilentlyContinue
  } catch {
    # sin permisos de escritura: el aviso en pantalla ya se imprimio
  }
}

Write-Log ("$banner sesion=$(if ($SessionID) { $SessionID } else { '?' }) dump=$(if ($DumpFile) { $DumpFile } else { '?' })")

Write-Output $banner
Write-Output ("Fecha: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
if ($SessionID) { Write-Output ("Sesion: " + $SessionID) }
if ($DumpFile) { Write-Output ("Dump: " + $DumpFile) }

# ── enfriamiento ─────────────────────────────────────────────────────────────
# Un limite de plan gratuito es de la CUENTA, no de la IP: si se reabre OpenCode
# enseguida, el limite sigue ahi. Sin este tope el script cerraria OpenCode en
# bucle.
function Test-Cooldown {
  if ($Cooldown -le 0) { return $false }
  if (-not $script:stampFile -or -not (Test-Path -LiteralPath $script:stampFile)) { return $false }
  try {
    $last = [int](Get-Content -LiteralPath $script:stampFile -ErrorAction Stop | Select-Object -First 1)
  } catch {
    return $false
  }
  $now = [int][double]::Parse((Get-Date -UFormat %s))
  return (($now - $last) -lt $Cooldown)
}

function Set-CooldownStamp {
  if (-not $script:stampFile) { return }
  try {
    Set-Content -LiteralPath $script:stampFile -Value ([int][double]::Parse((Get-Date -UFormat %s))) -ErrorAction SilentlyContinue
  } catch {
    # sin permisos: el aviso ya quedo registrado
  }
}

# ── limpieza ─────────────────────────────────────────────────────────────────
# Join-Path falla si la variable de entorno no existe (p.ej. LOCALAPPDATA vacio
# en una sesion sin perfil); sin ruta no hay nada que limpiar.
function Join-Safe([string]$root, [string]$leaf) {
  if (-not $root) { return $null }
  try { return (Join-Path $root $leaf) } catch { return $null }
}

# Borra SOLO el contenido de un directorio de cache. Se exige que el ultimo
# componente sea de cache y que la ruta no sea una raiz: asi una variable vacia
# o un directorio de datos jamas se tocan.
function Clear-CacheDir([string]$dir, [ref]$cleaned) {
  if (-not $dir) { return }
  if (-not (Test-Path -LiteralPath $dir -PathType Container)) { return }
  try {
    $full = [System.IO.Path]::GetFullPath($dir)
    if ($full -eq [System.IO.Path]::GetPathRoot($full)) {
      Write-Note "Se omite $dir (es una raiz)."
      return
    }
    $leaf = Split-Path -Leaf $full
    if (@("cache", "Cache", "caches", "Caches", "tmp", "temp", "Temp", "opencode") -notcontains $leaf) {
      Write-Note "Se omite $dir (no es una cache)."
      return
    }
    Get-ChildItem -LiteralPath $full -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    $cleaned.Value = "$($cleaned.Value) $full"
  } catch {
    Write-Note "No se pudo limpiar $dir."
  }
}

# Sanitiza opencode.db para remover cuentas y tokens de usuario conservando las sesiones
function Sanitize-OpenCodeDb([string]$dbPath) {
  if (-not (Test-Path -LiteralPath $dbPath -PathType Leaf)) { return }
  try {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
      & python -c "import sqlite3, sys; conn = sqlite3.connect(sys.argv[1]); [conn.execute(f'DELETE FROM {t}') for t in ['account', 'account_state', 'control_account', 'credential'] if conn.execute(f'SELECT 1 FROM sqlite_master WHERE type=''table'' AND name=''{t}''').fetchone()]; conn.commit(); conn.close()" $dbPath
      Write-Note "Base de datos saneada (cuentas/tokens de usuario limpiados, sesiones intactas)."
    }
  } catch {
    Write-Note "No se pudo sanear opencode.db automáticamente."
  }
}

# ── cierre de procesos ───────────────────────────────────────────────────────
# Nunca node.exe en bloque: se filtra por linea de comandos y se cierra solo lo
# que es de OpenCode.
function Close-OpenCodeProcesses([ref]$closed) {
  Write-Step "Cerrando procesos de OpenCode y Node..."
  $targets = @()

  $targets += @(Get-Process -Name "opencode" -ErrorAction SilentlyContinue)

  # Win32_Process porque Get-Process no expone la linea de comandos.
  $nodes = @()
  try {
    $nodes = @(Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue)
  } catch {
    Write-Note "No se pudo consultar los procesos Node; se omiten."
  }
  foreach ($proc in $nodes) {
    $isOpencodeNode = $proc.CommandLine -and ($proc.CommandLine -match "opencode")
    if ($isOpencodeNode -or [string]$KillNode -eq "1") {
      $found = Get-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue
      if ($found) { $targets += @($found) }
    }
  }

  if ($targets.Count -eq 0) {
    Write-Note "No se encontro ningun proceso de OpenCode en ejecucion."
    return
  }
  Write-Note ("Cerrando {0} proceso(s): {1}" -f $targets.Count, (($targets | ForEach-Object { $_.Id }) -join " "))
  foreach ($proc in $targets) {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
  }
  $closed.Value = $targets.Count
  Write-Note "Cerrados."
}

# ── VPN ──────────────────────────────────────────────────────────────────────
function Rotate-Vpn {
  Write-Step "Rotando salida de red con Proton VPN..."
  $vpnBin = $null
  foreach ($candidate in @("proton-vpn-cli", "protonvpn-cli")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) { $vpnBin = $candidate; break }
  }
  if (-not $vpnBin) {
    Write-Note "No se encontro la CLI de Proton VPN en el PATH; se omite."
    return "(no instalada)"
  }
  Write-Note "Ejecutable: $vpnBin"
  & $vpnBin disconnect *> $null
  & $vpnBin connect --fastest *> $null
  if ($LASTEXITCODE -eq 0) {
    Write-Note "Conectado."
  } else {
    Write-Note "No conecto. Inicia sesion antes con '$vpnBin login'."
  }
  Write-Note "El limite de plan gratuito es de la CUENTA, no de la IP: cambiar de salida"
  Write-Note "no lo reinicia, solo evita reutilizar la misma ruta de red."
  return $vpnBin
}

# ── principal ────────────────────────────────────────────────────────────────
if ([string]$Recover -ne "1") {
  Write-Step "Recuperacion desactivada (OPENCODE_LIMIT_RECOVER=$Recover): solo aviso."
  Write-Log "recuperacion omitida (RECOVER=$Recover)"
} elseif (Test-Cooldown) {
  Write-Step "Recuperacion omitida: ya se ejecuto hace menos de ${Cooldown}s."
  Write-Note "El limite sigue activo. Espera a que reinicie la ventana del plan (o cambia de"
  Write-Note "cuenta/plan): cerrar OpenCode otra vez no lo reinicia."
  Write-Log "recuperacion omitida (enfriamiento ${Cooldown}s)"
} else {
  Set-CooldownStamp
  $vpnUsed = Rotate-Vpn
  $closed = 0
  Close-OpenCodeProcesses ([ref]$closed)
  Write-Step "Limpiando cache temporal (conservando sesiones)..."
  $cleaned = ""
  Clear-CacheDir (Join-Safe $env:LOCALAPPDATA "OpenCode\Cache") ([ref]$cleaned)
  Clear-CacheDir (Join-Safe $env:LOCALAPPDATA "opencode\Cache") ([ref]$cleaned)
  Clear-CacheDir (Join-Safe $env:APPDATA "OpenCode\Cache") ([ref]$cleaned)
  Clear-CacheDir (Join-Safe $env:USERPROFILE ".cache\opencode") ([ref]$cleaned)
  Clear-CacheDir ".opencode\cache" ([ref]$cleaned)
  Clear-CacheDir ".opencode\tmp" ([ref]$cleaned)
  Sanitize-OpenCodeDb (Join-Safe $env:USERPROFILE ".local\share\opencode\opencode.db")
  Write-Note "Sesiones y datos del proyecto intactos."
  Write-Log ("recuperacion sesion=$(if ($SessionID) { $SessionID } else { '?' }) cerrados=$closed vpn=$vpnUsed cache=$cleaned")
  Write-Output ""
  Write-Output "==> Proceso completado. Abre OpenCode e inicia un chat nuevo."
}

# La ventana se abre desde el servidor de OpenCode: mantenerla visible para que
# el aviso se pueda leer antes de que se cierre sola.
if ($KeepOpenSeconds -gt 0) { Start-Sleep -Seconds $KeepOpenSeconds }
