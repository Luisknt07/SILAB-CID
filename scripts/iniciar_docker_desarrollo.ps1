param([switch]$SinConstruir)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Push-Location $taskRoot
try {
    if (-not (Test-Path -LiteralPath '.env')) { throw 'Falta la configuración privada .env de esta instalación.' }
    & docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Inicia Docker Desktop antes de ejecutar este script.' }
    $taskDatabaseJson = & docker inspect slcid-postgresql-institucional
    if ($LASTEXITCODE -ne 0) { throw 'Falta el PostgreSQL existente. Restaurar los respaldos privados antes de iniciar; no crear una base vacía.' }
    $taskDatabase = ($taskDatabaseJson | ConvertFrom-Json)[0]
    $taskVolume = @($taskDatabase.Mounts | Where-Object { $_.Type -eq 'volume' -and $_.Name -eq 'citt_postgres_data' })
    if ($taskVolume.Count -ne 1) { throw 'El PostgreSQL no utiliza el volumen existente esperado.' }
    if (-not $taskDatabase.State.Running) {
        & docker start slcid-postgresql-institucional | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'No se pudo iniciar el PostgreSQL existente.' }
    }
    & docker network inspect citt_default --format '{{.Name}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Falta la red citt_default del servidor de datos existente.' }
    & docker compose -f docker-compose.local.yml config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'La configuración local de Docker no es válida.' }
    $taskArgs = @('compose','-f','docker-compose.local.yml','up','-d','--wait','--wait-timeout','180')
    if (-not $SinConstruir) { $taskArgs += '--build' }
    $taskArgs += 'web'
    & docker @taskArgs
    if ($LASTEXITCODE -ne 0) { throw 'La aplicación no quedó saludable. Revisar docker compose -f docker-compose.local.yml logs web.' }
    Write-Host 'SILAB-CID listo en http://127.0.0.1:8000/; código con recarga automática y bases existentes conservadas.'
}
finally { Pop-Location }
