# OpenCode solo autoload los plugins como `.ts` planos en `~/.config/opencode/plugins/`,
# así que copiamos queue.ts como tui-queue.ts ahí (aplica a TODAS las instalaciones
# del usuario de este Windows). El resto de la estructura (comandos, docs, tests)
# se instala/actualiza con `python setup.py --all` desde el repo.
$ErrorActionPreference = "Stop"
$workspace = $PSScriptRoot
$ocPlugins = Join-Path $HOME ".config\opencode\plugins"
if (-not (Test-Path $ocPlugins)) { New-Item -ItemType Directory -Path $ocPlugins -Force | Out-Null }
Copy-Item -LiteralPath (Join-Path $workspace "queue.ts") -Destination (Join-Path $ocPlugins "tui-queue.ts") -Force
Write-Host "[OK] queue.ts -> $ocPlugins\tui-queue.ts"