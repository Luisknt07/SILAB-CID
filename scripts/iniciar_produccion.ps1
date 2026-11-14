param(
    [string]$Escucha = '127.0.0.1:8000',
    [switch]$SinMigrar
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repoRoot '.venv\Scripts\python.exe'
$waitressPath = Join-Path $repoRoot '.venv\Scripts\waitress-serve.exe'

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "No se encontró el entorno virtual en $pythonPath"
}
if (-not (Test-Path -LiteralPath $waitressPath)) {
    throw 'Waitress no está instalado. Ejecuta: uv sync --locked'
}

$env:DJANGO_SETTINGS_MODULE = 'config.settings_production'
Push-Location $repoRoot
try {
    & $pythonPath manage.py check --deploy
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if (-not $SinMigrar) {
        throw 'Ejecuta las migraciones con el rol separado según docs/produccion-linux.md y vuelve a iniciar con -SinMigrar.'
    }

    & $pythonPath manage.py verificar_seguridad_bd --all
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    # Limpia el despliegue anterior antes de publicar los archivos vigentes.
    & $pythonPath manage.py collectstatic --noinput --clear
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $env:WEB_LISTEN = $Escucha
    & $pythonPath scripts/servir_produccion.py
}
finally {
    Pop-Location
}
