param(
    [switch]$SinCorreo
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repoRoot '.venv\Scripts\python.exe'
$managePath = Join-Path $repoRoot 'manage.py'
$logDirectory = Join-Path $repoRoot 'var\logs'
$logPath = Join-Path $logDirectory 'recordatorios-reservas.log'

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "No se encontró el entorno virtual en $pythonPath"
}
if (-not (Test-Path -LiteralPath $managePath)) {
    throw "No se encontró manage.py en $managePath"
}

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$commandArguments = @($managePath, 'procesar_recordatorios_reservas')
if ($SinCorreo) {
    $commandArguments += '--sin-correo'
}

$startedAt = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Add-Content -LiteralPath $logPath -Value "[$startedAt] Inicio" -Encoding utf8
Push-Location $repoRoot
try {
    $commandOutput = & $pythonPath @commandArguments 2>&1
    $exitCode = $LASTEXITCODE
    if ($commandOutput) {
        $commandOutput | ForEach-Object {
            Add-Content -LiteralPath $logPath -Value $_ -Encoding utf8
        }
    }
}
finally {
    Pop-Location
}
$finishedAt = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Add-Content -LiteralPath $logPath -Value "[$finishedAt] Fin (codigo $exitCode)" -Encoding utf8
exit $exitCode
