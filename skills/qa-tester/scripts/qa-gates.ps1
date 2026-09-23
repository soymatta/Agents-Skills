# Gates rápidos + QA smoke para un proyecto Node genérico (Windows / PowerShell 7).
# Ejecuta los scripts de npm que existan en el orden: typecheck/tsc, lint, build.
# Con -Full corre también la suite E2E (test:e2e/e2e/test); sin -Full solo smoke/test:smoke.
# Sale con código de error != 0 si cualquier paso falla.
#
# Uso:
#   .\scripts\qa-gates.ps1                       # desde <proyecto>/scripts
#   .\scripts\qa-gates.ps1 -ProjectRoot <ruta>   # apuntando a otro proyecto
#   .\scripts\qa-gates.ps1 -Full                 # incluye la suite E2E
param(
    [string]$ProjectRoot,
    [switch]$Full
)
$ErrorActionPreference = "Stop"

if (-not $ProjectRoot) { $ProjectRoot = Split-Path $PSScriptRoot -Parent }
Set-Location -LiteralPath $ProjectRoot

if (-not (Test-Path (Join-Path $PWD "package.json"))) {
    Write-Host "No hay package.json en $PWD. Usa -ProjectRoot <ruta>." -ForegroundColor Yellow
    exit 1
}

$pkg = Get-Content (Join-Path $PWD "package.json") -Raw | ConvertFrom-Json
$scripts = @{}
if ($pkg.scripts) {
    $pkg.scripts.PSObject.Properties | ForEach-Object { $scripts[$_.Name] = $_.Value }
}

function Run-Npm([string]$name) {
    if ($scripts.ContainsKey($name)) {
        Write-Host "== $name =="
        npm run $name --silent
        if ($LASTEXITCODE -ne 0) { Write-Host "$name falló" -ForegroundColor Red; exit $LASTEXITCODE }
    } else {
        Write-Host "== $name == (sin script; omitido)"
    }
}

Run-Npm "typecheck"
Run-Npm "tsc"
Run-Npm "lint"
Run-Npm "build"

if ($Full) {
    Run-Npm "test:e2e"
    Run-Npm "e2e"
} else {
    Run-Npm "test:smoke"
    Run-Npm "smoke"
}

Write-Host "Gates OK" -ForegroundColor Green