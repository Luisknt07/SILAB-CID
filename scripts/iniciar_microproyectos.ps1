param(
    [switch]$Produccion
)

# Servicio que pone en marcha los microproyectos Django solicitados desde el admin.
# Debe correr junto al servidor web, con Docker disponible para esta cuenta.
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repoRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "No se encontró el entorno virtual en $pythonPath"
}
& docker info --format '{{.ServerVersion}}' | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw 'Docker no está disponible. Inicie Docker antes de este servicio.'
}
if ($Produccion) {
    $env:DJANGO_SETTINGS_MODULE = 'config.settings_production'
}

Push-Location $repoRoot
try {
    & $pythonPath manage.py atender_microproyectos
}
finally {
    Pop-Location
}
