param([switch]$SoloSistema)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repoRoot '.venv\Scripts\python.exe'
$managePath = Join-Path $repoRoot 'manage.py'
$argumentos = @($managePath, 'procesar_recordatorios_documentales')
if ($SoloSistema) { $argumentos += '--solo-sistema' }
Push-Location $repoRoot
try {
    & $pythonPath @argumentos
    $resultado = $LASTEXITCODE
} finally { Pop-Location }
exit $resultado
