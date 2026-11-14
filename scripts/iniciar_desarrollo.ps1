param(
    [string]$Escucha = '127.0.0.1:8000',
    [switch]$SinMigrar,
    [switch]$SinEstaticos,
    [switch]$SinRecarga
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repoRoot '.venv\Scripts\python.exe'
$managePath = Join-Path $repoRoot 'manage.py'

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "No se encontró el entorno virtual en $pythonPath"
}
if (-not (Test-Path -LiteralPath $managePath)) {
    throw "No se encontró manage.py en $managePath"
}

Push-Location $repoRoot
try {
    & $pythonPath manage.py check
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $pythonPath manage.py makemigrations --check --dry-run
    if ($LASTEXITCODE -ne 0) {
        Write-Error 'Hay cambios de modelos sin su migración correspondiente.'
        exit $LASTEXITCODE
    }

    if (-not $SinMigrar) {
        # Proceso corto con propietarios separados, sin cambiar el usuario
        # runtime del servidor ni copiar datos entre aliases.
        & $pythonPath scripts/migrar_desarrollo.py
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    if (-not $SinEstaticos) {
        # --clear elimina copias recopiladas antiguas antes de reconstruirlas.
        & $pythonPath manage.py collectstatic --noinput --clear
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    # Si otro servidor conserva el puerto, los cambios nunca llegan al navegador:
    # la plantilla vieja sigue en memoria mientras los estáticos se leen del disco.
    $puerto = [int]($Escucha -split ':')[-1]
    $ocupado = Get-NetTCPConnection -State Listen -LocalPort $puerto -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($ocupado) {
        $dueno = Get-CimInstance Win32_Process -Filter "ProcessId=$($ocupado.OwningProcess)" -ErrorAction SilentlyContinue
        Write-Error ("El puerto $puerto ya lo atiende el proceso $($ocupado.OwningProcess) " +
            "($($dueno.CommandLine)). Deténlo (Stop-Process -Id $($ocupado.OwningProcess)) y vuelve a ejecutar este script.")
        exit 1
    }

    $argumentosServidor = @('manage.py', 'runserver', $Escucha)
    if ($SinRecarga) {
        # Sin recarga automática Django conserva las plantillas en memoria: cada
        # cambio exige reiniciar. Solo para comprobar una versión fija.
        $argumentosServidor += '--noreload'
    }
    Write-Host "Servidor validado. Iniciando la versión vigente en http://$Escucha/"
    & $pythonPath @argumentosServidor
}
finally {
    Pop-Location
}
