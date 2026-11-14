param(
    [string]$NombreTarea = 'CITT - Recordatorios de reservas',
    [int]$IntervaloMinutos = 15,
    [switch]$SinCorreo
)

$ErrorActionPreference = 'Stop'
if ($IntervaloMinutos -lt 5 -or $IntervaloMinutos -gt 1440) {
    throw 'El intervalo debe estar entre 5 y 1440 minutos.'
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$runnerPath = Join-Path $PSScriptRoot 'ejecutar_recordatorios.ps1'
if (-not (Test-Path -LiteralPath $runnerPath)) {
    throw "No se encontró el ejecutor en $runnerPath"
}

$taskArguments = "-NoProfile -ExecutionPolicy Bypass -File `"$runnerPath`""
if ($SinCorreo) {
    $taskArguments += ' -SinCorreo'
}
$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument $taskArguments `
    -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervaloMinutos)
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes ([Math]::Max(5, $IntervaloMinutos)))

Register-ScheduledTask `
    -TaskName $NombreTarea `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description 'Procesa vencimientos, recordatorios, asignación, riesgos y cierres pendientes de reservas CITT.' `
    -Force | Out-Null

Write-Host "Tarea '$NombreTarea' instalada cada $IntervaloMinutos minutos."
Write-Host "Registro: $(Join-Path $repoRoot 'var\logs\recordatorios-reservas.log')"
