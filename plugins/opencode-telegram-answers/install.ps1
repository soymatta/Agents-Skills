# Instala el plugin opencode-telegram-answers en la config global de OpenCode.
# OpenCode autoload los archivos .ts planos que viven en ~/.config/opencode/plugins/,
# así que copiamos notification.ts como telegram-answers.ts ahí (aplica a TODAS
# tus sesiones).
#
# Uso:  powershell -ExecutionPolicy Bypass -File .\install.ps1
#       (o:  npm run install:global)

$ErrorActionPreference = "Stop"

$workspace = $PSScriptRoot
$ocConfig = Join-Path $env:USERPROFILE ".config\opencode"
$ocPlugins = Join-Path $ocConfig "plugins"

if (-not (Test-Path $ocConfig)) { New-Item -ItemType Directory -Path $ocConfig -Force | Out-Null }
if (-not (Test-Path $ocPlugins)) { New-Item -ItemType Directory -Path $ocPlugins -Force | Out-Null }

Copy-Item -LiteralPath (Join-Path $workspace "notification.ts") -Destination (Join-Path $ocPlugins "telegram-answers.ts") -Force
Write-Host "[OK] notification.ts -> $ocPlugins\telegram-answers.ts"

Write-Host ""
Write-Host "Listo. Cierra y vuelve a abrir OpenCode para cargar el plugin."
Write-Host ""
Write-Host "IMPORTANTE: ejecuta UN solo plugin de este grupo. Si el notifier"
Write-Host "clásico (telegram-notifier.ts) también está instalado, bórralo de"
Write-Host "$ocPlugins para no duplicar mensajes de fin de tarea y de permiso."
Write-Host ""
Write-Host "Recuerda configurar las credenciales de Telegram en un .env:"
Write-Host "  copia .env.example -> $ocConfig\.env  (todas las sesiones)"