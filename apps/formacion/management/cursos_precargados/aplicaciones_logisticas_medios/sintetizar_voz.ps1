param([string]$Directorio = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($Directorio)) { throw 'Indique la carpeta de fuentes del video.' }
$escenasCurso = Get-Content -LiteralPath (Join-Path $Directorio 'escenas.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$salidaCurso = Join-Path $Directorio '.qa/audio'
New-Item -ItemType Directory -Path $salidaCurso -Force | Out-Null
$vozCurso = New-Object -ComObject SAPI.SpVoice
$vocesCurso = $vozCurso.GetVoices()
$seleccionCurso = $null
for ($iCurso=0; $iCurso -lt $vocesCurso.Count; $iCurso++) {
    $candidataCurso = $vocesCurso.Item($iCurso)
    if ($candidataCurso.GetDescription() -like '*Sabina*') { $seleccionCurso=$candidataCurso; break }
}
if ($null -eq $seleccionCurso) { throw 'No existe la voz española Sabina. No sustituir por una voz inglesa.' }
$vozCurso.Voice = $seleccionCurso
$vozCurso.Rate = 1
$vozCurso.Volume = 100
for ($iCurso=0; $iCurso -lt $escenasCurso.Count; $iCurso++) {
    $archivoCurso = Join-Path $salidaCurso ('escena-{0:D2}.wav' -f ($iCurso+1))
    $flujoCurso = New-Object -ComObject SAPI.SpFileStream
    $flujoCurso.Open($archivoCurso, 3, $false)
    $vozCurso.AudioOutputStream = $flujoCurso
    [void]$vozCurso.Speak($escenasCurso[$iCurso].narration)
    $flujoCurso.Close()
}
Write-Output ('Narración sintética española creada: ' + $seleccionCurso.GetDescription())
